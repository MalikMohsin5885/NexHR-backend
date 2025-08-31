# Use stable Python base
FROM python:3.11-slim-bullseye

# Set workdir
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip before installing
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose Django/Gunicorn port
EXPOSE 8000

# Run Gunicorn server by default
CMD ["gunicorn", "nexhr_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers=4", "--threads=2", "--timeout=120"]
