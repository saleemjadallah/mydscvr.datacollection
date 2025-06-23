# DXB Events Data Lifecycle Management

## Overview

The DXB Events Data Lifecycle Management system provides automated retention policies, cleanup, and monitoring for scraped event data from 13 Dubai/UAE event sources. This system ensures optimal storage costs while maintaining high-quality family-focused event coverage.

## Features

### 🎯 Source-Prioritized Retention Strategy
- **High Priority** (7-day retention): Dubai Calendar, Time Out Dubai, Time Out Kids UAE, Platinumlist
- **Medium Priority** (3-day retention): Eventbrite, Meetup, What's On Dubai, etc.
- **Low Priority** (1-day retention): 7G Media, Social Rising, Instagram Influencers

### 💾 Smart Storage Management
- Automatic deletion based on `end_date + retention_days`
- MongoDB indexes optimized for efficient cleanup queries
- Soft delete with 24-hour grace period before hard deletion

### 🔄 Automated Cleanup
- **Daily Tasks**: Source-based cleanup at 3 AM UAE time
- **Weekly Tasks**: Comprehensive reports on Monday 4 AM UAE time
- **Health Monitoring**: Daily storage health checks at 2 AM UAE time
- **Emergency Cleanup**: Every 6 hours for critical issues

### 📊 Built-in Monitoring
- Storage health checks with automated alerts
- Cost estimation and efficiency tracking
- Source performance analysis
- Weekly comprehensive reports

## Installation

### 1. Install Dependencies
```bash
cd Backend
pip install -r requirements.txt
```

### 2. Setup Redis (for Celery)
```bash
# Using Docker
docker run -d -p 6379:6379 redis:alpine

# Or install locally
# macOS: brew install redis
# Ubuntu: sudo apt-get install redis-server
```

### 3. Configure Environment
Ensure your `Mongo.env` has the correct MongoDB Atlas credentials (already configured).

### 4. Initialize Database Indexes
The system will automatically create necessary indexes on startup, including:
- Lifecycle management indexes
- TTL-based cleanup indexes
- Source and priority-based indexes

## Usage

### Starting the Celery Worker
```bash
cd Backend
celery -A lifecycle_management.celery_config:celery_app worker --loglevel=info --queues=cleanup,monitoring
```

### Starting the Celery Beat Scheduler
```bash
cd Backend
celery -A lifecycle_management.celery_config:celery_app beat --loglevel=info
```

### Starting the FastAPI Server
```bash
cd Backend
uvicorn main:app --reload
```

## API Endpoints

### Health and Monitoring
- `GET /lifecycle/health` - Storage health status
- `GET /lifecycle/stats` - Retention statistics
- `GET /lifecycle/cost-estimate` - Storage cost estimates
- `GET /lifecycle/weekly-report` - Comprehensive weekly report

### Management Operations
- `POST /lifecycle/setup-retention` - Setup retention policies
- `POST /lifecycle/cleanup/manual` - Manual cleanup
- `POST /lifecycle/cleanup/source` - Clean specific source
- `POST /lifecycle/events/store` - Store events with lifecycle management

### Task Management
- `POST /lifecycle/tasks/trigger-cleanup` - Trigger cleanup task
- `POST /lifecycle/tasks/trigger-health-check` - Trigger health check
- `GET /lifecycle/tasks/{task_id}/status` - Get task status

### System Information
- `GET /lifecycle/policies` - Current retention policies
- `GET /lifecycle/system-info` - System configuration

## Configuration

### Source Priority Configuration
The system automatically classifies sources based on family-relevance and conversion potential:

```python
RETENTION_POLICIES = {
    'high': {
        'sources': ['dubai_calendar', 'timeout_dubai', 'timeout_kids_uae', 'platinumlist'],
        'retention_days': 7,
        'reason': 'High-value family events, keep for analytics'
    },
    'medium': {
        'sources': ['eventbrite_dubai', 'meetup_dubai', 'whats_on_dubai', 
                   'timeout_market_dubai', 'timeout_dxb', 'dubai_web_events'],
        'retention_days': 3,
        'reason': 'Good coverage, moderate retention'
    },
    'low': {
        'sources': ['7g_media', 'social_rising', 'instagram_influencers'],
        'retention_days': 1,
        'reason': 'Limited family appeal, minimal retention'
    }
}
```

### Automated Schedule
```python
CELERY_BEAT_SCHEDULE = {
    'daily-cleanup': crontab(hour=3, minute=0),       # 3 AM UAE daily
    'weekly-report': crontab(hour=4, minute=0, day_of_week=1),  # Monday 4 AM
    'health-check': crontab(hour=2, minute=0),        # 2 AM daily
    'retention-setup': crontab(minute=0, hour='*/4'), # Every 4 hours
    'emergency-check': crontab(minute=30, hour='*/6') # Every 6 hours
}
```

## Data Flow

### 1. Event Ingestion
```python
# When storing scraped events
data_handler = ScrapingDataHandler(retention_manager, db)
stored_count = await data_handler.store_scraped_events("timeout_dubai", events)
```

### 2. Automatic Retention Assignment
- Source priority determined automatically
- `delete_after` calculated as `end_date + retention_days`
- Lifecycle fields added to event document

### 3. Automated Cleanup
- Daily task checks `delete_after` dates
- Soft delete first (status = "deleted")
- Hard delete after 24-hour grace period

### 4. Monitoring and Alerts
- Health checks monitor cleanup efficiency
- Alerts generated for anomalies
- Weekly reports track trends

## Performance Metrics

### Expected Storage Efficiency
- **Total Events Stored**: ~769 events simultaneously
- **Storage Size**: ~3.8 MB total
- **Monthly Cost**: ~$0.001 (essentially free!)

### Success Criteria
- ✅ **Storage Cost**: Under $5/month
- ✅ **Cleanup Efficiency**: 99%+ expired events deleted within 24 hours
- ✅ **Query Performance**: Event searches under 200ms
- ✅ **Family Coverage**: 80%+ Dubai family events from high-priority sources

## Monitoring Dashboard

### Key Metrics to Watch
1. **Storage Health**: Should remain "healthy"
2. **Cleanup Efficiency**: Should be "good" (< 10 overdue events)
3. **Cost Estimate**: Should remain under $5/month
4. **Source Balance**: High priority events should be 40%+ of total

### Alert Conditions
- More than 5,000 total events (storage overload)
- More than 50 overdue events (cleanup failure)
- Less than 40% high-priority events (poor source balance)
- Storage costs exceeding $5/month

## Troubleshooting

### Common Issues

#### 1. Cleanup Not Running
```bash
# Check Celery worker status
celery -A lifecycle_management.celery_config:celery_app inspect active

# Check Redis connection
redis-cli ping

# Manually trigger cleanup
curl -X POST http://localhost:8000/lifecycle/tasks/trigger-cleanup
```

#### 2. Events Not Getting Retention Policies
```bash
# Setup retention for existing events
curl -X POST http://localhost:8000/lifecycle/setup-retention

# Check events without policies
curl http://localhost:8000/lifecycle/health
```

#### 3. High Storage Costs
```bash
# Check cost breakdown
curl http://localhost:8000/lifecycle/cost-estimate

# Check source distribution
curl http://localhost:8000/lifecycle/source-stats

# Manual cleanup if needed
curl -X POST http://localhost:8000/lifecycle/cleanup/manual
```

## Development

### Adding New Sources
1. Add source to appropriate priority level in `SourceBasedRetentionManager`
2. Update source classification logic if needed
3. Test retention behavior

### Modifying Retention Policies
1. Update `retention_policies` in `SourceBasedRetentionManager`
2. Run retention setup to apply to existing events
3. Monitor impact on storage costs

### Custom Monitoring
Extend `StorageHealthMonitor` to add custom metrics or alerts specific to your use case.

## Testing

### Test Lifecycle Management
```bash
# Test storage health
curl http://localhost:8000/lifecycle/health

# Test manual cleanup
curl -X POST http://localhost:8000/lifecycle/cleanup/manual

# Test event storage with lifecycle
curl -X POST http://localhost:8000/lifecycle/events/store \
  -H "Content-Type: application/json" \
  -d '{"source": "timeout_dubai", "events": [...]}'
```

### Load Testing
Use the provided endpoints to simulate high event volumes and verify cleanup efficiency under load.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   FastAPI App   │    │   MongoDB Atlas │
│                 │    │                 │    │                 │
│ • Dubai Calendar│────│ • Event Storage │────│ • Events Coll.  │
│ • Time Out Dubai│    │ • Lifecycle API │    │ • Weekly Stats  │
│ • Platinumlist  │    │ • Health Monitor│    │ • Indexes       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                         ┌─────────────────┐    ┌─────────────────┐
                         │   Celery Tasks  │    │      Redis      │
                         │                 │    │                 │
                         │ • Daily Cleanup │────│ • Task Queue    │
                         │ • Health Checks │    │ • Results Store │
                         │ • Weekly Reports│    │ • Beat Schedule │
                         └─────────────────┘    └─────────────────┘
```

This system ensures your DXB Events platform maintains optimal storage efficiency while providing comprehensive family event coverage across Dubai and the UAE. 