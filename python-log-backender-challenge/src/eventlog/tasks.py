import structlog
from celery import shared_task
from clickhouse_connect import get_client
from django.conf import settings
from django.db import transaction

from .models import OutboxEvent

logger = structlog.get_logger(__name__)

@shared_task
def publish_events_to_clickhouse() -> None:   # noqa: C901
    logger.info("Starting publish_events_to_clickhouse task")
    events = OutboxEvent.get_unprocessed_events(limit=1000)
    if not events:
        logger.info("No events to publish")
        return

    event_data = [
        (event.event_type, event.created_at, settings.ENVIRONMENT, event.event_data)
        for event in events
    ]

    client = get_client(
        host=settings.CLICKHOUSE_HOST,
        port=settings.CLICKHOUSE_PORT,
        user=settings.CLICKHOUSE_USER,
        password=settings.CLICKHOUSE_PASSWORD,
    )

    try:
        with transaction.atomic():
            for event in events:
                event.mark_as_processing()

        client.insert(
            data=event_data,
            column_names=["event_type", "event_date_time", "environment", "event_context"],
            database=settings.CLICKHOUSE_SCHEMA,
            table=settings.CLICKHOUSE_EVENT_LOG_TABLE_NAME,
        )

        with transaction.atomic():
            for event in events:
                event.mark_as_completed()

        logger.info(f"Successfully published {len(events)} events to ClickHouse")
    except Exception as e:
        logger.error(f"Failed to publish events to ClickHouse: {str(e)}")
        with transaction.atomic():
            for event in events:
                event.mark_as_failed(error_message=str(e))
        raise
    finally:
        client.close()
