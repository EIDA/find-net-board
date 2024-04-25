import os
from datetime import timedelta
from celery import Celery


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netstests.settings')

app = Celery('netstests', broker='pyamqp://guest@127.0.0.1:5672//')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Define periodic tasks
app.conf.beat_schedule = {
    'update db and run tests every 14 days': {
        'task': 'board.tasks.update_and_run',
        'schedule': timedelta(days=14),
    },
}
