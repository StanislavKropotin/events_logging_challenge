from unittest.mock import Mock, patch

from django.test import TestCase

from eventlog.models import OutboxEvent
from eventlog.tasks import publish_events_to_clickhouse


class PublishEventsToClickhouseErrorHandlingTestCase(TestCase):
    def setUp(self) -> None:
        OutboxEvent.objects.create(event_type='user_created', event_data={"id": 1, "name": "John"})

    @patch('eventlog.tasks.get_client')
    def test_clickhouse_error_handling(self, mock_client: Mock) -> None:
        mock_client.return_value.insert.side_effect = Exception("ClickHouse connection error")

        with self.assertRaises(Exception) as context:
            publish_events_to_clickhouse()

        self.assertEqual(str(context.exception), "ClickHouse connection error")

        self.assertEqual(OutboxEvent.objects.filter(processed_at__isnull=True).count(), 1)
