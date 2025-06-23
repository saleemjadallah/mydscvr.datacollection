#!/bin/bash
# MyDSCVR Backend Management Script
# Production-ready systemd service management

SERVER="ubuntu@3.29.102.4"
SSH_KEY="mydscvrkey.pem"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

case "$1" in
  status)
    echo "🔍 Checking MyDSCVR Backend Status..."
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl status mydscvr-backend --no-pager"
    ;;
    
  start)
    echo "🚀 Starting MyDSCVR Backend..."
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl start mydscvr-backend"
    sleep 5
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl status mydscvr-backend --no-pager | head -10"
    ;;
    
  stop)
    echo "🛑 Stopping MyDSCVR Backend..."
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl stop mydscvr-backend"
    print_status "Backend stopped"
    ;;
    
  restart)
    echo "🔄 Restarting MyDSCVR Backend..."
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl restart mydscvr-backend"
    sleep 5
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl status mydscvr-backend --no-pager | head -10"
    ;;
    
  logs)
    echo "📋 MyDSCVR Backend Logs (last 50 lines)..."
    ssh -i "$SSH_KEY" "$SERVER" "sudo journalctl -u mydscvr-backend -n 50 --no-pager"
    ;;
    
  follow)
    echo "📋 Following MyDSCVR Backend Logs (Ctrl+C to exit)..."
    ssh -i "$SSH_KEY" "$SERVER" "sudo journalctl -u mydscvr-backend -f"
    ;;
    
  test)
    echo "🧪 Testing MyDSCVR Backend API..."
    echo ""
    echo "Health Check:"
    ssh -i "$SSH_KEY" "$SERVER" "curl -s http://localhost:8000/ | jq ."
    echo ""
    echo "Events API:"
    ssh -i "$SSH_KEY" "$SERVER" "curl -s http://localhost:8000/api/events/ | jq '.pagination'"
    ;;
    
  deploy)
    echo "🚀 Deploying Backend Code..."
    rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
      --exclude='.git' --exclude='logs' --exclude='*.log' \
      -e "ssh -i $SSH_KEY" Backend/ "$SERVER:/home/ubuntu/backend/"
    
    print_status "Code deployed, restarting service..."
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl restart mydscvr-backend"
    sleep 5
    ssh -i "$SSH_KEY" "$SERVER" "sudo systemctl status mydscvr-backend --no-pager | head -10"
    ;;
    
  *)
    echo "🛠️  MyDSCVR Backend Management"
    echo ""
    echo "Usage: $0 {status|start|stop|restart|logs|follow|test|deploy}"
    echo ""
    echo "Commands:"
    echo "  status  - Check service status"
    echo "  start   - Start the backend service"
    echo "  stop    - Stop the backend service"
    echo "  restart - Restart the backend service"
    echo "  logs    - View last 50 log entries"
    echo "  follow  - Follow logs in real-time"
    echo "  test    - Test API endpoints"
    echo "  deploy  - Deploy code and restart service"
    exit 1
    ;;
esac