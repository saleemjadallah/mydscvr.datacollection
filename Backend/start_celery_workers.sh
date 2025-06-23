#!/bin/bash

# DXB Events - Celery Workers Startup Script
# This script starts Celery workers for lifecycle management

echo "🚀 Starting DXB Events Lifecycle Management Celery Workers..."

# Check if we're in the Backend directory
if [[ ! -d "lifecycle_management" ]]; then
    echo "❌ Error: Must run from Backend directory"
    echo "📂 Please run: cd Backend && ./start_celery_workers.sh"
    exit 1
fi

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Error: Redis is not running"
    echo "📋 Please start Redis first: brew services start redis"
    exit 1
fi

echo "✅ Redis is running"

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Virtual environment not detected"
    echo "📋 Please activate it: source ../.venv/bin/activate"
fi

# Test Celery configuration
echo "🔍 Testing Celery configuration..."
python -c "from lifecycle_management.celery_config import celery_app; print('✅ Celery app loaded successfully')" || {
    echo "❌ Error: Failed to load Celery configuration"
    exit 1
}

echo "🎯 Starting Celery worker..."
echo "📋 Available tasks will be processed from cleanup and monitoring queues"
echo "⏹️  Press Ctrl+C to stop the worker"
echo ""

# Start Celery worker
celery -A lifecycle_management.celery_config worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=cleanup,monitoring \
    --hostname=dxb-worker@%h \
    --pool=prefork

echo "🛑 Celery worker stopped" 