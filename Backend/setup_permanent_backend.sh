#!/bin/bash
# Setup permanent backend service to prevent disconnection issues
# This creates a systemd service for automatic restart and management

echo "🔧 Setting up permanent MyDSCVR Backend Service..."

# Configuration
SERVER_USER="ubuntu"
SERVER_HOST="3.29.102.4"
SSH_KEY="mydscvrkey.pem"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# Step 1: Upload service file
print_status "Uploading systemd service file..."
scp -i "$SSH_KEY" mydscvr-backend.service "$SERVER_USER@$SERVER_HOST:/tmp/"

# Step 2: Setup systemd service
print_status "Setting up systemd service..."
ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" << 'EOF'
# Stop any existing backend processes
sudo pkill -f "uvicorn main:app" || true
sleep 2

# Move service file to systemd directory
sudo mv /tmp/mydscvr-backend.service /etc/systemd/system/

# Set proper permissions
sudo chmod 644 /etc/systemd/system/mydscvr-backend.service

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable mydscvr-backend

# Start the service
sudo systemctl start mydscvr-backend

# Wait for service to start
sleep 5

# Check service status
sudo systemctl status mydscvr-backend --no-pager
EOF

# Step 3: Verify service is running
print_status "Verifying backend service..."
sleep 3

HEALTH_CHECK=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "curl -s http://localhost:8000/ | grep -o '\"status\":\"healthy\"' || echo 'FAILED'")

if [[ $HEALTH_CHECK == *"healthy"* ]]; then
    print_status "🎉 Backend service is running and healthy!"
else
    print_error "Backend service failed to start properly"
fi

# Step 4: Test API endpoints
print_status "Testing API endpoints..."

# Test events
EVENTS_TEST=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "timeout 10 curl -s http://localhost:8000/api/events | head -c 50")
if [[ $EVENTS_TEST == *"["* ]] || [[ $EVENTS_TEST == *"events"* ]]; then
    print_status "Events API is responding"
else
    print_warning "Events API may need attention"
fi

# Test auth
AUTH_TEST=$(ssh -i "$SSH_KEY" "$SERVER_USER@$SERVER_HOST" "timeout 10 curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/auth/test-email?recipient_email=test@test.com -X POST")
if [[ $AUTH_TEST == "200" ]]; then
    print_status "Auth API is responding"
else
    print_warning "Auth API returned status: $AUTH_TEST"
fi

print_status "🎉 Permanent backend service setup completed!"
echo ""
echo "📋 Service Management Commands:"
echo "   Start:   sudo systemctl start mydscvr-backend"
echo "   Stop:    sudo systemctl stop mydscvr-backend"
echo "   Restart: sudo systemctl restart mydscvr-backend"
echo "   Status:  sudo systemctl status mydscvr-backend"
echo "   Logs:    sudo journalctl -u mydscvr-backend -f"
echo ""
echo "🔄 The service will now automatically:"
echo "   ✅ Start on server boot"
echo "   ✅ Restart if it crashes"
echo "   ✅ Maintain stable connections"
echo "   ✅ Log to system journal"