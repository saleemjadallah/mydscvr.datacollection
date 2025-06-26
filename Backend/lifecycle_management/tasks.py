"""
Lifecycle Management Tasks - Converted from Celery to Regular Functions

All tasks previously managed by Celery, now converted to regular async functions
that can be called via API endpoints or cron jobs.
"""

from datetime import datetime, timedelta, date
import asyncio
import logging
import random
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from bson import ObjectId

logger = logging.getLogger(__name__)

# Get MongoDB client for tasks
def get_mongodb_client():
    client = AsyncIOMotorClient(
        settings.mongodb_url,
        tls=True,
        tlsAllowInvalidCertificates=True  # For development/testing
    )
    return client[settings.mongodb_database]

async def create_daily_hidden_gem():
    """Create daily hidden gem with fallback logic"""
    try:
        mongodb = get_mongodb_client()
        
        # Check if today's gem already exists
        today = date.today()
        existing_gem = await mongodb.hidden_gems.find_one({
            "date": today.isoformat(),
            "is_active": True
        })
        
        if existing_gem:
            logger.info(f"Hidden gem already exists for {today}")
            return {"status": "exists", "gem_id": str(existing_gem["_id"])}
        
        # Get potential events for hidden gem
        # Priority: High engagement, recent events, variety
        tomorrow = datetime.now() + timedelta(days=1)
        week_ahead = datetime.now() + timedelta(days=7)
        
        pipeline = [
            {
                "$match": {
                    "start_date": {
                        "$gte": tomorrow,
                        "$lte": week_ahead
                    },
                    "is_active": True,
                    "family_score": {"$gte": 60}  # Family-friendly events
                }
            },
            {
                "$addFields": {
                    "gem_score": {
                        "$add": [
                            {"$multiply": ["$family_score", 0.4]},
                            {"$multiply": [{"$ifNull": ["$view_count", 0]}, 0.3]},
                            {"$multiply": [{"$ifNull": ["$engagement_rating", 0]}, 0.3]}
                        ]
                    }
                }
            },
            {"$sort": {"gem_score": -1}},
            {"$limit": 10}
        ]
        
        candidates = await mongodb.events.aggregate(pipeline).to_list(length=None)
        
        if not candidates:
            logger.warning("No suitable events found for hidden gem")
            return {"status": "no_candidates"}
        
        # Select gem with some randomness for variety
        top_candidates = candidates[:min(3, len(candidates))]
        selected_event = random.choice(top_candidates)
        
        # Create hidden gem entry
        gem_data = {
            "event_id": selected_event["_id"],
            "date": today.isoformat(),
            "title": selected_event.get("title", "Special Event"),
            "description": selected_event.get("description", ""),
            "gem_reason": "Curated for families - high engagement and family-friendly",
            "gem_score": selected_event.get("gem_score", 0),
            "is_active": True,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=1)
        }
        
        result = await mongodb.hidden_gems.insert_one(gem_data)
        
        logger.info(f"Created hidden gem: {selected_event.get('title')} with score {selected_event.get('gem_score', 0)}")
        return {"status": "created", "gem_id": str(result.inserted_id), "event_title": selected_event.get("title")}
        
    except Exception as e:
        logger.error(f"Error creating daily hidden gem: {str(e)}")
        return {"status": "error", "error": str(e)}

async def cleanup_expired_gems():
    """Clean up expired hidden gems"""
    try:
        mongodb = get_mongodb_client()
        
        # Remove gems older than 1 week
        cutoff_date = datetime.now() - timedelta(days=7)
        
        result = await mongodb.hidden_gems.delete_many({
            "created_at": {"$lt": cutoff_date}
        })
        
        logger.info(f"Cleaned up {result.deleted_count} expired hidden gems")
        return {"status": "success", "deleted_count": result.deleted_count}
        
    except Exception as e:
        logger.error(f"Error cleaning up expired gems: {str(e)}")
        return {"status": "error", "error": str(e)}

async def daily_storage_health_check():
    """Perform daily storage health check and generate metrics"""
    try:
        mongodb = get_mongodb_client()
        
        # Basic health metrics
        total_events = await mongodb.events.count_documents({})
        active_events = await mongodb.events.count_documents({"is_active": True})
        future_events = await mongodb.events.count_documents({
            "start_date": {"$gte": datetime.now()}
        })
        
        # Check for recent activity
        last_24h = datetime.now() - timedelta(days=1)
        recent_events = await mongodb.events.count_documents({
            "created_at": {"$gte": last_24h}
        })
        
        # Storage health summary
        health_data = {
            "date": date.today().isoformat(),
            "total_events": total_events,
            "active_events": active_events,
            "future_events": future_events,
            "events_added_24h": recent_events,
            "health_score": min(100, (active_events / max(total_events, 1)) * 100),
            "checked_at": datetime.now()
        }
        
        # Store health report
        await mongodb.storage_health.insert_one(health_data)
        
        logger.info(f"Storage health check completed: {total_events} total, {active_events} active, {future_events} future")
        return {"status": "success", "health_data": health_data}
        
    except Exception as e:
        logger.error(f"Error in storage health check: {str(e)}")
        return {"status": "error", "error": str(e)}

async def daily_source_based_cleanup():
    """Perform daily cleanup based on source retention policies"""
    try:
        from .retention.source_based_cleanup import SourceBasedRetentionManager
        
        retention_manager = SourceBasedRetentionManager()
        
        # Run retention cleanup
        cleanup_results = await retention_manager.cleanup_expired_events()
        
        logger.info(f"Daily cleanup completed: {cleanup_results}")
        return {"status": "success", "cleanup_results": cleanup_results}
        
    except Exception as e:
        logger.error(f"Error in daily cleanup: {str(e)}")
        return {"status": "error", "error": str(e)}

async def weekly_retention_report():
    """Generate weekly retention and performance report"""
    try:
        mongodb = get_mongodb_client()
        
        # Get data for last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        
        # Event source analysis
        source_pipeline = [
            {"$match": {"created_at": {"$gte": week_ago}}},
            {"$group": {
                "_id": "$source",
                "count": {"$sum": 1},
                "avg_family_score": {"$avg": "$family_score"}
            }},
            {"$sort": {"count": -1}}
        ]
        
        source_stats = await mongodb.events.aggregate(source_pipeline).to_list(length=None)
        
        # Overall statistics
        total_week = await mongodb.events.count_documents({
            "created_at": {"$gte": week_ago}
        })
        
        active_week = await mongodb.events.count_documents({
            "created_at": {"$gte": week_ago},
            "is_active": True
        })
        
        report_data = {
            "week_ending": date.today().isoformat(),
            "total_events_added": total_week,
            "active_events_added": active_week,
            "source_breakdown": source_stats,
            "activity_rate": (active_week / max(total_week, 1)) * 100,
            "generated_at": datetime.now()
        }
        
        # Store weekly report
        await mongodb.weekly_reports.insert_one(report_data)
        
        logger.info(f"Weekly report generated: {total_week} events added, {len(source_stats)} sources")
        return {"status": "success", "report_data": report_data}
        
    except Exception as e:
        logger.error(f"Error generating weekly report: {str(e)}")
        return {"status": "error", "error": str(e)}