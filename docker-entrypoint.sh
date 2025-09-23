#!/bin/bash
set -e

# Get port from environment (Cloud Run sets PORT)
PORT=${PORT:-8080}

# Determine which service to run based on the first argument
SERVICE_TYPE=${1:-web}

# For web service, we need to handle database and static files
if [ "$SERVICE_TYPE" = "web" ]; then
    echo "Preparing web service..."
    
    # Only try database operations if DATABASE_URL is set
    if [ -n "$DATABASE_URL" ] || [ -n "$POSTGRES_DB" ]; then
        echo "Database configuration found, testing connection..."
        python -c "
import os
import django
import time
from django.db import connections

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexhr_backend.settings')
django.setup()

# Test database connection with timeout
try:
    conn = connections['default']
    conn.ensure_connection()
    print('Database connection successful!')
except Exception as e:
    print(f'Database connection failed: {e}')
    print('Continuing anyway - migrations will handle this...')
" || echo "Database check skipped due to error"

        # Run migrations
        echo "Running migrations..."
        python manage.py migrate --noinput || echo "Migration failed, continuing..."
    else
        echo "No database configuration found, skipping database operations"
    fi

    # Collect static files
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear || echo "Static files collection failed, continuing..."
fi

case $SERVICE_TYPE in
    "web")
        echo "Starting Django web server with Gunicorn on port $PORT..."
        exec gunicorn nexhr_backend.wsgi:application \
            --bind 0.0.0.0:$PORT \
            --workers 2 \
            --worker-class sync \
            --worker-connections 1000 \
            --timeout 120 \
            --keepalive 5 \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --log-level info \
            --access-logfile - \
            --error-logfile - \
            --capture-output
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
        echo "Starting Flower monitoring on port $PORT..."
        exec celery -A nexhr_backend flower \
            --port=$PORT \
            --basic_auth=admin:${FLOWER_PASSWORD:-admin123}
        ;;
    *)
        echo "Unknown service type: $SERVICE_TYPE"
        echo "Available options: web, worker, beat, flower"
        exit 1
        ;;
esac
