from django.contrib import admin

from .models import OutboxEvent


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "created_at", "processed_at", "retries")
    list_filter = ("event_type", "processed_at", "created_at")
    search_fields = ("event_type", "event_data")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

