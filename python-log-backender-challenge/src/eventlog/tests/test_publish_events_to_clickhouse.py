from unittest.mock import MagicMock, patch

from django.test import TestCase

from eventlog.models import EventStatus, OutboxEvent
from eventlog.tasks import publish_events_to_clickhouse


class PublishEventsToClickhouseTestCase(TestCase):
    def setUp(self) -> None:
        OutboxEvent.objects.create(
            event_type='user_created',
            event_data={"id": 1, "name": "John"},
            status=EventStatus.PENDING,
        )
        OutboxEvent.objects.create(
            event_type='user_created',
            event_data={"id": 1, "name": "John Smith"},
            status=EventStatus.PENDING,
        )

    @patch('eventlog.tasks.get_client')
    def test_publish_events_to_clickhouse(self, mock_client: MagicMock) -> None:
        publish_events_to_clickhouse()
        mock_client.return_value.insert.assert_called_once()
        self.assertEqual(OutboxEvent.objects.filter(status=EventStatus.COMPLETED).count(), 2)
