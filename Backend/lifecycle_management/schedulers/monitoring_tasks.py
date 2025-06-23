from celery import current_app
from datetime import datetime, timedelta
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from ..monitoring.storage_health import StorageHealthMonitor
from ..retention.source_based_cleanup import SourceBasedRetentionManager

logger = logging.getLogger(__name__)

# Get MongoDB client for tasks
def get_mongodb_client():
    client = AsyncIOMotorClient(
        settings.mongodb_url,
        tls=True,
        tlsAllowInvalidCertificates=True  # For development/testing
    )
    return client[settings.mongodb_database]

@current_app.task(bind=True, name='lifecycle_management.schedulers.monitoring_tasks.daily_storage_health_check')
def daily_storage_health_check(self):
    """Daily storage health check and alert generation"""
    async def run_health_check():
        try:
            mongodb = get_mongodb_client()
            health_monitor = StorageHealthMonitor(mongodb)
            
            # Run comprehensive health check
            health_report = await health_monitor.check_storage_health()
            
            # Get cleanup efficiency stats
            cleanup_stats = await health_monitor.get_cleanup_efficiency_stats()
            
            # Calculate storage costs
            cost_estimate = await health_monitor.calculate_storage_cost_estimate()
            
            result = {
                "status": "completed",
                "health_status": health_report['status'],
                "alerts": health_report['alerts'],
                "storage_stats": health_report['stats'],
                "cleanup_efficiency": cleanup_stats,
                "cost_estimate": cost_estimate,
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
            
            # Log critical alerts
            if health_report['alerts']:
                logger.warning(f"Storage health alerts: {health_report['alerts']}")
            
            # Log if cleanup efficiency is poor
            if cleanup_stats['cleanup_efficiency'] == 'needs_attention':
                logger.warning(f"Cleanup efficiency needs attention: {cleanup_stats}")
            
            # Log if costs are high
            if cost_estimate['estimated_monthly_cost_usd'] > 5:
                logger.warning(f"Storage costs high: ${cost_estimate['estimated_monthly_cost_usd']:.2f}/month")
            
            logger.info(f"Daily health check completed - Status: {health_report['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Daily storage health check failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_health_check())

@current_app.task(bind=True, name='lifecycle_management.schedulers.monitoring_tasks.weekly_retention_report')
def weekly_retention_report(self):
    """Weekly comprehensive retention and storage report"""
    async def generate_report():
        try:
            mongodb = get_mongodb_client()
            health_monitor = StorageHealthMonitor(mongodb)
            retention_manager = SourceBasedRetentionManager(mongodb)
            
            # Generate comprehensive weekly report
            weekly_report = await health_monitor.generate_weekly_report()
            
            # Get additional statistics
            retention_stats = await retention_manager.get_retention_stats()
            
            # Calculate week-over-week changes (if previous report exists)
            previous_week_stats = await get_previous_week_stats(mongodb)
            
            trends = {}
            if previous_week_stats:
                current_total = weekly_report['storage_stats']['total_events']
                previous_total = previous_week_stats.get('total_events', 0)
                trends = {
                    "total_events_change": current_total - previous_total,
                    "total_events_change_percent": ((current_total - previous_total) / previous_total * 100) if previous_total > 0 else 0
                }
            
            # Store this week's stats for next week's comparison
            await store_weekly_stats(mongodb, weekly_report['storage_stats'])
            
            result = {
                "status": "completed",
                "report": weekly_report,
                "retention_stats": retention_stats,
                "trends": trends,
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
            
            # Log important metrics
            logger.info(f"Weekly report generated - Total events: {weekly_report['storage_stats']['total_events']}")
            logger.info(f"Storage health: {weekly_report['health_status']}")
            logger.info(f"Monthly cost estimate: {weekly_report['summary']['estimated_monthly_cost']}")
            
            # Log recommendations
            if weekly_report['recommendations']:
                logger.info(f"Recommendations: {weekly_report['recommendations']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Weekly retention report failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(generate_report())

@current_app.task(bind=True, name='lifecycle_management.schedulers.monitoring_tasks.source_performance_analysis')
def source_performance_analysis(self):
    """Analyze performance of different event sources"""
    async def run_analysis():
        try:
            mongodb = get_mongodb_client()
            health_monitor = StorageHealthMonitor(mongodb)
            
            # Get detailed source statistics
            source_stats = await health_monitor.get_detailed_source_stats()
            
            # Analyze source performance
            analysis = {}
            for source, stats in source_stats.items():
                # Calculate events per day
                if stats['oldest_event'] and stats['newest_event']:
                    days_active = (stats['newest_event'] - stats['oldest_event']).days or 1
                    events_per_day = stats['active_events'] / days_active
                else:
                    events_per_day = 0
                
                # Performance metrics
                analysis[source] = {
                    "priority": stats['priority'],
                    "active_events": stats['active_events'],
                    "events_per_day": round(events_per_day, 2),
                    "retention_days": stats.get('avg_retention_days', 0),
                    "performance_score": calculate_source_performance_score(stats, events_per_day)
                }
            
            # Identify top and bottom performers
            sorted_sources = sorted(analysis.items(), key=lambda x: x[1]['performance_score'], reverse=True)
            
            result = {
                "status": "completed",
                "source_analysis": analysis,
                "top_performers": sorted_sources[:3],
                "bottom_performers": sorted_sources[-3:],
                "total_sources_analyzed": len(analysis),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
            
            logger.info(f"Source performance analysis completed for {len(analysis)} sources")
            return result
            
        except Exception as e:
            logger.error(f"Source performance analysis failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_analysis())

async def get_previous_week_stats(mongodb):
    """Get previous week's statistics for trend analysis"""
    try:
        one_week_ago = datetime.now() - timedelta(days=7)
        previous_stats = await mongodb.weekly_stats.find_one(
            {"week_start": {"$gte": one_week_ago}},
            sort=[("week_start", -1)]
        )
        return previous_stats.get('stats', {}) if previous_stats else None
    except Exception:
        return None

async def store_weekly_stats(mongodb, stats):
    """Store weekly statistics for trend analysis"""
    try:
        # Calculate week start (Monday)
        now = datetime.now()
        days_since_monday = now.weekday()
        week_start = now - timedelta(days=days_since_monday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        await mongodb.weekly_stats.update_one(
            {"week_start": week_start},
            {
                "$set": {
                    "stats": stats,
                    "recorded_at": now
                }
            },
            upsert=True
        )
    except Exception as e:
        logger.error(f"Failed to store weekly stats: {e}")

def calculate_source_performance_score(stats, events_per_day):
    """Calculate performance score for a source"""
    score = 0
    
    # Points for activity level
    if events_per_day > 10:
        score += 40
    elif events_per_day > 5:
        score += 30
    elif events_per_day > 1:
        score += 20
    else:
        score += 10
    
    # Points for priority
    priority = stats.get('priority', 'low')
    if priority == 'high':
        score += 30
    elif priority == 'medium':
        score += 20
    else:
        score += 10
    
    # Points for consistency (active events)
    active_events = stats.get('active_events', 0)
    if active_events > 100:
        score += 30
    elif active_events > 50:
        score += 20
    elif active_events > 10:
        score += 10
    
    return min(score, 100)  # Cap at 100 