# Multi-stage Docker build for Conversational RAG API
# Stage 1: Build stage with all build dependencies
FROM python:3.11-slim as builder

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY app/ app/
COPY start_server.py .
COPY requirements.txt .
COPY entrypoint.sh .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/chroma_db /app/logs /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser/.cache

# Set cache directories for HuggingFace and transformers
ENV HF_HOME=/home/appuser/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/transformers \
    HF_DATASETS_CACHE=/home/appuser/.cache/huggingface/datasets \
    PRELOAD_MODEL=false \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    PYTORCH_TRANSFORMERS_CACHE=/home/appuser/.cache/huggingface/transformers

# Create HuggingFace cache directories with proper permissions
RUN mkdir -p /home/appuser/.cache/huggingface/transformers /home/appuser/.cache/huggingface/datasets && \
    chown -R appuser:appuser /home/appuser/.cache

# Pre-download the sentence transformer model during build (DISABLED for memory optimization)
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" && \
#     chown -R appuser:appuser /home/appuser/.cache

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["./entrypoint.sh"]
