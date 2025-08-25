#!/bin/bash

# Entrypoint script for chatbot-rag Docker container
# This script helps with debugging permission and cache issues

echo "=== Chatbot RAG Container Startup ==="
echo "Current user: $(whoami)"
echo "User ID: $(id -u)"
echo "Group ID: $(id -g)"
echo "Home directory: $HOME"
echo "Current directory: $(pwd)"

# Check cache directories
echo "=== Cache Directory Check ==="
for cache_dir in "$HF_HOME" "$TRANSFORMERS_CACHE" "$HF_DATASETS_CACHE"; do
    if [ -n "$cache_dir" ]; then
        echo "Checking cache directory: $cache_dir"
        if [ -d "$cache_dir" ]; then
            echo "  ✓ Directory exists"
            if [ -w "$cache_dir" ]; then
                echo "  ✓ Directory is writable"
            else
                echo "  ✗ Directory is NOT writable"
                ls -la "$cache_dir"
            fi
        else
            echo "  ✗ Directory does not exist"
            echo "  Creating directory..."
            mkdir -p "$cache_dir" && echo "  ✓ Directory created" || echo "  ✗ Failed to create directory"
        fi
    fi
done

# Check application directories
echo "=== Application Directory Check ==="
for app_dir in "/app/data" "/app/chroma_db" "/app/logs"; do
    echo "Checking app directory: $app_dir"
    if [ -d "$app_dir" ]; then
        echo "  ✓ Directory exists"
        if [ -w "$app_dir" ]; then
            echo "  ✓ Directory is writable"
        else
            echo "  ✗ Directory is NOT writable"
            ls -la "$app_dir"
        fi
    else
        echo "  ✗ Directory does not exist"
        echo "  Creating directory..."
        mkdir -p "$app_dir" && echo "  ✓ Directory created" || echo "  ✗ Failed to create directory"
    fi
done

# Test model loading (optional, can be disabled for faster startup)
if [ "$PRELOAD_MODEL" = "true" ]; then
    echo "=== Pre-loading Model ==="
    python -c "
import os
print('Testing model loading...')
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print('✓ Model loaded successfully')
except Exception as e:
    print(f'✗ Model loading failed: {e}')
    exit(1)
"
fi

echo "=== Starting Application ==="
exec python start_server.py