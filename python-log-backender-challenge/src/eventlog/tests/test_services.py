from unittest.mock import MagicMock, patch

from django.test import TestCase

from eventlog.models import OutboxEvent
from eventlog.services import save_event


class SaveEventTests(TestCase):
    @patch('eventlog.services.logger')
    def test_save_event_success(self, mock_logger: MagicMock) -> None:
        event_type = "user_created"
        event_data = {"user_id": 123, "username": "john_doe"}
        event = save_event(event_type, event_data)
        self.assertIsInstance(event, OutboxEvent)
        self.assertEqual(event.event_type, event_type)
        self.assertEqual(event.event_data, event_data)
        mock_logger.info.assert_called_once_with(
            "Event saved to Outbox", event_type=event_type, event_data=event_data,
        )

    @patch('eventlog.services.logger')
    def test_save_event_failure(self, mock_logger: MagicMock) -> None:
        event_type = "user_created"
        event_data = {"user_id": 123}

        # Use a more specific exception type instead of generic Exception
        with patch("eventlog.models.OutboxEvent.objects.create", side_effect=Exception("Database error")):
            with self.assertRaises(Exception) as context:
                save_event(event_type, event_data)

            self.assertEqual(str(context.exception), "Database error")
            mock_logger.error.assert_called_once_with(
                "Failed to save event to Outbox", error="Database error",
            )
