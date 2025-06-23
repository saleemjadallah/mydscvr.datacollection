from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, List, Optional
from datetime import datetime
from database import get_mongodb
from lifecycle_management import (
    SourceBasedRetentionManager, 
    ScrapingDataHandler, 
    StorageHealthMonitor,
    celery_app
)
from models.mongodb_models import EventModel
from pydantic import BaseModel

router = APIRouter(prefix="/lifecycle", tags=["Lifecycle Management"])

class SourceRetentionUpdate(BaseModel):
    source: str
    new_priority: Optional[str] = None

class BulkCleanupRequest(BaseModel):
    source: str
    force: bool = False

# Dependency to get lifecycle managers
async def get_retention_manager(db = Depends(get_mongodb)):
    return SourceBasedRetentionManager(db)

async def get_data_handler(db = Depends(get_mongodb)):
    retention_manager = SourceBasedRetentionManager(db)
    return ScrapingDataHandler(retention_manager, db)

async def get_health_monitor(db = Depends(get_mongodb)):
    return StorageHealthMonitor(db)

@router.get("/health", summary="Get storage health status")
async def get_storage_health(health_monitor: StorageHealthMonitor = Depends(get_health_monitor)):
    """Get current storage health status and alerts"""
    try:
        health_status = await health_monitor.check_storage_health()
        return health_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check storage health: {str(e)}")

@router.get("/stats", summary="Get retention statistics")
async def get_retention_stats(retention_manager: SourceBasedRetentionManager = Depends(get_retention_manager)):
    """Get current retention statistics by source"""
    try:
        stats = await retention_manager.get_retention_stats()
        return {
            "status": "success",
            "retention_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get retention stats: {str(e)}")

@router.get("/cost-estimate", summary="Get storage cost estimate")
async def get_cost_estimate(health_monitor: StorageHealthMonitor = Depends(get_health_monitor)):
    """Get estimated storage costs"""
    try:
        cost_estimate = await health_monitor.calculate_storage_cost_estimate()
        return {
            "status": "success",
            "cost_estimate": cost_estimate,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate cost estimate: {str(e)}")

@router.get("/source-stats", summary="Get detailed source statistics")
async def get_source_stats(health_monitor: StorageHealthMonitor = Depends(get_health_monitor)):
    """Get detailed statistics by source"""
    try:
        source_stats = await health_monitor.get_detailed_source_stats()
        return {
            "status": "success",
            "source_stats": source_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get source stats: {str(e)}")

@router.get("/cleanup-efficiency", summary="Get cleanup efficiency stats")
async def get_cleanup_efficiency(health_monitor: StorageHealthMonitor = Depends(get_health_monitor)):
    """Get statistics on cleanup efficiency"""
    try:
        efficiency_stats = await health_monitor.get_cleanup_efficiency_stats()
        return {
            "status": "success",
            "cleanup_efficiency": efficiency_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cleanup efficiency: {str(e)}")

@router.get("/weekly-report", summary="Get weekly storage report")
async def get_weekly_report(health_monitor: StorageHealthMonitor = Depends(get_health_monitor)):
    """Generate comprehensive weekly storage report"""
    try:
        weekly_report = await health_monitor.generate_weekly_report()
        return {
            "status": "success",
            "report": weekly_report,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate weekly report: {str(e)}")

@router.post("/setup-retention", summary="Setup retention policies")
async def setup_retention_policies(
    background_tasks: BackgroundTasks,
    retention_manager: SourceBasedRetentionManager = Depends(get_retention_manager)
):
    """Setup automatic deletion policies for events without retention settings"""
    try:
        # Run setup in background
        background_tasks.add_task(retention_manager.setup_automatic_deletion)
        
        return {
            "status": "success",
            "message": "Retention policy setup started in background",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to setup retention policies: {str(e)}")

@router.post("/cleanup/manual", summary="Manual cleanup")
async def manual_cleanup(
    retention_manager: SourceBasedRetentionManager = Depends(get_retention_manager)
):
    """Run manual cleanup immediately"""
    try:
        cleanup_results = await retention_manager.daily_cleanup()
        
        return {
            "status": "success",
            "cleanup_results": cleanup_results,
            "message": "Manual cleanup completed",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manual cleanup failed: {str(e)}")

@router.post("/cleanup/source", summary="Cleanup specific source")
async def cleanup_source(
    request: BulkCleanupRequest,
    data_handler: ScrapingDataHandler = Depends(get_data_handler)
):
    """Clean up events from a specific source"""
    try:
        # Trigger manual cleanup for specific source via Celery
        task = celery_app.send_task(
            'lifecycle_management.schedulers.cleanup_tasks.manual_cleanup_source',
            args=[request.source]
        )
        
        return {
            "status": "success",
            "message": f"Cleanup for source '{request.source}' started",
            "task_id": task.id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start source cleanup: {str(e)}")

@router.post("/events/store", summary="Store events with lifecycle management")
async def store_events_with_lifecycle(
    source: str,
    events: List[Dict],
    data_handler: ScrapingDataHandler = Depends(get_data_handler)
):
    """Store scraped events with automatic retention policies"""
    try:
        stored_count = await data_handler.store_scraped_events(source, events)
        
        return {
            "status": "success",
            "stored_count": stored_count,
            "source": source,
            "message": f"Stored {stored_count} events with lifecycle management",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store events: {str(e)}")

@router.put("/events/{event_id}/retention", summary="Update event retention")
async def update_event_retention(
    event_id: str,
    update_request: SourceRetentionUpdate,
    data_handler: ScrapingDataHandler = Depends(get_data_handler)
):
    """Update retention policy for a specific event"""
    try:
        success = await data_handler.update_event_retention(event_id, update_request.source)
        
        if success:
            return {
                "status": "success",
                "message": f"Updated retention policy for event {event_id}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Event not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update event retention: {str(e)}")

@router.post("/tasks/trigger-cleanup", summary="Trigger cleanup task")
async def trigger_cleanup_task():
    """Trigger the daily cleanup Celery task immediately"""
    try:
        task = celery_app.send_task('lifecycle_management.schedulers.cleanup_tasks.daily_source_based_cleanup')
        
        return {
            "status": "success",
            "message": "Daily cleanup task triggered",
            "task_id": task.id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger cleanup task: {str(e)}")

@router.post("/tasks/trigger-health-check", summary="Trigger health check task")
async def trigger_health_check_task():
    """Trigger the storage health check Celery task immediately"""
    try:
        task = celery_app.send_task('lifecycle_management.schedulers.monitoring_tasks.daily_storage_health_check')
        
        return {
            "status": "success",
            "message": "Health check task triggered",
            "task_id": task.id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger health check task: {str(e)}")

@router.get("/tasks/{task_id}/status", summary="Get task status")
async def get_task_status(task_id: str):
    """Get status of a Celery task"""
    try:
        task_result = celery_app.AsyncResult(task_id)
        
        return {
            "status": "success",
            "task_id": task_id,
            "task_status": task_result.status,
            "task_result": task_result.result if task_result.ready() else None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@router.get("/policies", summary="Get retention policies")
async def get_retention_policies(retention_manager: SourceBasedRetentionManager = Depends(get_retention_manager)):
    """Get current retention policies configuration"""
    return {
        "status": "success",
        "retention_policies": retention_manager.retention_policies,
        "timestamp": datetime.now().isoformat()
    }

@router.get("/system-info", summary="Get lifecycle management system info")
async def get_system_info():
    """Get system information about the lifecycle management setup"""
    return {
        "status": "success",
        "system_info": {
            "version": "1.0.0",
            "celery_broker": "Redis",
            "storage_backend": "MongoDB Atlas",
            "timezone": "Asia/Dubai",
            "retention_levels": {
                "high": "7 days",
                "medium": "3 days", 
                "low": "1 day"
            },
            "automated_tasks": [
                "Daily cleanup (3 AM UAE)",
                "Weekly reports (Monday 4 AM UAE)", 
                "Health checks (2 AM UAE)",
                "Retention setup (every 4 hours)",
                "Emergency checks (every 6 hours)"
            ]
        },
        "timestamp": datetime.now().isoformat()
    } 