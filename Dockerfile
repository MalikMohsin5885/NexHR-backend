# Multi-stage build for Google Cloud Run
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn and gevent for production server
RUN pip install gunicorn==21.2.0 gevent==23.9.1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Copy project files
COPY --chown=app:app . .

# Collect static files (if needed)
RUN python manage.py collectstatic --noinput --clear || true

# Create entrypoint script
COPY --chown=app:app docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose port for Cloud Run
EXPOSE 8080

# Use entrypoint script to handle different service types
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default to web service (Django with Gunicorn)
CMD ["web"]
