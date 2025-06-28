#!/bin/bash

# June 28th AI Image Generation Fix Script
# Generates missing AI images for events collected on June 28th, 2025

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="fix_june28_missing_images.py"
LOG_FILE="logs/june28_image_fix_run.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log_with_timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] $1" | tee -a "$SCRIPT_DIR/$LOG_FILE"
}

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_with_timestamp "$message"
}

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

print_status $BLUE "🚀 Starting June 28th AI Image Generation Fix"
print_status $BLUE "=============================================="
log_with_timestamp "Script started from: $SCRIPT_DIR"
log_with_timestamp "Target script: $PYTHON_SCRIPT"

# Change to script directory
cd "$SCRIPT_DIR" || {
    print_status $RED "❌ FATAL: Cannot change to script directory: $SCRIPT_DIR"
    exit 1
}

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    print_status $RED "❌ FATAL: Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

print_status $GREEN "✅ Python script found: $PYTHON_SCRIPT"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status $RED "❌ FATAL: Virtual environment not found. Please create it first:"
    print_status $YELLOW "   python -m venv venv"
    print_status $YELLOW "   source venv/bin/activate"
    print_status $YELLOW "   pip install -r requirements.txt"
    exit 1
fi

print_status $GREEN "✅ Virtual environment found"

# Activate virtual environment
print_status $BLUE "🔧 Activating virtual environment..."
source venv/bin/activate

if [ "$VIRTUAL_ENV" ]; then
    print_status $GREEN "✅ Virtual environment activated: $VIRTUAL_ENV"
else
    print_status $RED "❌ FATAL: Virtual environment activation failed"
    exit 1
fi

# Check environment files
print_status $BLUE "🔍 Checking environment files..."
for env_file in "AI_API.env" "Mongo.env"; do
    if [ -f "$env_file" ]; then
        print_status $GREEN "✅ Environment file found: $env_file"
    else
        print_status $RED "❌ FATAL: Environment file missing: $env_file"
        exit 1
    fi
done

# Check if OpenAI API key is configured
if grep -q "OPENAI_API_KEY=sk-" "AI_API.env"; then
    print_status $GREEN "✅ OpenAI API key configured"
else
    print_status $RED "❌ FATAL: OpenAI API key not properly configured in AI_API.env"
    exit 1
fi

# Check if MongoDB URI is configured
if grep -q "Mongo_URI=mongodb" "Mongo.env"; then
    print_status $GREEN "✅ MongoDB URI configured"
else
    print_status $RED "❌ FATAL: MongoDB URI not properly configured in Mongo.env"
    exit 1
fi

# Display estimated execution info
print_status $YELLOW "📊 Execution Information:"
print_status $YELLOW "   • Target: Events from June 28th, 2025 missing AI images"
print_status $YELLOW "   • Expected: ~285 events to process"
print_status $YELLOW "   • Batch size: 5 events per batch (configurable)"
print_status $YELLOW "   • Batch delay: 10 seconds between batches"
print_status $YELLOW "   • Estimated time: ~15-20 minutes"
print_status $YELLOW "   • Log file: $LOG_FILE"

# Ask for confirmation
print_status $YELLOW "⚠️  This will generate AI images using OpenAI DALL-E 3 API"
print_status $YELLOW "   Cost estimate: ~$0.04 per image × 285 images ≈ $11.40"
echo ""
read -p "Do you want to continue? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status $YELLOW "❌ Operation cancelled by user"
    exit 0
fi

# Start the fix
print_status $BLUE "🎨 Starting AI image generation fix..."
print_status $BLUE "=============================================="
log_with_timestamp "Starting Python script execution"

# Execute the Python script
python "$PYTHON_SCRIPT" 2>&1 | while IFS= read -r line; do
    echo "$line"
    echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] PYTHON: $line" >> "$SCRIPT_DIR/$LOG_FILE"
done

# Capture exit code
PYTHON_EXIT_CODE=${PIPESTATUS[0]}

print_status $BLUE "=============================================="
log_with_timestamp "Python script completed with exit code: $PYTHON_EXIT_CODE"

if [ $PYTHON_EXIT_CODE -eq 0 ]; then
    print_status $GREEN "✅ SUCCESS: June 28th AI image fix completed successfully!"
    print_status $GREEN "📋 Check the logs for detailed results:"
    print_status $GREEN "   • Execution log: $LOG_FILE"
    print_status $GREEN "   • Detailed log: logs/june28_image_fix.log"
else
    print_status $RED "❌ FAILURE: June 28th AI image fix failed with exit code $PYTHON_EXIT_CODE"
    print_status $RED "📋 Check the logs for error details:"
    print_status $RED "   • Execution log: $LOG_FILE"
    print_status $RED "   • Detailed log: logs/june28_image_fix.log"
fi

print_status $BLUE "🏁 June 28th AI Image Fix Script Completed"
print_status $BLUE "=============================================="

exit $PYTHON_EXIT_CODE 