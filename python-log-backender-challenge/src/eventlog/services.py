import structlog

from .models import OutboxEvent

logger = structlog.get_logger(__name__)


def save_event(event_type: str, event_data: dict) -> OutboxEvent:
    try:
        event = OutboxEvent.objects.create(
            event_type=event_type,
            event_data=event_data,
        )
        logger.info("Event saved to Outbox", event_type=event_type, event_data=event_data)
        return event
    except Exception as e:
        logger.error("Failed to save event to Outbox", error=str(e))
        raise
