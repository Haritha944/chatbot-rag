#!/bin/bash
# Build and deployment script for Conversational RAG API

set -e

echo "🚀 Building and Deploying Conversational RAG API"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found!"
    if [ -f env.template ]; then
        print_status "Copying env.template to .env..."
        cp env.template .env
        print_warning "Please edit .env file and add your GROQ_API_KEY!"
        print_warning "Then run this script again."
        exit 1
    else
        print_error "No env.template found! Please create .env file manually."
        exit 1
    fi
fi

# Check if GROQ_API_KEY is set
if ! grep -q "GROQ_API_KEY=your_groq_api_key_here" .env; then
    print_status "GROQ_API_KEY appears to be configured ✓"
else
    print_error "Please set your GROQ_API_KEY in .env file!"
    exit 1
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p data chroma_db logs

# Build Docker image
print_status "Building Docker image..."
docker build -t chatbot-rag:latest .

# Check if build was successful
if [ $? -eq 0 ]; then
    print_status "Docker image built successfully ✓"
else
    print_error "Docker build failed!"
    exit 1
fi

# Run with Docker Compose
print_status "Starting services with Docker Compose..."
docker-compose up -d

# Wait for service to be ready
print_status "Waiting for service to be ready..."
sleep 10

# Check health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Service is healthy ✓"
    echo ""
    echo "🎉 Deployment successful!"
    echo "================================================"
    echo "🌐 API URL: http://localhost:8000"
    echo "📚 Documentation: http://localhost:8000/docs"
    echo "❤️  Health Check: http://localhost:8000/health"
    echo "📊 Session Stats: http://localhost:8000/api/v1/sessions/stats"
    echo ""
    echo "📋 Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop services: docker-compose down"
    echo "  Restart: docker-compose restart"
    echo "================================================"
else
    print_warning "Service might still be starting up..."
    print_status "Check logs with: docker-compose logs -f"
fi
