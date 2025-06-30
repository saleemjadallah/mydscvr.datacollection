# Hybrid Mode Deployment Guide

## 🎯 Overview

This guide explains how to enable **Hybrid Mode** for the DXB Events Collection system, which combines:

1. **Perplexity AI** extraction (primary source)
2. **Firecrawl MCP** supplemental extraction  
3. **AI image generation** for all events
4. **Automatic deduplication**

## 🚀 Quick Deployment

### On Server (Ubuntu):

```bash
# 1. Navigate to DataCollection directory
cd /home/ubuntu/DXB-events/DataCollection

# 2. Pull latest changes
git pull origin main

# 3. Run the hybrid mode enablement script
./enable_hybrid_mode.sh

# 4. Verify configuration
python verify_hybrid_mode.py
```

### On Local Machine:

```bash
# 1. Test locally first (optional)
cd DataCollection
./enable_hybrid_mode.sh

# 2. Deploy to server
git add .
git commit -m "Enable hybrid mode: Firecrawl MCP + enhanced monitoring"
git push origin main
```

## 📋 What Gets Enabled

### ✅ Firecrawl MCP Integration
- **Source Coverage**: Platinumlist, TimeOut Dubai, WhatsOn Dubai
- **Daily Limits**: 
  - Platinumlist: 20 events
  - TimeOut: 12 events  
  - WhatsOn: 8 events
- **Total Additional**: ~40 supplemental events per day

### ✅ Enhanced Monitoring
- Firecrawl API connectivity checks
- Configuration validation in cron logs
- Real-time status reporting

### ✅ Optimized Performance
- Concurrent extraction (2 threads)
- Smart rate limiting
- Timeout protection (60s per source)

## 🔧 Configuration Details

### Environment Variables Added/Updated:

```bash
# Core Hybrid Settings
ENABLE_FIRECRAWL_SUPPLEMENT=true

# Firecrawl Limits (Conservative for Stability)
FIRECRAWL_PLATINUMLIST_LIMIT=20
FIRECRAWL_TIMEOUT_LIMIT=12  
FIRECRAWL_WHATSON_LIMIT=8

# Advanced Performance Settings
FIRECRAWL_TIMEOUT_SECONDS=60
FIRECRAWL_MAX_PAGES_PER_SOURCE=40
FIRECRAWL_CONCURRENT_EXTRACTIONS=2

# AI Image Settings (Already Enabled)
ENABLE_AI_IMAGE_GENERATION=true
AI_IMAGE_BATCH_SIZE=5
AI_IMAGE_BATCH_DELAY=10
```

## 📊 Expected Impact

### 📈 Increased Event Coverage
- **Before**: ~215-370 events/day (Perplexity only)
- **After**: ~255-410 events/day (Hybrid mode)
- **Increase**: +15-20% more events

### 🎯 Improved Event Quality
- Better venue information (Platinumlist specializes in venues)
- More diverse event types (TimeOut covers lifestyle events)
- Enhanced cultural events coverage (WhatsOn Dubai)

### ⏱️ Execution Time
- **Perplexity Only**: ~15-20 seconds
- **Hybrid Mode**: ~45-60 seconds  
- **Total Increase**: ~40 seconds (still well within limits)

## 🛡️ Safety Features

### 🔒 Rate Limiting
- Conservative API call limits
- Built-in delays between requests
- Timeout protection for stuck requests

### 🔄 Fallback Protection
- Firecrawl failure won't break Perplexity extraction
- Individual source failures don't affect others
- Comprehensive error logging

### 📊 Monitoring
- Real-time status in cron logs
- API connectivity verification
- Configuration validation

## 🔍 Verification Commands

### Check Hybrid Mode Status:
```bash
python verify_hybrid_mode.py
```

### Monitor Live Execution:
```bash
tail -f logs/cron_execution.log
```

### Check Recent Extraction Sessions:
```bash
# Connect to MongoDB and check
python -c "
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv('DataCollection.env')

client = MongoClient(os.getenv('MONGO_URI'))
db = client.DXB
sessions = list(db.extraction_sessions.find().sort('started_at', -1).limit(3))
for session in sessions:
    print(f'{session[\"started_at\"]}: {session[\"extraction_method\"]} - {session[\"stored_events\"]} events')
"
```

## 🧪 Testing Hybrid Mode

### Manual Test Run:
```bash
# Activate virtual environment
source venv/bin/activate

# Run collection manually
python enhanced_collection.py

# Check results
python -c "
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv('DataCollection.env')

client = MongoClient(os.getenv('MONGO_URI'))
db = client.DXB
latest = db.extraction_sessions.find_one(sort=[('started_at', -1)])
print(f'Latest: {latest[\"extraction_method\"]} - {latest[\"stored_events\"]} events')
if 'firecrawl_events' in latest:
    print(f'Firecrawl contributed: {latest[\"firecrawl_events\"]} events')
"
```

## 🎉 Success Indicators

### ✅ Hybrid Mode Active:
- Cron logs show "🔥 Firecrawl MCP: true"
- Extraction sessions show `extraction_method: "hybrid_collection"`
- Event count increases by 15-20%
- Both Perplexity and Firecrawl events in database

### ✅ Firecrawl Working:
- No API timeout errors in logs
- Firecrawl events have `source: "Firecrawl MCP"`
- Session includes `firecrawl_events` count

### ✅ AI Images Enhanced:
- More events with successful image generation
- Diverse image styles from different sources
- Lower failure rate due to better event descriptions

## 🚨 Troubleshooting

### Issue: Firecrawl API Errors
```bash
# Check API key configuration
grep FIRECRAWL_API_KEY DataCollection.env

# Test API connectivity  
ping api.firecrawl.dev

# Reduce limits if rate limiting issues
# Edit DataCollection.env and lower FIRECRAWL_*_LIMIT values
```

### Issue: Longer Execution Times
```bash
# Check if timeout settings are appropriate
grep FIRECRAWL_TIMEOUT DataCollection.env

# Monitor execution time
tail -f logs/cron_execution.log | grep "Total execution time"
```

### Issue: Import Errors
```bash
# Reinstall requirements
source venv/bin/activate
pip install -r requirements.txt

# Test imports
python verify_hybrid_mode.py
```

## 📞 Support

If issues arise, check:
1. **Logs**: `logs/cron_execution.log`
2. **Configuration**: `python verify_hybrid_mode.py`  
3. **Database**: MongoDB extraction_sessions collection
4. **API Status**: Firecrawl and Perplexity API endpoints

## 🎯 Next Steps After Deployment

1. **Monitor First Run**: Watch the next scheduled execution (1 AM UTC)
2. **Verify Results**: Check that hybrid extraction is working
3. **Adjust Limits**: Fine-tune Firecrawl limits based on performance
4. **Document Results**: Note the improvement in event coverage

## 📊 Performance Metrics to Track

- **Total events per day** (should increase by 15-20%)
- **Execution time** (should remain under 2 minutes)
- **AI image success rate** (should improve with better descriptions)
- **Duplicate removal effectiveness** (should handle cross-source duplicates)

---

**Deployment Date**: _To be filled when deployed_  
**Deployed By**: _To be filled when deployed_  
**Status**: _To be filled when deployed_ 