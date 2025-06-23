# DXB Events EC2 Deployment Guide

Complete step-by-step guide to deploy DXB Events backend with lifecycle management on Ubuntu EC2.

## 🎯 **Prerequisites**
- AWS Account with EC2 access
- MongoDB Atlas credentials (already configured)
- Local DXB Events backend code
- SSH key pair for EC2 access

---

## **Phase 1: EC2 Instance Creation**

### 1.1 Launch EC2 Instance
```bash
# AWS Console Steps:
1. Go to EC2 Dashboard → Launch Instance
2. Choose: Ubuntu Server 22.04 LTS (ami-0c7217cdde317cfec)
3. Instance Type: t3.medium (2 vCPU, 4GB RAM) - recommended for production
   - For testing: t3.micro (1 vCPU, 1GB RAM)
4. Key Pair: Create new or use existing
5. Security Group: Create with these rules:
   - SSH (22): Your IP
   - HTTP (80): 0.0.0.0/0
   - HTTPS (443): 0.0.0.0/0
   - Custom TCP (8000): 0.0.0.0/0  # FastAPI
   - Custom TCP (6379): Your IP only  # Redis (if external access needed)
6. Storage: 20GB gp3 (minimum)
7. Launch Instance
```

### 1.2 Connect to Instance
```bash
# Download your key pair and set permissions
chmod 400 mydscvrkey.pem

# Connect to instance
ssh -i mydscvrkey.pem ubuntu@YOUR-EC2-PUBLIC-IP


---

## **Phase 2: System Setup & Dependencies**

### 2.1 Update System
```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    supervisor \
    redis-server \
    htop \
    tree \
    curl \
    wget \
    unzip
```

### 2.2 Configure Redis
```bash
# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping  # Should return PONG

# Optional: Configure Redis for production
sudo nano /etc/redis/redis.conf
# Set: maxmemory 256mb
# Set: maxmemory-policy allkeys-lru
sudo systemctl restart redis-server
```

### 2.3 Create Application User
```bash
# Create dedicated user for the application
sudo adduser dxbevents
sudo usermod -aG sudo dxbevents

# Switch to application user
sudo su - dxbevents
```

---

## **Phase 3: Application Deployment**

### 3.1 Transfer Code to EC2

**Option A: Using Git (Recommended)**
```bash
# Clone from your repository
git clone https://github.com/your-username/DXB-events.git
cd DXB-events/Backend
```

**Option B: Using SCP (Direct Transfer)**
```bash
# From your local machine
scp -i mydscvrkey.pem -r /path/to/DXB-events/Backend ubuntu@YOUR-EC2-IP:/home/dxbevents/
```

### 3.2 Setup Python Environment
```bash
# Navigate to Backend directory
cd ~/DXB-events/Backend

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 3.3 Configure Environment Variables
```bash
# Copy and edit MongoDB environment file
cp Mongo.env.example Mongo.env  # If you have an example file
nano Mongo.env

# Add your MongoDB Atlas credentials:
Mongo_URI=mongodb+srv://support:olaabdel88@dxb.tq60png.mongodb.net/?retryWrites=true&w=majority&appName=DXB
MONGO_USER=support
MONGO_PASSWORD=olaabdel88
MONGO_DB_NAME=DXB
```

### 3.4 Test Application
```bash
# Test MongoDB connection
python -c "
from pymongo import MongoClient
from dotenv import load_dotenv
import os
load_dotenv('Mongo.env')
client = MongoClient(os.getenv('Mongo_URI'))
print('MongoDB connected:', client.admin.command('ping'))
"

# Test FastAPI application
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
sleep 5
curl http://localhost:8000/
# Should return: {"message":"Welcome to DXB Events API"...}

# Stop test server
pkill -f uvicorn
```

---

## **Phase 4: Production Configuration**

### 4.1 Create Systemd Service for FastAPI
```bash
sudo nano /etc/systemd/system/dxb-events.service
```

Add this content:
```ini
[Unit]
Description=DXB Events FastAPI Application
After=network.target

[Service]
Type=exec
User=dxbevents
Group=dxbevents
WorkingDirectory=/home/dxbevents/DXB-events/Backend
Environment=PATH=/home/dxbevents/DXB-events/Backend/.venv/bin
ExecStart=/home/dxbevents/DXB-events/Backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 4.2 Create Systemd Service for Celery Worker
```bash
sudo nano /etc/systemd/system/dxb-celery-worker.service
```

Add this content:
```ini
[Unit]
Description=DXB Events Celery Worker
After=network.target redis.service

[Service]
Type=exec
User=dxbevents
Group=dxbevents
WorkingDirectory=/home/dxbevents/DXB-events/Backend
Environment=PATH=/home/dxbevents/DXB-events/Backend/.venv/bin
ExecStart=/home/dxbevents/DXB-events/Backend/.venv/bin/celery -A lifecycle_management.celery_config worker --loglevel=info --concurrency=2 --queues=cleanup,monitoring --hostname=dxb-worker@%h
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.3 Create Systemd Service for Celery Beat (Scheduler)
```bash
sudo nano /etc/systemd/system/dxb-celery-beat.service
```

Add this content:
```ini
[Unit]
Description=DXB Events Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=exec
User=dxbevents
Group=dxbevents
WorkingDirectory=/home/dxbevents/DXB-events/Backend
Environment=PATH=/home/dxbevents/DXB-events/Backend/.venv/bin
ExecStart=/home/dxbevents/DXB-events/Backend/.venv/bin/celery -A lifecycle_management.celery_config beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4.4 Configure Nginx Reverse Proxy
```bash
sudo nano /etc/nginx/sites-available/dxb-events
```

Add this content:
```nginx
server {
    listen 80;
    server_name your-domain.com your-ec2-public-ip;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Serve static files (if any)
    location /static/ {
        alias /home/dxbevents/DXB-events/Backend/static/;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/;
        access_log off;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/dxb-events /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

---

## **Phase 5: Start Services**

### 5.1 Enable and Start All Services
```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable dxb-events
sudo systemctl enable dxb-celery-worker
sudo systemctl enable dxb-celery-beat
sudo systemctl enable nginx
sudo systemctl enable redis-server

# Start all services
sudo systemctl start dxb-events
sudo systemctl start dxb-celery-worker
sudo systemctl start dxb-celery-beat
sudo systemctl restart nginx
```

### 5.2 Verify Services Status
```bash
# Check service status
sudo systemctl status dxb-events
sudo systemctl status dxb-celery-worker
sudo systemctl status dxb-celery-beat
sudo systemctl status nginx
sudo systemctl status redis-server

# Check application logs
sudo journalctl -u dxb-events -f
sudo journalctl -u dxb-celery-worker -f
```

---

## **Phase 6: Testing & Verification**

### 6.1 Test API Endpoints
```bash
# Test main API
curl http://your-ec2-public-ip/

# Test lifecycle management endpoints
curl http://your-ec2-public-ip/lifecycle/health
curl http://your-ec2-public-ip/lifecycle/stats
curl http://your-ec2-public-ip/lifecycle/cost-estimate

# Test Swagger documentation
# Visit: http://your-ec2-public-ip/docs
```

### 6.2 Monitor System Resources
```bash
# Check system resources
htop

# Check disk usage
df -h

# Check memory usage
free -h

# Check application processes
ps aux | grep -E "(uvicorn|celery|nginx)"
```

---

## **Phase 7: Security & Maintenance**

### 7.1 Setup Firewall (UFW)
```bash
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS (for future SSL)
sudo ufw status
```

### 7.2 Create Backup Script
```bash
nano ~/backup_dxb.sh
```

Add this content:
```bash
#!/bin/bash
# DXB Events Backup Script

BACKUP_DIR="/home/dxbevents/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup application code
tar -czf $BACKUP_DIR/dxb-backend-$DATE.tar.gz /home/dxbevents/DXB-events/Backend/

# Backup logs
sudo tar -czf $BACKUP_DIR/dxb-logs-$DATE.tar.gz /var/log/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

Make executable and setup cron:
```bash
chmod +x ~/backup_dxb.sh

# Add to crontab (daily backup at 2 AM)
crontab -e
# Add: 0 2 * * * /home/dxbevents/backup_dxb.sh
```

### 7.3 Log Rotation
```bash
sudo nano /etc/logrotate.d/dxb-events
```

Add this content:
```
/var/log/dxb-events/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
}
```

---

## **Phase 8: SSL Certificate (Optional but Recommended)**

### 8.1 Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 8.2 Obtain SSL Certificate
```bash
# Replace with your domain
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## **🎯 Final Verification Checklist**

- [ ] EC2 instance running Ubuntu 22.04
- [ ] All dependencies installed
- [ ] MongoDB Atlas connection working
- [ ] Redis server running
- [ ] FastAPI application running on port 8000
- [ ] Celery worker processing tasks
- [ ] Celery beat scheduler running
- [ ] Nginx reverse proxy configured
- [ ] All systemd services enabled and started
- [ ] API endpoints responding correctly
- [ ] Lifecycle management endpoints working
- [ ] Firewall configured
- [ ] Backup script created
- [ ] Log rotation configured
- [ ] SSL certificate installed (optional)

---

## **🚨 Troubleshooting**

### Common Issues and Solutions:

**Service won't start:**
```bash
sudo journalctl -u service-name -f
sudo systemctl reset-failed service-name
sudo systemctl restart service-name
```

**MongoDB connection issues:**
```bash
# Check environment variables
cat ~/DXB-events/Backend/Mongo.env

# Test connection
cd ~/DXB-events/Backend
source .venv/bin/activate
python3 -c "from database import mongodb_client; print(mongodb_client.admin.command('ping'))"
```

**Celery issues:**
```bash
# Check Redis
redis-cli ping

# Test Celery configuration
cd ~/DXB-events/Backend
source .venv/bin/activate
python3 -c "from lifecycle_management.celery_config import celery_app; print('Tasks:', list(celery_app.tasks.keys()))"
```

**Memory issues on t3.micro:**
```bash
# Create swap file
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## **📊 Performance Monitoring**

Monitor your deployment with:
- `htop` - System resources
- `sudo journalctl -u dxb-events -f` - Application logs
- `curl http://localhost/lifecycle/health` - API health
- `redis-cli info memory` - Redis memory usage

Your DXB Events backend with lifecycle management is now deployed and ready for production! 🎉 