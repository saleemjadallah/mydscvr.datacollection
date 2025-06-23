#!/bin/bash
# Deploy favorites endpoint fix to server

echo "Deploying favorites endpoint fix..."
echo "=================================="

# Server details
SERVER="ubuntu@mydscvr.xyz"
BACKEND_DIR="/home/ubuntu/DXB-events-platform/Backend"

# Copy the updated file
echo "1. Copying updated auth_with_otp.py..."
scp routers/auth_with_otp.py $SERVER:$BACKEND_DIR/routers/

# Restart the backend service
echo "2. Restarting backend service..."
ssh $SERVER "sudo systemctl restart mydscvr-backend"

# Check service status
echo "3. Checking service status..."
ssh $SERVER "sudo systemctl status mydscvr-backend --no-pager"

# Check logs for errors
echo -e "\n4. Checking recent logs..."
ssh $SERVER "sudo journalctl -u mydscvr-backend -n 20 --no-pager"

echo -e "\n✓ Deployment complete!"
echo "Test the fix at: https://api.mydscvr.ai/auth/favorites"