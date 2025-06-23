#!/bin/bash

# DXB Events EC2 Deployment Script
# Run this script on your Ubuntu EC2 instance

echo "🚀 DXB Events EC2 Deployment Starting..."
echo "=" * 50

# Phase 2: System Setup & Dependencies
echo "📦 Phase 2: Installing System Dependencies..."

# Update system
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

echo "✅ System packages installed"

# Configure Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping
echo "✅ Redis configured and running"

# Create application user
sudo adduser --disabled-password --gecos "" dxbevents
sudo usermod -aG sudo dxbevents

echo "✅ Application user 'dxbevents' created"

# Switch to application user for the rest
echo "🔄 Switching to dxbevents user..."
echo "Please run the following commands manually:"
echo "sudo su - dxbevents"
echo "Then continue with Phase 3..."

echo ""
echo "🎯 Next Steps:"
echo "1. Run: sudo su - dxbevents"
echo "2. Upload your Backend code"
echo "3. Set up Python environment"
echo "4. Configure services" 