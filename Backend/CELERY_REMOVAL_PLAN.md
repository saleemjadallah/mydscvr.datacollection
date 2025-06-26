# Celery Removal Plan - mydscvr.backend

## Overview
Complete removal of Celery infrastructure and replacement with simple cron jobs and API endpoints to eliminate scheduling conflicts with the datacollection pipeline.

## 🗑️ Files to Remove Completely

### 1. Celery Configuration
- `lifecycle_management/celery_config.py` - Main Celery configuration
- `celerybeat-schedule.db` - Celery beat scheduler database  
- `start_celery_workers.sh` - Celery worker startup script
- `setup_lifecycle.sh` - Celery setup script

### 2. Celery Dependencies (requirements.txt)
Remove these packages:
```
celery==5.3.4
kombu==5.3.4
```
Keep Redis if used for other caching purposes.

## 🔧 Files to Modify

### 1. Task Files - Convert from Celery to Regular Functions

#### `lifecycle_management/schedulers/hidden_gems_tasks.py`
- **REMOVE**: `@current_app.task` decorators and Celery imports
- **KEEP**: Business logic for hidden gem creation
- **CONVERT TO**: Regular async functions

#### `lifecycle_management/schedulers/cleanup_tasks.py`  
- **REMOVE**: `@current_app.task` decorators
- **KEEP**: Data retention and cleanup logic
- **CONVERT TO**: Regular async functions

#### `lifecycle_management/schedulers/monitoring_tasks.py`
- **REMOVE**: `@current_app.task` decorators
- **KEEP**: Health check and monitoring logic
- **CONVERT TO**: Regular async functions

### 2. Initialization Files
#### `lifecycle_management/__init__.py`
- **REMOVE**: `celery_app` export
- **KEEP**: Other lifecycle management exports

### 3. Router Files  
#### `routers/lifecycle_management.py`
- **REMOVE**: Celery app imports and task queuing
- **ADD**: New API endpoints for manual task triggering

## 🔄 Replacement Strategy

### Step 1: Create New API Endpoints
Add these endpoints to handle essential tasks:

```python
# New endpoints in routers/lifecycle_management.py
@router.post("/tasks/daily-cleanup")
@router.post("/tasks/health-check") 
@router.post("/tasks/create-hidden-gem")
@router.post("/tasks/weekly-report")
```

### Step 2: Setup Replacement Cron Jobs
Use system cron instead of Celery beat, **avoiding datacollection pipeline times**:

```bash
# SAFE TIMING - No conflicts with datacollection (12AM-3AM UTC)

# Daily cleanup at 6 AM UAE (2 AM UTC) - MOVED from 3 AM UAE to avoid conflict
0 2 * * * curl -X POST http://localhost:8000/lifecycle/tasks/daily-cleanup

# Daily health check at 8 AM UAE (4 AM UTC) - MOVED from 2 AM UAE  
0 4 * * * curl -X POST http://localhost:8000/lifecycle/tasks/health-check

# Daily hidden gem at 9 AM UAE (5 AM UTC) - MOVED from 1 AM UAE
0 5 * * * curl -X POST http://localhost:8000/lifecycle/tasks/create-hidden-gem

# Weekly report on Monday 10 AM UAE (Monday 6 AM UTC) - MOVED from 4 AM UAE
0 6 * * 1 curl -X POST http://localhost:8000/lifecycle/tasks/weekly-report
```

## 📋 Essential Business Logic to Preserve

### 1. Hidden Gems Creation
- **Function**: `create_daily_hidden_gem()`
- **Purpose**: Creates daily featured events
- **Database**: `hidden_gems` collection
- **Logic**: Event selection, fallback mechanisms, uniqueness checks

### 2. Data Cleanup  
- **Function**: `daily_source_based_cleanup()`
- **Purpose**: Enforces retention policies, removes expired events
- **Database**: `events` collection
- **Logic**: Source-based retention, expiration date cleanup

### 3. Storage Health Monitoring
- **Function**: `daily_storage_health_check()`  
- **Purpose**: Database health metrics, cost calculations
- **Database**: Multiple collections
- **Logic**: Storage statistics, performance monitoring

### 4. Weekly Reporting
- **Function**: `weekly_retention_report()`
- **Purpose**: Analytics and performance reports  
- **Database**: Multiple collections
- **Logic**: Retention statistics, source performance analysis

## ⚠️ Critical Timing Changes

### OLD Celery Schedule (UAE Time = UTC+4):
- **1:00 AM UAE** (9:00 PM UTC): Hidden gems - **CONFLICT with datacollection**
- **2:00 AM UAE** (10:00 PM UTC): Health check - **CONFLICT with datacollection**  
- **3:00 AM UAE** (11:00 PM UTC): Daily cleanup - **CONFLICT with datacollection**

### NEW Cron Schedule (No Conflicts):
- **5:00 AM UAE** (1:00 AM UTC): Hidden gems - **SAFE**
- **8:00 AM UAE** (4:00 AM UTC): Health check - **SAFE**
- **6:00 AM UAE** (2:00 AM UTC): Daily cleanup - **SAFE**

## 🚀 Implementation Steps

### Phase 1: Prepare Replacement (No Downtime)
1. Create new API endpoints for each task
2. Convert Celery tasks to regular async functions
3. Test new endpoints manually

### Phase 2: Setup Cron Jobs
1. Install new cron jobs with safe timing
2. Test cron job execution
3. Monitor for 24 hours alongside Celery

### Phase 3: Remove Celery (Safe Removal)
1. Stop Celery workers and beat
2. Remove Celery configuration files
3. Remove Celery dependencies from requirements.txt
4. Clean up imports and decorators

## 🎯 Benefits After Removal

### ✅ **Eliminated Conflicts:**
- No more database operation conflicts at 1-3 AM UTC
- No Redis broker dependency for task scheduling  
- No Celery worker memory overhead
- No complex task queue management

### ✅ **Simplified Architecture:**
- Direct API calls instead of task queuing
- Standard cron jobs instead of Celery beat
- Easier debugging and monitoring
- Reduced infrastructure complexity

### ✅ **Better Reliability:**
- No Celery worker failures or restarts
- No Redis connectivity issues
- No task queue backlogs
- Direct execution feedback

## 📊 Impact Assessment

### **Zero Business Logic Loss:**
All essential functionality preserved through API endpoints

### **Improved Performance:**
- Eliminated 2:00 AM UTC database conflicts
- Reduced memory usage (no Celery workers)
- Better resource allocation during datacollection window

### **Simplified Operations:**
- System cron jobs instead of Celery management
- Direct HTTP calls for manual triggering
- Standard logging instead of Celery task logs

This removal will completely eliminate the scheduling conflicts with your datacollection pipeline while preserving all essential business functionality!