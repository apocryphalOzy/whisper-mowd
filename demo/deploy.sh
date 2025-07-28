#!/bin/bash
# Deployment script for Whisper MOWD Demo

echo "=== Whisper MOWD Demo Deployment ==="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Set environment variables
export DEMO_PASSWORD=${DEMO_PASSWORD:-whisper2025}

echo "Configuration:"
echo "- Demo Password: $DEMO_PASSWORD"
echo "- Port: 8000"
echo ""

# Build and start containers
echo "Building Docker image..."
docker-compose build

echo ""
echo "Starting containers..."
docker-compose up -d

# Wait for health check
echo ""
echo "Waiting for application to start..."
sleep 10

# Check if running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "Access the demo at: http://localhost:8000"
    echo "Demo password: $DEMO_PASSWORD"
    echo ""
    echo "Commands:"
    echo "- View logs: docker-compose logs -f"
    echo "- Stop: docker-compose down"
    echo "- Restart: docker-compose restart"
else
    echo ""
    echo "❌ Deployment failed. Check logs with: docker-compose logs"
    exit 1
fi