# Dockerfile for Whisper MOWD Demo
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p uploads templates static

# Copy requirements first for better caching
COPY requirements-demo.txt .
RUN pip install --no-cache-dir -r requirements-demo.txt

# Copy application files
COPY app_demo.py .
COPY templates/ templates/
COPY static/ static/

# Create non-root user
RUN useradd -m -u 1000 whisper && chown -R whisper:whisper /app
USER whisper

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app_demo:app", "--host", "0.0.0.0", "--port", "8000"]