@echo off
REM Build and deployment script for Conversational RAG API (Windows)

echo ========================================
echo Building and Deploying Conversational RAG API
echo ========================================

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found!
    if exist env.template (
        echo [INFO] Copying env.template to .env...
        copy env.template .env
        echo [WARNING] Please edit .env file and add your GROQ_API_KEY!
        echo [WARNING] Then run this script again.
        pause
        exit /b 1
    ) else (
        echo [ERROR] No env.template found! Please create .env file manually.
        pause
        exit /b 1
    )
)

REM Check if GROQ_API_KEY is configured
findstr /C:"GROQ_API_KEY=your_groq_api_key_here" .env > nul
if %errorlevel% == 0 (
    echo [ERROR] Please set your GROQ_API_KEY in .env file!
    pause
    exit /b 1
) else (
    echo [INFO] GROQ_API_KEY appears to be configured
)

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist data mkdir data
if not exist chroma_db mkdir chroma_db
if not exist logs mkdir logs

REM Build Docker image
echo [INFO] Building Docker image...
docker build -t chatbot-rag:latest .

if %errorlevel% neq 0 (
    echo [ERROR] Docker build failed!
    pause
    exit /b 1
)

echo [INFO] Docker image built successfully

REM Run with Docker Compose
echo [INFO] Starting services with Docker Compose...
docker-compose up -d

REM Wait for service to be ready
echo [INFO] Waiting for service to be ready...
timeout /t 10 /nobreak > nul

REM Check health
curl -f http://localhost:8000/health > nul 2>&1
if %errorlevel% == 0 (
    echo [INFO] Service is healthy
    echo.
    echo Deployment successful!
    echo ========================================
    echo API URL: http://localhost:8000
    echo Documentation: http://localhost:8000/docs
    echo Health Check: http://localhost:8000/health
    echo Session Stats: http://localhost:8000/api/v1/sessions/stats
    echo.
    echo Useful commands:
    echo   View logs: docker-compose logs -f
    echo   Stop services: docker-compose down
    echo   Restart: docker-compose restart
    echo ========================================
) else (
    echo [WARNING] Service might still be starting up...
    echo [INFO] Check logs with: docker-compose logs -f
)

pause
