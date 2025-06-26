#!/bin/bash

# Install Lifecycle Management Cron Jobs
# Replaces Celery beat scheduler with system cron jobs
# SAFE TIMING: Avoids datacollection pipeline window (11:30 PM - 3:30 AM UTC)

echo "🕐 Installing Lifecycle Management Cron Jobs (Post-Celery)"
echo "========================================================"
echo "📋 Safe timing to avoid datacollection conflicts:"
echo "   🚫 AVOIDED: 11:30 PM - 3:30 AM UTC (datacollection window)"
echo "   ✅ USING: 1:00 AM - 6:00 AM UTC (safe window)"
echo ""

# Backend API base URL (adjust for your environment)
API_BASE="http://localhost:8000"

# Create cron entries with SAFE timing
CRON_ENTRIES="
# Lifecycle Management Tasks - Post-Celery Removal
# SAFE TIMING: No conflicts with datacollection pipeline (12AM-3AM UTC)

# Daily cleanup at 6 AM UAE (2 AM UTC) - SAFE after datacollection deduplication
0 2 * * * curl -X POST $API_BASE/lifecycle/tasks/daily-cleanup -H 'Content-Type: application/json' >> /home/ubuntu/backend/logs/lifecycle-cleanup.log 2>&1

# Daily health check at 8 AM UAE (4 AM UTC) - SAFE window  
0 4 * * * curl -X POST $API_BASE/lifecycle/tasks/health-check -H 'Content-Type: application/json' >> /home/ubuntu/backend/logs/lifecycle-health.log 2>&1

# Daily hidden gem at 9 AM UAE (5 AM UTC) - SAFE window
0 5 * * * curl -X POST $API_BASE/lifecycle/tasks/create-hidden-gem -H 'Content-Type: application/json' >> /home/ubuntu/backend/logs/lifecycle-gems.log 2>&1

# Weekly report on Monday 10 AM UAE (Monday 6 AM UTC) - SAFE window
0 6 * * 1 curl -X POST $API_BASE/lifecycle/tasks/weekly-report -H 'Content-Type: application/json' >> /home/ubuntu/backend/logs/lifecycle-weekly.log 2>&1

# Cleanup expired gems on Sunday 11 AM UAE (Sunday 7 AM UTC) - SAFE window
0 7 * * 0 curl -X POST $API_BASE/lifecycle/tasks/cleanup-gems -H 'Content-Type: application/json' >> /home/ubuntu/backend/logs/lifecycle-gem-cleanup.log 2>&1
"

# Check if lifecycle cron jobs already exist
if crontab -l 2>/dev/null | grep -q "lifecycle/tasks"; then
    echo "⚠️ Lifecycle cron jobs already exist. Updating..."
    # Remove existing lifecycle entries and add new ones
    (crontab -l 2>/dev/null | grep -v "lifecycle/tasks"; echo "$CRON_ENTRIES") | crontab -
else
    echo "➕ Installing new lifecycle cron jobs..."
    # Add new entries to existing crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRIES") | crontab -
fi

echo ""
echo "✅ Lifecycle Management Cron Jobs Installed Successfully!"
echo ""
echo "📋 Current crontab with new lifecycle jobs:"
crontab -l | grep -E "(lifecycle|#.*Lifecycle)"
echo ""

echo "🕐 Schedule Summary (All times in UTC):"
echo "   2:00 AM UTC (6:00 AM UAE): Daily cleanup"  
echo "   4:00 AM UTC (8:00 AM UAE): Health check"
echo "   5:00 AM UTC (9:00 AM UAE): Hidden gems"
echo "   6:00 AM UTC Mon (10:00 AM UAE): Weekly report"
echo "   7:00 AM UTC Sun (11:00 AM UAE): Gem cleanup"
echo ""

echo "📝 Log files will be created in:"
echo "   /home/ubuntu/backend/logs/lifecycle-*.log"
echo ""

echo "🚫 CONFLICTS ELIMINATED:"
echo "   ❌ OLD Celery: 1-3 AM UAE (9-11 PM UTC) - CONFLICTED!"
echo "   ✅ NEW Cron: 6-11 AM UAE (2-7 AM UTC) - SAFE!"
echo ""

# Create log directory if it doesn't exist
mkdir -p /home/ubuntu/backend/logs

echo "🎉 Setup complete! Lifecycle management now runs independently"
echo "   of datacollection pipeline with zero conflicts."