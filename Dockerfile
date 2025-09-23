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

# Install gunicorn for production server (removed gevent as it was causing issues)
RUN pip install gunicorn==21.2.0

# Copy project files first
COPY . .

# Create non-root user for security but give proper permissions
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app \
    && chmod -R 755 /app

# Create directories that might be needed
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app/staticfiles /app/media

# Switch to non-root user
USER app

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Expose port for Cloud Run
EXPOSE 8080

# Use entrypoint script to handle different service types
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default to web service (Django with Gunicorn)
CMD ["web"]
