from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class StorageHealthMonitor:
    def __init__(self, db_client):
        self.db = db_client
    
    async def check_storage_health(self):
        """Monitor storage efficiency and alert on issues"""
        stats = await self.get_storage_stats()
        alerts = []
        
        # Check for excessive storage
        if stats['total_events'] > 5000:
            alerts.append("High event count - consider more aggressive cleanup")
        
        # Check for imbalanced priorities
        if stats['total_events'] > 0:
            high_priority_ratio = stats['high_priority_events'] / stats['total_events']
            if high_priority_ratio < 0.4:
                alerts.append("Too many low-priority events - review source strategy")
        
        # Check for old events not being cleaned up
        old_events = await self.db.events.count_documents({
            "delete_after": {"$lt": datetime.now() - timedelta(days=1)},
            "status": "active"
        })
        if old_events > 50:
            alerts.append(f"{old_events} events overdue for deletion - check cleanup task")
        
        # Check for events without retention policies
        events_without_retention = await self.db.events.count_documents({
            "status": "active",
            "$or": [
                {"source_priority": {"$exists": False}},
                {"retention_days": {"$exists": False}},
                {"delete_after": {"$exists": False}}
            ]
        })
        if events_without_retention > 0:
            alerts.append(f"{events_without_retention} events missing retention policies")
        
        return {
            "status": "healthy" if not alerts else "needs_attention",
            "stats": stats,
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_storage_stats(self):
        """Get current storage statistics"""
        pipeline = [
            {
                "$match": {"status": {"$ne": "deleted"}}
            },
            {
                "$group": {
                    "_id": "$source_priority",
                    "count": {"$sum": 1},
                    "sources": {"$addToSet": "$source"}
                }
            }
        ]
        
        results = await self.db.events.aggregate(pipeline).to_list(None)
        
        stats = {
            "total_events": 0,
            "high_priority_events": 0,
            "medium_priority_events": 0,
            "low_priority_events": 0,
            "unknown_priority_events": 0
        }
        
        for result in results:
            priority = result["_id"]
            count = result["count"]
            stats["total_events"] += count
            
            if priority == "high":
                stats["high_priority_events"] = count
            elif priority == "medium":
                stats["medium_priority_events"] = count
            elif priority == "low":
                stats["low_priority_events"] = count
            else:
                stats["unknown_priority_events"] = count
        
        return stats
    
    async def get_detailed_source_stats(self) -> Dict:
        """Get detailed statistics by source"""
        pipeline = [
            {
                "$match": {"status": {"$ne": "deleted"}}
            },
            {
                "$group": {
                    "_id": {
                        "source": "$source",
                        "priority": "$source_priority"
                    },
                    "active_count": {"$sum": 1},
                    "avg_retention_days": {"$avg": "$retention_days"},
                    "oldest_event": {"$min": "$created_at"},
                    "newest_event": {"$max": "$created_at"}
                }
            }
        ]
        
        results = await self.db.events.aggregate(pipeline).to_list(None)
        
        source_stats = {}
        for result in results:
            source = result["_id"]["source"]
            priority = result["_id"]["priority"]
            
            source_stats[source] = {
                "priority": priority,
                "active_events": result["active_count"],
                "avg_retention_days": result["avg_retention_days"],
                "oldest_event": result["oldest_event"],
                "newest_event": result["newest_event"]
            }
        
        return source_stats
    
    async def get_cleanup_efficiency_stats(self) -> Dict:
        """Get statistics on cleanup efficiency"""
        now = datetime.now()
        
        # Events that should have been deleted but weren't
        overdue_events = await self.db.events.count_documents({
            "delete_after": {"$lt": now},
            "status": "active"
        })
        
        # Recently deleted events
        recently_deleted = await self.db.events.count_documents({
            "status": "deleted",
            "deleted_at": {"$gte": now - timedelta(days=7)}
        })
        
        # Events pending hard deletion
        pending_hard_delete = await self.db.events.count_documents({
            "status": "deleted",
            "deleted_at": {"$lt": now - timedelta(hours=24)}
        })
        
        return {
            "overdue_events": overdue_events,
            "recently_deleted": recently_deleted,
            "pending_hard_delete": pending_hard_delete,
            "cleanup_efficiency": "good" if overdue_events < 10 else "needs_attention"
        }
    
    async def calculate_storage_cost_estimate(self) -> Dict:
        """Calculate estimated storage costs"""
        stats = await self.get_storage_stats()
        
        # Estimated document size in KB
        avg_document_size_kb = 5
        
        # Convert to GB
        total_storage_gb = (stats['total_events'] * avg_document_size_kb) / (1024 * 1024)
        
        # MongoDB Atlas pricing estimate (varies by region)
        monthly_cost_per_gb = 0.25
        estimated_monthly_cost = total_storage_gb * monthly_cost_per_gb
        
        return {
            "total_events": stats['total_events'],
            "estimated_storage_gb": round(total_storage_gb, 4),
            "estimated_monthly_cost_usd": round(estimated_monthly_cost, 4),
            "cost_per_event_usd": round(estimated_monthly_cost / stats['total_events'], 6) if stats['total_events'] > 0 else 0
        }
    
    async def generate_weekly_report(self) -> Dict:
        """Generate comprehensive weekly storage report"""
        health_check = await self.check_storage_health()
        source_stats = await self.get_detailed_source_stats()
        cleanup_stats = await self.get_cleanup_efficiency_stats()
        cost_estimate = await self.calculate_storage_cost_estimate()
        
        # Performance recommendations
        recommendations = []
        
        if health_check['stats']['total_events'] > 3000:
            recommendations.append("Consider more aggressive cleanup for low-priority sources")
        
        if cleanup_stats['overdue_events'] > 20:
            recommendations.append("Cleanup tasks may need optimization - check Celery workers")
        
        if cost_estimate['estimated_monthly_cost_usd'] > 5:
            recommendations.append("Storage costs exceeding target - review retention policies")
        
        high_priority_sources = [s for s, data in source_stats.items() if data.get('priority') == 'high']
        if len(high_priority_sources) < 4:
            recommendations.append("Consider promoting more sources to high priority for better coverage")
        
        return {
            "report_date": datetime.now().isoformat(),
            "health_status": health_check['status'],
            "storage_stats": health_check['stats'],
            "cleanup_efficiency": cleanup_stats,
            "cost_estimate": cost_estimate,
            "source_breakdown": source_stats,
            "alerts": health_check['alerts'],
            "recommendations": recommendations,
            "summary": {
                "total_active_events": health_check['stats']['total_events'],
                "storage_health": health_check['status'],
                "cleanup_efficiency": cleanup_stats['cleanup_efficiency'],
                "estimated_monthly_cost": f"${cost_estimate['estimated_monthly_cost_usd']:.2f}"
            }
        } 