#!/bin/bash
set -e

# Wait for database to be ready (optional)
echo "Waiting for database..."
python -c "
import os
import django
import time
from django.db import connections
from django.core.management.color import no_style
from django.core.management.sql import sql_flush

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexhr_backend.settings')
django.setup()

# Test database connection
for i in range(30):
    try:
        conn = connections['default']
        conn.ensure_connection()
        print('Database is ready!')
        break
    except Exception as e:
        print(f'Database not ready ({i}/30): {e}')
        time.sleep(2)
else:
    print('Could not connect to database after 30 attempts')
    exit(1)
"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || true

# Determine which service to run based on the first argument
SERVICE_TYPE=${1:-web}

case $SERVICE_TYPE in
    "web")
        echo "Starting Django web server with Gunicorn..."
        exec gunicorn nexhr_backend.wsgi:application \
            --bind 0.0.0.0:8080 \
            --workers 2 \
            --worker-class gevent \
            --worker-connections 1000 \
            --timeout 120 \
            --keepalive 5 \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --log-level info \
            --access-logfile - \
            --error-logfile -
        ;;
    "worker")
        echo "Starting Celery worker..."
        exec celery -A nexhr_backend worker \
            --loglevel=info \
            --concurrency=2 \
            --without-gossip \
            --without-mingle \
            --without-heartbeat
        ;;
    "beat")
        echo "Starting Celery beat scheduler..."
        exec celery -A nexhr_backend beat \
            --loglevel=info \
            --schedule=/tmp/celerybeat-schedule \
            --pidfile=/tmp/celerybeat.pid
        ;;
    "flower")
        echo "Starting Flower monitoring..."
        exec celery -A nexhr_backend flower \
            --port=8080 \
            --basic_auth=admin:${FLOWER_PASSWORD:-admin123}
        ;;
    *)
        echo "Unknown service type: $SERVICE_TYPE"
        echo "Available options: web, worker, beat, flower"
        exit 1
        ;;
esac
