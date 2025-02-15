from django.core.exceptions import ValidationError
from django.test import TestCase

from eventlog.models import EventStatus, OutboxEvent


class OutboxEventTestCase(TestCase):
    def test_create_event(self) -> None:
        event = OutboxEvent.objects.create(
            event_type='user_created',
            event_data={"user_id": 1, "username": "testuser"},
            metadata_version=1,
        )
        self.assertEqual(event.event_type, 'user_created')
        self.assertEqual(event.event_data, {"user_id": 1, "username": "testuser"})
        self.assertEqual(event.status, EventStatus.PENDING)
        self.assertIsNotNone(event.created_at)
        self.assertIsNone(event.processed_at)
        self.assertEqual(event.retries, 0)
        self.assertEqual(event.max_retries, 3)
        self.assertIsNone(event.last_error)
        self.assertIsNone(event.next_retry_at)


class OutboxEventValidationTestCase(TestCase):
    def test_event_data_required(self) -> None:
        event = OutboxEvent(event_type='user_created', event_data=None, metadata_version=1)
        with self.assertRaises(ValidationError):
            event.clean()


class OutboxEventStatusTestCase(TestCase):
    def test_mark_as_processing(self) -> None:
        event = OutboxEvent.objects.create(
            event_type='user_created',
            event_data={"user_id": 1, "username": "testuser"},
            metadata_version=1,
        )
        event.mark_as_processing()
        self.assertEqual(event.status, EventStatus.PROCESSING)

    def test_mark_as_completed(self) -> None:
        event = OutboxEvent.objects.create(
            event_type='user_created',
            event_data={"user_id": 1, "username": "testuser"},
            metadata_version=1,
        )
        event.mark_as_completed()
        self.assertEqual(event.status, EventStatus.COMPLETED)
        self.assertIsNotNone(event.processed_at)

    def test_mark_as_failed(self) -> None:
        event = OutboxEvent.objects.create(
            event_type='user_created',
            event_data={"user_id": 1, "username": "testuser"},
            metadata_version=1,
        )
        event.mark_as_failed("Ошибка при обработке")
        self.assertEqual(event.status, EventStatus.FAILED)
        self.assertEqual(event.retries, 1)
        self.assertEqual(event.last_error, "Ошибка при обработке")
        self.assertIsNotNone(event.next_retry_at)
