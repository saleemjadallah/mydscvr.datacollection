#!/bin/bash

# DXB Events Lifecycle Management Setup Script
echo "🚀 Setting up DXB Events Lifecycle Management System..."
echo "================================================================"

# Check if we're in the right directory
if [[ ! -f "main.py" ]]; then
    echo "❌ Please run this script from the Backend directory"
    exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo "1️⃣ Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found. Please install Python 3.8 or higher"
    exit 1
fi

# Check pip
echo "2️⃣ Checking pip installation..."
if command_exists pip3; then
    echo "✅ pip3 found"
elif command_exists pip; then
    echo "✅ pip found"
else
    echo "❌ pip not found. Please install pip"
    exit 1
fi

# Install requirements
echo "3️⃣ Installing Python dependencies..."
if [[ -f "requirements.txt" ]]; then
    pip3 install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# Check Redis
echo "4️⃣ Checking Redis availability..."
if command_exists redis-cli; then
    if redis-cli ping >/dev/null 2>&1; then
        echo "✅ Redis is running"
    else
        echo "⚠️ Redis is not running. Starting Redis..."
        # Try to start Redis with different methods
        if command_exists brew; then
            brew services start redis
        elif command_exists systemctl; then
            sudo systemctl start redis
        elif command_exists service; then
            sudo service redis-server start
        else
            echo "❌ Could not start Redis automatically"
            echo "💡 Please start Redis manually or run: docker run -d -p 6379:6379 redis:alpine"
            exit 1
        fi
    fi
else
    echo "⚠️ Redis not found. Installing with Docker..."
    if command_exists docker; then
        docker run -d -p 6379:6379 --name dxb-redis redis:alpine
        echo "✅ Redis started in Docker container"
    else
        echo "❌ Docker not found. Please install Redis or Docker"
        echo "💡 macOS: brew install redis"
        echo "💡 Ubuntu: sudo apt-get install redis-server"
        echo "💡 Docker: docker run -d -p 6379:6379 redis:alpine"
        exit 1
    fi
fi

# Initialize the lifecycle management system
echo "5️⃣ Initializing lifecycle management system..."
python3 start_lifecycle_management.py

if [[ $? -eq 0 ]]; then
    echo "✅ Lifecycle management system initialized successfully"
else
    echo "❌ Initialization failed. Check the logs above."
    exit 1
fi

# Create startup helper scripts
echo "6️⃣ Creating startup helper scripts..."

# Celery worker script
cat > start_celery_worker.sh << 'EOF'
#!/bin/bash
echo "🔧 Starting Celery Worker for DXB Events Lifecycle Management..."
celery -A lifecycle_management.celery_config:celery_app worker \
    --loglevel=info \
    --queues=cleanup,monitoring \
    --concurrency=2 \
    --prefetch-multiplier=1
EOF

# Celery beat script
cat > start_celery_beat.sh << 'EOF'
#!/bin/bash
echo "⏰ Starting Celery Beat Scheduler for DXB Events Lifecycle Management..."
celery -A lifecycle_management.celery_config:celery_app beat \
    --loglevel=info \
    --schedule=/tmp/celerybeat-schedule
EOF

# FastAPI server script
cat > start_api_server.sh << 'EOF'
#!/bin/bash
echo "🌐 Starting FastAPI Server with Lifecycle Management..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
EOF

# Make scripts executable
chmod +x start_celery_worker.sh
chmod +x start_celery_beat.sh
chmod +x start_api_server.sh

echo "✅ Startup scripts created"

# Final instructions
echo ""
echo "================================================================"
echo "🎉 SETUP COMPLETE!"
echo "================================================================"
echo ""
echo "📋 TO START THE SYSTEM:"
echo ""
echo "   Terminal 1 - Celery Worker:"
echo "   ./start_celery_worker.sh"
echo ""
echo "   Terminal 2 - Celery Beat Scheduler:"
echo "   ./start_celery_beat.sh"
echo ""
echo "   Terminal 3 - FastAPI Server:"
echo "   ./start_api_server.sh"
echo ""
echo "📊 MONITORING ENDPOINTS:"
echo "   Health Check:     http://localhost:8000/lifecycle/health"
echo "   Statistics:       http://localhost:8000/lifecycle/stats"
echo "   Cost Estimate:    http://localhost:8000/lifecycle/cost-estimate"
echo "   Weekly Report:    http://localhost:8000/lifecycle/weekly-report"
echo "   API Docs:         http://localhost:8000/docs"
echo ""
echo "🔧 MANUAL TASKS:"
echo "   Trigger Cleanup:  curl -X POST http://localhost:8000/lifecycle/tasks/trigger-cleanup"
echo "   Health Check:     curl -X POST http://localhost:8000/lifecycle/tasks/trigger-health-check"
echo ""
echo "📚 DOCUMENTATION:"
echo "   See lifecycle_management/README.md for detailed documentation"
echo ""
echo "================================================================"
echo "🚀 DXB Events Lifecycle Management is ready!"
echo "================================================================" 