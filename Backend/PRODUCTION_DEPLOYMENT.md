# MyDSCVR Backend Production Deployment Guide

## ✅ Production Setup Complete

The MyDSCVR backend is now running in production mode on EC2 with the following configuration:

### 🚀 Service Details
- **Service Name**: `mydscvr-backend.service`
- **Port**: 8000
- **Status**: Active and running
- **Auto-restart**: Enabled (restarts automatically on crash)
- **Boot startup**: Enabled (starts automatically on server reboot)

### 🗄️ Database Configuration
- **Primary Database**: MongoDB Atlas
- **Database Name**: DXB
- **Total Events**: 107
- **No PostgreSQL dependencies** (removed completely)

### 🛠️ Management Commands

Use the `manage_backend.sh` script for easy management:

```bash
# Check service status
./manage_backend.sh status

# Start the service
./manage_backend.sh start

# Stop the service
./manage_backend.sh stop

# Restart the service
./manage_backend.sh restart

# View logs (last 50 lines)
./manage_backend.sh logs

# Follow logs in real-time
./manage_backend.sh follow

# Test API endpoints
./manage_backend.sh test

# Deploy code changes
./manage_backend.sh deploy
```

### 📋 Direct Server Commands

If you need to manage the service directly on the server:

```bash
# SSH into server
ssh -i mydscvrkey.pem ubuntu@3.29.102.4

# Service management
sudo systemctl status mydscvr-backend
sudo systemctl start mydscvr-backend
sudo systemctl stop mydscvr-backend
sudo systemctl restart mydscvr-backend

# View logs
sudo journalctl -u mydscvr-backend -f     # Follow logs
sudo journalctl -u mydscvr-backend -n 100 # Last 100 lines

# Check if service is enabled
sudo systemctl is-enabled mydscvr-backend
```

### 🔍 Monitoring

The backend provides these endpoints for monitoring:

- **Health Check**: `https://mydscvr.xyz/` or `https://mydscvr.xyz/api/`
- **Events API**: `https://mydscvr.xyz/api/events/`
- **API Documentation**: `https://mydscvr.xyz/docs`

### 🚨 Troubleshooting

1. **Service won't start**
   ```bash
   # Check logs for errors
   sudo journalctl -u mydscvr-backend -n 50
   
   # Check if port 8000 is in use
   sudo lsof -i :8000
   ```

2. **MongoDB connection issues**
   ```bash
   # Check environment variables
   cat /home/ubuntu/backend/.env | grep MONGO
   ```

3. **Service crashes repeatedly**
   ```bash
   # Check system resources
   free -h
   df -h
   
   # Check Python dependencies
   cd /home/ubuntu/backend
   source venv/bin/activate
   pip list
   ```

### 🔒 Security Features

The systemd service includes these security hardening features:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `ProtectSystem=strict` - Read-only system directories
- `ProtectHome=read-only` - Home directories are read-only
- Write access only to specific paths (logs, storage)

### 📊 Performance Configuration

- **Workers**: 1 (can be increased for higher load)
- **File descriptor limit**: 65536
- **Process limit**: 4096
- **Restart delay**: 10 seconds
- **Stop timeout**: 30 seconds

### 🔄 Deployment Process

When deploying new code:

1. Test locally first
2. Run deployment command:
   ```bash
   ./manage_backend.sh deploy
   ```
3. Monitor logs after deployment:
   ```bash
   ./manage_backend.sh follow
   ```
4. Test API endpoints:
   ```bash
   ./manage_backend.sh test
   ```

### 📝 Notes

- The service automatically installs missing Python dependencies on start
- Logs are managed by systemd journal (automatic rotation)
- MongoDB indexes are created automatically on startup
- Redis connection is established for caching (optional)
- Elasticsearch is optional (warnings can be ignored)

### ✨ Production Ready Features

✅ Automatic restart on failure
✅ Starts on system boot
✅ Proper signal handling (SIGTERM)
✅ Resource limits configured
✅ Security hardening applied
✅ Centralized logging
✅ MongoDB-only configuration
✅ Health check endpoints
✅ Graceful shutdown support

The backend is now fully production-ready and will maintain stable connections for your frontend application!