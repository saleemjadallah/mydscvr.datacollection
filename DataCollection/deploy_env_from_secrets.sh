#!/bin/bash

# Deploy Environment from Secrets (Manual/Testing Version)
# This script simulates the GitHub Actions deployment process

set -e

SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR"

echo "🔐 Deploying Environment Configuration (Manual Mode)"
echo "=================================================="

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log_message "📂 Working directory: $(pwd)"

# Check if we're on the server (has access to production environment)
if [[ "$(hostname)" == *"ip-"* ]] || [[ "$(whoami)" == "ubuntu" ]]; then
    log_message "🖥️ Detected server environment"
    SERVER_MODE=true
else
    log_message "💻 Detected local environment"
    SERVER_MODE=false
fi

if [ "$SERVER_MODE" = true ]; then
    log_message "⚠️ Server deployment should use GitHub Actions for security"
    log_message "This script is for testing purposes only"
    read -p "Continue with manual deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_message "❌ Operation cancelled"
        exit 1
    fi
fi

# Create template environment files for testing
log_message "📋 Creating environment file templates..."

# Create AI_API.env template
cat > AI_API.env << 'EOF'
# AI API Keys (Replace with actual values)
OPENAI_API_KEY=your-openai-api-key-here
PERPLEXITY_API_KEY=your-perplexity-api-key-here
FIRECRAWL_API_KEY=your-firecrawl-api-key-here

# Rate limiting settings
FIRECRAWL_RATE_LIMIT=100
PERPLEXITY_RATE_LIMIT=1000

# Error handling
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5
EOF

# Create Mongo.env template
cat > Mongo.env << 'EOF'
# MongoDB Configuration (Replace with actual values)
MONGO_URI=your-mongodb-connection-string-here
EOF

# Create DataCollection.env template with hybrid mode configuration
cat > DataCollection.env << 'EOF'
# DXB Events Data Collection Pipeline - Environment Variables

# Environment Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# MongoDB Configuration
MONGO_URI=your-mongodb-connection-string-here
MONGO_USER=your-mongo-username
MONGO_PASSWORD=your-mongo-password
MONGO_DB_NAME=DXB

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Keys (REQUIRED)
FIRECRAWL_API_KEY=your-firecrawl-api-key-here
PERPLEXITY_API_KEY=your-perplexity-api-key-here
OPENAI_API_KEY=your-openai-api-key-here

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id

# Backend Integration
BACKEND_API_URL=https://yourdomain.com
BACKEND_WEBHOOK_URL=https://yourdomain.com/api/webhooks/events
BACKEND_API_KEY=your-backend-api-key

# Rate Limiting Settings
FIRECRAWL_RATE_LIMIT=100
PERPLEXITY_RATE_LIMIT=1000

# Error Handling
MAX_RETRY_ATTEMPTS=3
RETRY_DELAY_SECONDS=5

# Monitoring Configuration
METRICS_PORT=8001
ENABLE_MONITORING=true

# Scraping Configuration
DEFAULT_SCRAPING_TIMEOUT=30
MAX_CONCURRENT_SCRAPERS=3
RATE_LIMIT_DELAY=1

# AI Processing Configuration
AI_TEMPERATURE=0.7
MAX_AI_RETRIES=3
AI_TIMEOUT=30

# AI Image Generation Configuration (HYBRID MODE)
ENABLE_AI_IMAGE_GENERATION=true
AI_IMAGE_BATCH_SIZE=5
AI_IMAGE_BATCH_DELAY=10

# Firecrawl MCP Configuration (HYBRID MODE)
ENABLE_FIRECRAWL_SUPPLEMENT=true
FIRECRAWL_PLATINUMLIST_LIMIT=20
FIRECRAWL_TIMEOUT_LIMIT=12
FIRECRAWL_WHATSON_LIMIT=8
FIRECRAWL_TIMEOUT_SECONDS=60
FIRECRAWL_MAX_PAGES_PER_SOURCE=40
FIRECRAWL_CONCURRENT_EXTRACTIONS=2

# Data Quality Thresholds
MIN_QUALITY_SCORE=70
ENABLE_FAMILY_ANALYSIS=true
ENABLE_CONTENT_ENHANCEMENT=true
EOF

# Set secure permissions
chmod 600 AI_API.env Mongo.env DataCollection.env

log_message "✅ Environment file templates created"
log_message "⚠️ IMPORTANT: Replace placeholder values with actual secrets"

if [ "$SERVER_MODE" = true ]; then
    log_message "🚀 For production deployment, use:"
    log_message "   • GitHub Actions workflow (recommended)"
    log_message "   • Manual secret replacement in environment files"
else
    log_message "💻 For local testing:"
    log_message "   • Update environment files with your API keys"
    log_message "   • Run: ./enable_hybrid_mode.sh"
fi

log_message "📋 Created files:"
log_message "   • AI_API.env - AI service configuration"
log_message "   • Mongo.env - Database configuration"
log_message "   • DataCollection.env - Main configuration with hybrid mode"

echo ""
echo "🔐 SECURITY NOTES:"
echo "• Environment files are set to 600 permissions (owner read/write only)"
echo "• Never commit actual API keys to version control"
echo "• Use GitHub secrets for production deployment"
echo "• Rotate API keys regularly"

echo ""
echo "🎯 Next Steps:"
echo "1. Replace placeholder values with actual API keys"
echo "2. Run verification: python verify_hybrid_mode.py"
echo "3. Test hybrid mode: python enhanced_collection.py" 