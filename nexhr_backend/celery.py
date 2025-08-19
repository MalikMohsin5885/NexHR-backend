# nexhr_backend/celery.py
import os
from celery import Celery

# set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexhr_backend.settings')

app = Celery('nexhr_backend')

# Load custom config from Django settings, all CELERY_ vars
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps (accounts, api, etc.)
app.autodiscover_tasks()
