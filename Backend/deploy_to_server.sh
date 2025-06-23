#!/bin/bash
# Permanent deployment script for MyDSCVR Backend
# This ensures proper service restart and connection stability

echo "🚀 Starting MyDSCVR Backend Deployment..."

# Configuration
SERVER_USER="ubuntu"
SERVER_HOST="3.29.102.4"
SSH_KEY="mydscvrkey.pem"
BACKEND_DIR="/home/ubuntu/backend"
TEMP_DIR="/tmp/mydscvr_deploy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Step 1: Create deployment package
print_status "Creating deployment package..."
mkdir -p "$TEMP_DIR"

# Copy all backend files to temp directory
rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='logs' --exclude='*.log' \
    ./ "$TEMP_DIR/"

# Step 2: Upload files to server
print_status "Uploading files to server..."
rsync -av -e "ssh -i $SSH_KEY" "$TEMP_DIR/" "$SERVER_USER@$SERVER_HOST:$BACKEND_DIR/"

# Step 3: Check if backend is running and get PID
print_status "Checking current backend status..."
BACKEND_PID=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "ps aux | grep 'python -m uvicorn main:app' | grep -v grep | awk '{print \$2}'")

if [ ! -z "$BACKEND_PID" ]; then
    print_warning "Backend is running with PID: $BACKEND_PID"
    print_status "Gracefully stopping backend..."
    
    # Graceful shutdown first
    ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "kill -TERM $BACKEND_PID"
    sleep 3
    
    # Check if it's still running
    STILL_RUNNING=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "ps -p $BACKEND_PID -o pid= 2>/dev/null")
    if [ ! -z "$STILL_RUNNING" ]; then
        print_warning "Force killing backend process..."
        ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "kill -KILL $BACKEND_PID"
        sleep 2
    fi
else
    print_warning "No backend process found running"
fi

# Step 4: Install/update dependencies
print_status "Installing dependencies..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "cd $BACKEND_DIR && source venv/bin/activate && pip install -r requirements.txt --quiet"

# Step 5: Test configuration
print_status "Testing backend configuration..."
CONFIG_TEST=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "cd $BACKEND_DIR && source venv/bin/activate && python -c 'import main; print(\"✅ Configuration OK\")' 2>&1")

if [[ $CONFIG_TEST != *"Configuration OK"* ]]; then
    print_error "Configuration test failed: $CONFIG_TEST"
fi

# Step 6: Start backend with proper logging
print_status "Starting backend service..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "cd $BACKEND_DIR && source venv/bin/activate && nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info > backend.log 2>&1 & echo \$! > backend.pid"

# Step 7: Wait for backend to start
print_status "Waiting for backend to start..."
sleep 5

# Step 8: Verify backend is running
for i in {1..10}; do
    print_status "Health check attempt $i/10..."
    
    HEALTH_CHECK=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "curl -s http://localhost:8000/ | grep -o '\"status\":\"healthy\"' || echo 'FAILED'")
    
    if [[ $HEALTH_CHECK == *"healthy"* ]]; then
        print_status "Backend is healthy and responding!"
        break
    elif [ $i -eq 10 ]; then
        print_error "Backend failed to start properly after 10 attempts"
    else
        print_warning "Backend not ready yet, waiting 3 seconds..."
        sleep 3
    fi
done

# Step 9: Test key endpoints
print_status "Testing key API endpoints..."

# Test events endpoint
EVENTS_TEST=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "curl -s http://localhost:8000/api/events | head -c 100")
if [[ $EVENTS_TEST == *"events"* ]] || [[ $EVENTS_TEST == *"["* ]]; then
    print_status "Events API is working"
else
    print_warning "Events API may have issues"
fi

# Test auth endpoint
AUTH_TEST=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/auth/test-email?recipient_email=test@test.com -X POST")
if [[ $AUTH_TEST == "200" ]]; then
    print_status "Auth API is working"
else
    print_warning "Auth API returned status: $AUTH_TEST"
fi

# Step 10: Display backend status
print_status "Getting backend process info..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "ps aux | grep 'python -m uvicorn main:app' | grep -v grep"

# Step 11: Show recent logs
print_status "Recent backend logs:"
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "cd $BACKEND_DIR && tail -10 backend.log"

# Step 12: Cleanup
print_status "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

print_status "🎉 Deployment completed successfully!"
print_status "Backend is running on: https://mydscvr.xyz"
print_status "API Documentation: https://mydscvr.xyz/docs"

echo ""
echo "📋 Deployment Summary:"
echo "   ✅ Files uploaded and updated"
echo "   ✅ Dependencies installed"
echo "   ✅ Backend service restarted"
echo "   ✅ Health checks passed"
echo "   ✅ API endpoints tested"
echo ""
echo "🔗 You can now test the frontend at: https://mydscvr.ai"