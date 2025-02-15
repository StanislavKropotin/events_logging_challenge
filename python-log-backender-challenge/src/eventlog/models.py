import json

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class EventStatus(models.TextChoices):
    PENDING = "pending", "Ожидает обработки"
    PROCESSING = "processing", "В процессе обработки"
    FAILED = "failed", "Ошибка обработки"
    COMPLETED = "completed", "Обработано успешно"


class OutboxEvent(models.Model):
    EVENT_TYPES = (("user_created", "User Created"),)

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        help_text="Тип события",
    )
    event_data = models.JSONField(
        help_text="Данные события в формате JSON",
    )
    metadata_version = models.PositiveIntegerField(
        default=1,
        help_text="Версия структуры метаданных",
    )
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PENDING,
        help_text="Текущий статус обработки события",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="Время создания события",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Время успешной обработки события",
    )
    retries = models.IntegerField(
        default=0,
        help_text="Количество попыток обработки",
    )
    max_retries = models.IntegerField(
        default=3,
        help_text="Максимальное количество попыток",
    )
    last_error = models.TextField(
        null=True,
        blank=True,
        help_text="Описание последней ошибки",
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Время следующей попытки обработки",
    )

    class Meta:
        indexes = [
            models.Index(fields=["status", "next_retry_at"], name="status_retry_idx"),
            models.Index(fields=["created_at"], name="created_at_idx"),
            models.Index(fields=["event_type"], name="event_type_idx"),
        ]
        ordering = ["created_at"]

    def clean(self) -> None:
        super().clean()
        if not self.event_data:
            raise ValidationError({"event_data": "Event data cannot be empty"})
        try:
            json.dumps(self.event_data)
        except (TypeError, json.JSONDecodeError) as err:
            raise ValidationError({"event_data": "Invalid JSON format"}) from err

    def save(self, *args: tuple, **kwargs: dict) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_pending_events(cls, batch_size: int = 1000) -> models.QuerySet["OutboxEvent"]:
        now = timezone.now()
        return cls.objects.filter(
            models.Q(status=EventStatus.PENDING)
            | models.Q(
                status=EventStatus.FAILED,
                retries__lt=models.F("max_retries"),
                next_retry_at__lte=now,
            ),
        ).exclude(next_retry_at=None)[:batch_size]

    def mark_as_processing(self) -> None:
        self.status = EventStatus.PROCESSING
        self.save(update_fields=["status"])

    def mark_as_completed(self) -> None:
        self.status = EventStatus.COMPLETED
        self.processed_at = timezone.now()
        self.save(update_fields=["status", "processed_at"])

    def mark_as_failed(self, error_message: str) -> None:
        self.status = EventStatus.FAILED
        self.last_error = error_message
        self.retries += 1
        if self.retries < self.max_retries:
            delay_minutes = 2 ** (self.retries - 1)
            self.next_retry_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        else:
            self.next_retry_at = None
        self.save(update_fields=["status", "last_error", "retries", "next_retry_at"])

    def __str__(self) -> str:  # Добавлена аннотация типа
        return f"{self.event_type} ({self.status}) - {self.created_at}"

    @classmethod
    def get_unprocessed_events(cls, limit: int = 1000) -> models.QuerySet["OutboxEvent"]:
        return cls.objects.filter(processed_at__isnull=True)[:limit]
