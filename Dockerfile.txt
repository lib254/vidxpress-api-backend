# Use a lightweight official Python image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and using output buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies first (for caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create directory for temporary files and make it writable
RUN mkdir -p /tmp/files && chmod -R 777 /tmp/files

# Expose the application port (Render injects $PORT automatically)
EXPOSE 8000

# Default startup command
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
