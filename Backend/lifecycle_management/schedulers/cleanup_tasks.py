from celery import current_app
from datetime import datetime, timedelta
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from ..retention.source_based_cleanup import SourceBasedRetentionManager
from ..retention.data_handler import ScrapingDataHandler

logger = logging.getLogger(__name__)

# Get MongoDB client for tasks
def get_mongodb_client():
    client = AsyncIOMotorClient(
        settings.mongodb_url,
        tls=True,
        tlsAllowInvalidCertificates=True  # For development/testing
    )
    return client[settings.mongodb_database]

@current_app.task(bind=True, name='lifecycle_management.schedulers.cleanup_tasks.daily_source_based_cleanup')
def daily_source_based_cleanup(self):
    """Daily cleanup based on source priority and retention policies"""
    async def run_cleanup():
        try:
            mongodb = get_mongodb_client()
            retention_manager = SourceBasedRetentionManager(mongodb)
            
            # Set up automatic deletion for new events
            await retention_manager.setup_automatic_deletion()
            
            # Run daily cleanup
            cleanup_results = await retention_manager.daily_cleanup()
            
            # Get retention statistics
            stats = await retention_manager.get_retention_stats()
            
            result = {
                "status": "completed",
                "cleanup_results": cleanup_results,
                "retention_stats": stats,
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
            
            logger.info(f"Daily cleanup completed: {cleanup_results}")
            logger.info(f"Current retention stats: {stats}")
            
            return result
            
        except Exception as e:
            logger.error(f"Daily cleanup failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_cleanup())

@current_app.task(bind=True, name='lifecycle_management.schedulers.cleanup_tasks.setup_retention_policies')
def setup_retention_policies(self):
    """Setup retention policies for events that don't have them"""
    async def run_setup():
        try:
            mongodb = get_mongodb_client()
            retention_manager = SourceBasedRetentionManager(mongodb)
            
            # Find events without retention policies
            events_without_policies = await mongodb.events.find({
                "$or": [
                    {"source_priority": {"$exists": False}},
                    {"retention_days": {"$exists": False}},
                    {"delete_after": {"$exists": False}}
                ],
                "status": {"$ne": "deleted"}
            }).to_list(None)
            
            updated_count = 0
            for event in events_without_policies:
                source = event.get('source') or event.get('source_name', 'unknown')
                priority = retention_manager.get_source_priority(source)
                retention_days = retention_manager.retention_policies[priority]['retention_days']
                
                # Calculate delete_after if event has end_date
                delete_after = None
                if event.get('end_date'):
                    delete_after = event['end_date'] + timedelta(days=retention_days)
                
                # Update the event
                await mongodb.events.update_one(
                    {"_id": event["_id"]},
                    {
                        "$set": {
                            "source": source,
                            "source_priority": priority,
                            "retention_days": retention_days,
                            "delete_after": delete_after,
                            "last_updated": datetime.now()
                        }
                    }
                )
                updated_count += 1
            
            result = {
                "status": "completed",
                "events_updated": updated_count,
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
            
            logger.info(f"Setup retention policies for {updated_count} events")
            return result
            
        except Exception as e:
            logger.error(f"Setup retention policies failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_setup())

@current_app.task(bind=True, name='lifecycle_management.schedulers.cleanup_tasks.emergency_cleanup_check')
def emergency_cleanup_check(self):
    """Emergency cleanup check for storage issues"""
    async def run_emergency_check():
        try:
            mongodb = get_mongodb_client()
            retention_manager = SourceBasedRetentionManager(mongodb)
            
            # Check for critical storage issues
            now = datetime.now()
            
            # Find severely overdue events (more than 7 days past deletion date)
            severely_overdue = await mongodb.events.count_documents({
                "delete_after": {"$lt": now - timedelta(days=7)},
                "status": "active"
            })
            
            # Find events stuck in deleted status for too long
            stuck_deleted = await mongodb.events.count_documents({
                "status": "deleted",
                "deleted_at": {"$lt": now - timedelta(days=3)}
            })
            
            emergency_actions = []
            
            # Force cleanup severely overdue events
            if severely_overdue > 0:
                result = await mongodb.events.update_many(
                    {
                        "delete_after": {"$lt": now - timedelta(days=7)},
                        "status": "active"
                    },
                    {
                        "$set": {
                            "status": "deleted",
                            "deleted_at": now
                        }
                    }
                )
                emergency_actions.append(f"Force deleted {result.modified_count} severely overdue events")
            
            # Hard delete stuck events
            if stuck_deleted > 0:
                result = await mongodb.events.delete_many({
                    "status": "deleted",
                    "deleted_at": {"$lt": now - timedelta(days=3)}
                })
                emergency_actions.append(f"Hard deleted {result.deleted_count} stuck events")
            
            # Check total event count
            total_events = await mongodb.events.count_documents({"status": {"$ne": "deleted"}})
            
            result = {
                "status": "completed",
                "severely_overdue_found": severely_overdue,
                "stuck_deleted_found": stuck_deleted,
                "emergency_actions": emergency_actions,
                "total_active_events": total_events,
                "needs_attention": severely_overdue > 50 or stuck_deleted > 100 or total_events > 10000,
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
            
            if emergency_actions:
                logger.warning(f"Emergency cleanup performed: {emergency_actions}")
            
            return result
            
        except Exception as e:
            logger.error(f"Emergency cleanup check failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_emergency_check())

@current_app.task(bind=True, name='lifecycle_management.schedulers.cleanup_tasks.manual_cleanup_source')
def manual_cleanup_source(self, source_name: str):
    """Manual cleanup for a specific source"""
    async def run_manual_cleanup():
        try:
            mongodb = get_mongodb_client()
            retention_manager = SourceBasedRetentionManager(mongodb)
            
            # Get source priority
            priority = retention_manager.get_source_priority(source_name)
            
            # Force cleanup for this source
            now = datetime.now()
            result = await mongodb.events.update_many(
                {
                    "source": source_name,
                    "status": "active",
                    "$or": [
                        {"delete_after": {"$lt": now}},
                        {"delete_after": {"$exists": False}}
                    ]
                },
                {
                    "$set": {
                        "status": "deleted",
                        "deleted_at": now
                    }
                }
            )
            
            return {
                "status": "completed",
                "source": source_name,
                "priority": priority,
                "events_cleaned": result.modified_count,
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
            
        except Exception as e:
            logger.error(f"Manual cleanup for {source_name} failed: {e}")
            return {
                "status": "failed",
                "source": source_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_manual_cleanup()) 