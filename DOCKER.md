# Docker Deployment Guide

This guide explains how to build and deploy the Conversational RAG API using Docker.

## 🐳 Docker Files Overview

- **`Dockerfile`**: Multi-stage build for optimized production image
- **`docker-compose.yml`**: Complete deployment with optional Nginx proxy
- **`.dockerignore`**: Excludes unnecessary files from build context
- **`nginx.conf`**: Production-ready Nginx configuration
- **`deploy.sh`** / **`deploy.bat`**: Automated deployment scripts

## 🚀 Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ available RAM
- 10GB+ available disk space

### 1. Environment Setup

```bash
# Copy environment template
cp env.template .env

# Edit .env file and set your GROQ_API_KEY
nano .env  # or use your preferred editor
```

### 2. Automated Deployment

**Linux/macOS:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

### 3. Manual Deployment

```bash
# Create directories
mkdir -p data chroma_db logs

# Build image
docker build -t chatbot-rag:latest .

# Start services
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

## 📊 Service Access

After deployment, access these endpoints:

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Session Stats**: http://localhost:8000/api/v1/sessions/stats

## 🔧 Configuration

### Environment Variables

All configuration is handled through environment variables in `.env`:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional (defaults shown)
MODEL_NAME=llama-3.3-70b-versatile
TEMPERATURE=0.7
VECTOR_STORE_TYPE=chroma
VECTOR_STORE_PATH=./chroma_db
MEMORY_TYPE=buffer
MAX_TOKEN_LIMIT=2000
SESSION_STORE_TYPE=sqlite
SESSION_DB_PATH=./data/sessions.db
SESSION_TTL=3600
MAX_CACHED_SESSIONS=100
CLEANUP_INTERVAL=300
DB_CONNECTION_POOL_SIZE=10
MAX_CONCURRENT_REQUESTS=50
```

### Volume Mounts

Data persistence is handled through Docker volumes:

- `./data:/app/data` - SQLite session database
- `./chroma_db:/app/chroma_db` - Vector store data
- `./logs:/app/logs` - Application logs

## 🏗️ Docker Image Details

### Multi-Stage Build

The Dockerfile uses a multi-stage build:

1. **Builder Stage**: Installs build dependencies and Python packages
2. **Production Stage**: Creates minimal runtime image

### Security Features

- Non-root user execution
- Minimal base image (Python 3.11 slim)
- No unnecessary packages in production
- Health checks enabled

### Image Size Optimization

- Virtual environment copying from builder stage
- Build dependencies excluded from final image
- Efficient layer caching

## 📈 Production Deployment

### With Nginx Proxy

For production, enable the Nginx service:

```bash
docker-compose --profile production up -d
```

This provides:
- Rate limiting (10 requests/second)
- Gzip compression
- Security headers
- Load balancing ready
- SSL termination ready

### Resource Limits

Add resource limits in `docker-compose.yml`:

```yaml
services:
  chatbot-rag:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Scaling

Scale the application:

```bash
docker-compose up -d --scale chatbot-rag=3
```

## 🔍 Monitoring & Troubleshooting

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f chatbot-rag

# With timestamps
docker-compose logs -f -t chatbot-rag
```

### Health Monitoring

```bash
# Check container health
docker-compose ps

# Detailed health check
curl -v http://localhost:8000/health

# Service statistics
curl http://localhost:8000/api/v1/sessions/stats
```

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker-compose logs chatbot-rag

# Common causes:
# - Missing GROQ_API_KEY
# - Port 8000 already in use
# - Insufficient permissions on data directories
```

#### High Memory Usage
```bash
# Check resource usage
docker stats

# Solutions:
# - Reduce MAX_CACHED_SESSIONS
# - Decrease MAX_TOKEN_LIMIT
# - Add memory limits
```

#### Database Issues
```bash
# Check SQLite database
docker-compose exec chatbot-rag ls -la /app/data/

# Reset database (WARNING: Loses all sessions)
docker-compose down
rm -rf data/sessions.db*
docker-compose up -d
```

## 🛠️ Development

### Development Mode

For development with live code reloading:

```yaml
# docker-compose.dev.yml
services:
  chatbot-rag:
    build: .
    volumes:
      - ./app:/app/app:ro  # Mount source code
    environment:
      - PYTHONPATH=/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

```bash
docker-compose -f docker-compose.dev.yml up
```

### Building Different Variants

```bash
# Development build with debug symbols
docker build --target builder -t chatbot-rag:dev .

# Production build (default)
docker build -t chatbot-rag:prod .

# Custom Python version
docker build --build-arg PYTHON_VERSION=3.12 -t chatbot-rag:py312 .
```

## 🔄 Updates & Maintenance

### Update Application

```bash
# Pull latest code
git pull

# Rebuild and redeploy
docker-compose down
docker build -t chatbot-rag:latest .
docker-compose up -d
```

### Database Maintenance

```bash
# Backup sessions database
docker-compose exec chatbot-rag sqlite3 /app/data/sessions.db ".backup /app/data/sessions_backup.db"

# Cleanup expired sessions
curl -X POST http://localhost:8000/api/v1/sessions/cleanup
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove images
docker rmi chatbot-rag:latest

# Clean up volumes (WARNING: Removes all data)
docker-compose down -v

# System cleanup
docker system prune -f
```

## 🌐 Cloud Deployment

### Docker Hub

```bash
# Tag for Docker Hub
docker tag chatbot-rag:latest username/chatbot-rag:latest

# Push to Docker Hub
docker push username/chatbot-rag:latest
```

### AWS ECS / Azure Container Instances

```yaml
# Use the provided docker-compose.yml as a base
# Add cloud-specific configurations:
# - Load balancers
# - Auto-scaling
# - Log aggregation
# - Secret management
```

### Kubernetes

```yaml
# Example Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatbot-rag
spec:
  replicas: 3
  selector:
    matchLabels:
      app: chatbot-rag
  template:
    metadata:
      labels:
        app: chatbot-rag
    spec:
      containers:
      - name: chatbot-rag
        image: chatbot-rag:latest
        ports:
        - containerPort: 8000
        env:
        - name: GROQ_API_KEY
          valueFrom:
            secretKeyRef:
              name: groq-secret
              key: api-key
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
        - name: chroma-volume
          mountPath: /app/chroma_db
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: data-pvc
      - name: chroma-volume
        persistentVolumeClaim:
          claimName: chroma-pvc
```

This Docker setup provides a production-ready deployment for your Conversational RAG API with proper security, monitoring, and scalability features.
