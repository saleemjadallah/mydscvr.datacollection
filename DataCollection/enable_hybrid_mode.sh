#!/bin/bash

# Enable Hybrid Mode Script for DXB Events Collection
# This script enables Firecrawl MCP supplemental extraction alongside Perplexity AI

set -e

SCRIPT_DIR="$(dirname "$0")"
ENV_FILE="$SCRIPT_DIR/DataCollection.env"

echo "🚀 Enabling Hybrid Mode for DXB Events Collection"
echo "=================================================="

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if running on the correct server
if [[ "$(hostname)" != *"ubuntu"* ]] && [[ "$(whoami)" != "ubuntu" ]]; then
    log_message "⚠️ WARNING: This script is designed to run on the Ubuntu server"
    log_message "Current user: $(whoami), hostname: $(hostname)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_message "❌ Operation cancelled"
        exit 1
    fi
fi

# Change to script directory
cd "$SCRIPT_DIR" || {
    log_message "❌ FATAL: Cannot change to script directory: $SCRIPT_DIR"
    exit 1
}

log_message "📂 Working directory: $(pwd)"

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    log_message "❌ DataCollection.env file not found. Creating from template..."
    
    if [ -f "DataCollection.env.example" ]; then
        cp "DataCollection.env.example" "$ENV_FILE"
        log_message "✅ Created DataCollection.env from template"
        log_message "⚠️ Please configure the required API keys and settings"
    else
        log_message "❌ DataCollection.env.example not found"
        exit 1
    fi
fi

# Backup current configuration
BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$BACKUP_FILE"
log_message "💾 Backed up current config to: $BACKUP_FILE"

# Function to update or add environment variable
update_env_var() {
    local var_name="$1"
    local var_value="$2"
    local file="$3"
    
    if grep -q "^${var_name}=" "$file"; then
        # Update existing variable (macOS and Linux compatible)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i "" "s/^${var_name}=.*/${var_name}=${var_value}/" "$file"
        else
            sed -i "s/^${var_name}=.*/${var_name}=${var_value}/" "$file"
        fi
        log_message "✅ Updated $var_name=$var_value"
    else
        # Add new variable
        echo "${var_name}=${var_value}" >> "$file"
        log_message "✅ Added $var_name=$var_value"
    fi
}

log_message "🔧 Configuring hybrid mode settings..."

# Enable Firecrawl MCP supplement
update_env_var "ENABLE_FIRECRAWL_SUPPLEMENT" "true" "$ENV_FILE"

# Ensure AI image generation is enabled
update_env_var "ENABLE_AI_IMAGE_GENERATION" "true" "$ENV_FILE"

# Set optimal Firecrawl limits for hybrid mode
update_env_var "FIRECRAWL_PLATINUMLIST_LIMIT" "20" "$ENV_FILE"
update_env_var "FIRECRAWL_TIMEOUT_LIMIT" "12" "$ENV_FILE"
update_env_var "FIRECRAWL_WHATSON_LIMIT" "8" "$ENV_FILE"

# Set advanced Firecrawl settings
update_env_var "FIRECRAWL_TIMEOUT_SECONDS" "60" "$ENV_FILE"
update_env_var "FIRECRAWL_MAX_PAGES_PER_SOURCE" "40" "$ENV_FILE"
update_env_var "FIRECRAWL_CONCURRENT_EXTRACTIONS" "2" "$ENV_FILE"

# Set AI image generation batch settings
update_env_var "AI_IMAGE_BATCH_SIZE" "5" "$ENV_FILE"
update_env_var "AI_IMAGE_BATCH_DELAY" "10" "$ENV_FILE"

log_message "🔍 Verifying configuration..."

# Check required variables
REQUIRED_VARS=("ENABLE_FIRECRAWL_SUPPLEMENT" "FIRECRAWL_API_KEY" "PERPLEXITY_API_KEY" "OPENAI_API_KEY" "MONGO_URI")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" "$ENV_FILE" || grep -q "^${var}=$" "$ENV_FILE" || grep -q "^${var}=your-" "$ENV_FILE"; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log_message "⚠️ The following variables need to be configured:"
    for var in "${MISSING_VARS[@]}"; do
        log_message "   ❌ $var"
    done
    log_message ""
    log_message "Please edit $ENV_FILE and set the required values"
    log_message "Then run this script again to verify the configuration"
    exit 1
fi

log_message "✅ All required variables are configured"

# Test virtual environment and dependencies
log_message "🔍 Checking virtual environment and dependencies..."

if [ ! -d "venv" ]; then
    log_message "❌ Virtual environment not found. Please create it first:"
    log_message "   python3 -m venv venv"
    log_message "   source venv/bin/activate"
    log_message "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment and test imports
if source venv/bin/activate; then
    log_message "✅ Virtual environment activated"
    
    # Test critical imports
    python -c "
try:
    from firecrawl_mcp_extractor import FirecrawlMCPExtractor
    from perplexity_events_extractor import DubaiEventsPerplexityExtractor
    from ai_image_service_hybrid import HybridAIImageService
    print('✅ All hybrid mode modules can be imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
" || {
        log_message "❌ Python dependency check failed"
        log_message "Please ensure all requirements are installed:"
        log_message "   pip install -r requirements.txt"
        exit 1
    }
else
    log_message "❌ Failed to activate virtual environment"
    exit 1
fi

# Display current configuration
log_message "📋 Current hybrid mode configuration:"
log_message "   🔥 Firecrawl MCP: $(grep "ENABLE_FIRECRAWL_SUPPLEMENT" "$ENV_FILE" | cut -d'=' -f2)"
log_message "   🎨 AI Images: $(grep "ENABLE_AI_IMAGE_GENERATION" "$ENV_FILE" | cut -d'=' -f2)"
log_message "   📊 Platinumlist Limit: $(grep "FIRECRAWL_PLATINUMLIST_LIMIT" "$ENV_FILE" | cut -d'=' -f2)"
log_message "   ⏱️ Timeout Limit: $(grep "FIRECRAWL_TIMEOUT_LIMIT" "$ENV_FILE" | cut -d'=' -f2)"
log_message "   📑 WhatsOn Limit: $(grep "FIRECRAWL_WHATSON_LIMIT" "$ENV_FILE" | cut -d'=' -f2)"

log_message ""
log_message "🎉 Hybrid mode has been successfully enabled!"
log_message "🚀 The next scheduled collection will use:"
log_message "   1. Perplexity AI extraction (primary)"
log_message "   2. Firecrawl MCP supplemental extraction"
log_message "   3. AI image generation for all events"
log_message "   4. Automatic deduplication"
log_message ""
log_message "📝 To manually test hybrid mode:"
log_message "   python enhanced_collection.py"
log_message ""
log_message "📊 To monitor the next scheduled run:"
log_message "   tail -f logs/cron_execution.log"

# Create a verification script
cat > "verify_hybrid_mode.py" << 'EOF'
#!/usr/bin/env python3
"""Quick verification script for hybrid mode configuration"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv('DataCollection.env')

def check_config():
    print("🔍 Verifying Hybrid Mode Configuration")
    print("=" * 40)
    
    # Check Firecrawl MCP
    firecrawl_enabled = os.getenv('ENABLE_FIRECRAWL_SUPPLEMENT', 'false').lower() == 'true'
    print(f"🔥 Firecrawl MCP: {'✅ ENABLED' if firecrawl_enabled else '❌ DISABLED'}")
    
    # Check AI Images
    ai_enabled = os.getenv('ENABLE_AI_IMAGE_GENERATION', 'true').lower() == 'true'
    print(f"🎨 AI Images: {'✅ ENABLED' if ai_enabled else '❌ DISABLED'}")
    
    # Check API keys
    apis = {
        'Firecrawl': 'FIRECRAWL_API_KEY',
        'Perplexity': 'PERPLEXITY_API_KEY', 
        'OpenAI': 'OPENAI_API_KEY',
        'MongoDB': 'MONGO_URI'
    }
    
    for name, key in apis.items():
        value = os.getenv(key, '')
        configured = value and not value.startswith('your-') and len(value) > 10
        print(f"🔑 {name}: {'✅ CONFIGURED' if configured else '❌ MISSING'}")
    
    print("\n🎯 Status: ", end="")
    if firecrawl_enabled and ai_enabled:
        print("✅ HYBRID MODE ACTIVE")
        return True
    else:
        print("❌ HYBRID MODE INACTIVE")
        return False

if __name__ == "__main__":
    success = check_config()
    exit(0 if success else 1)
EOF

chmod +x "verify_hybrid_mode.py"
log_message "📋 Created verification script: verify_hybrid_mode.py"

log_message "✅ Hybrid mode enablement completed successfully!" 