FROM python:3.12-slim

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (build-essential, libpq for PostgreSQL, fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY .env.example .env.example

# Create data directory for SQLite database storage
RUN mkdir -p /app/data

# Default command
CMD ["python", "-m", "app.main"]
