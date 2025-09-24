#!/bin/bash
set -e

# Get port from environment (Cloud Run sets PORT)
PORT=${PORT:-8080}

# Set Django settings module
export DJANGO_SETTINGS_MODULE=nexhr_backend.settings

# Set minimal required environment variables for container startup
export DEBUG=${DEBUG:-False}
export SECRET_KEY=${SECRET_KEY:-django-insecure-38c5xwiefht=#wsahbul4n3*9&g4tgz^_jn2m8(!0c$1z2&)#f}
export ALLOWED_HOSTS=${ALLOWED_HOSTS:-localhost,127.0.0.1,*.run.app}

echo "🚀 Starting NexHR Backend on port $PORT"
echo "📋 Django Settings Module: $DJANGO_SETTINGS_MODULE"
echo "🔧 DEBUG: $DEBUG"
echo "🌐 ALLOWED_HOSTS: $ALLOWED_HOSTS"

# Determine which service to run based on the first argument
SERVICE_TYPE=${1:-web}

# Function to test Django setup
test_django_setup() {
    echo "🧪 Testing Django setup..."
    python test_startup.py || exit 1
}

# Health check server function for non-HTTP services
start_health_server() {
    echo "🏥 Starting health check server on port 8080..."
    python3 -c "
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Disable logging

def health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    print('✅ Health check server started on port 8080')
    server.serve_forever()

# Start health server in background
thread = threading.Thread(target=health_server, daemon=True)
thread.start()
print('🚀 Health server started for Cloud Run')
" &
}

# For web service, we need to handle database and static files
if [ "$SERVICE_TYPE" = "web" ]; then
    echo "🌐 Preparing web service..."
    
    # Test Django setup first
    test_django_setup
    
    # Skip database operations initially to test basic startup
    echo "⏭️  Skipping database operations for faster startup"
    
    # Skip static files collection initially
    echo "⏭️  Skipping static files collection for faster startup"
fi

case $SERVICE_TYPE in
    "web")
        echo "🚀 Starting Django web server with Gunicorn on port $PORT..."
        exec gunicorn nexhr_backend.wsgi:application \
            --bind 0.0.0.0:$PORT \
            --workers 1 \
            --timeout 60 \
            --log-level info \
            --access-logfile - \
            --error-logfile - \
            --preload
        ;;
    
    "worker")
        echo "🔄 Starting Celery worker..."
        test_django_setup
        start_health_server
        
        echo "🚀 Starting Celery worker..."
        exec celery -A nexhr_backend worker \
            --loglevel=info \
            --concurrency=2 \
            --without-gossip \
            --without-mingle \
            --without-heartbeat
        ;;
    
    "beat")
        echo "⏰ Starting Celery beat scheduler..."
        test_django_setup
        start_health_server
        
        exec celery -A nexhr_backend beat \
            --loglevel=info \
            --schedule=/tmp/celerybeat-schedule \
            --pidfile=/tmp/celerybeat.pid
        ;;
    
    "flower")
        echo "🌸 Starting Flower monitoring on port $PORT..."
        test_django_setup
        
        # Flower already has HTTP server, but ensure it uses the correct port
        echo "🔧 Configuring Flower to use port $PORT for health checks..."
        exec celery -A nexhr_backend flower \
            --port=$PORT \
            --basic_auth=admin:${FLOWER_PASSWORD:-admin123}
        ;;
    
    *)
        echo "❌ Unknown service type: $SERVICE_TYPE"
        echo "Available options: web, worker, beat, flower"
        exit 1
        ;;
esac