import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'codesh.settings')

app = Celery('codesh')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
