import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core', broker='redis://redis:6379/0')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

CELERY_BEAT_SCHEDULE = {
    'publish-events-to-clickhouse': {
        'task': 'your_app.tasks.publish_events_to_clickhouse',
        'schedule': 60.0,
    },
}