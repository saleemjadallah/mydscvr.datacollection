from datetime import datetime, timedelta
import asyncio
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class SourceBasedRetentionManager:
    def __init__(self, db_client):
        self.db = db_client
        self.retention_policies = {
            # High Priority - 7 days after event end
            'high': {
                'sources': ['dubai_calendar', 'timeout_dubai', 'timeout_kids_uae', 'platinumlist'],
                'retention_days': 7,
                'reason': 'High-value family events, keep for analytics'
            },
            # Medium Priority - 3 days after event end
            'medium': {
                'sources': ['eventbrite_dubai', 'meetup_dubai', 'whats_on_dubai', 
                           'timeout_market_dubai', 'timeout_dxb', 'dubai_web_events'],
                'retention_days': 3,
                'reason': 'Good coverage, moderate retention'
            },
            # Low Priority - 1 day after event end
            'low': {
                'sources': ['7g_media', 'social_rising', 'instagram_influencers'],
                'retention_days': 1,
                'reason': 'Limited family appeal, minimal retention'
            }
        }
    
    async def setup_automatic_deletion(self):
        """Set delete_after field for all events based on source priority"""
        for priority, policy in self.retention_policies.items():
            for source in policy['sources']:
                await self.db.events.update_many(
                    {
                        "source": source,
                        "delete_after": {"$exists": False}  # Only update if not set
                    },
                    {
                        "$set": {
                            "source_priority": priority,
                            "retention_days": policy['retention_days']
                        }
                    }
                )
                
                # Calculate delete_after for events with end_date
                await self.db.events.update_many(
                    {
                        "source": source,
                        "end_date": {"$exists": True},
                        "delete_after": {"$exists": False}
                    },
                    [
                        {
                            "$set": {
                                "delete_after": {
                                    "$dateAdd": {
                                        "startDate": "$end_date",
                                        "unit": "day",
                                        "amount": policy['retention_days']
                                    }
                                }
                            }
                        }
                    ]
                )
    
    async def daily_cleanup(self) -> Dict[str, int]:
        """Clean up expired events based on delete_after field"""
        now = datetime.now()
        cleanup_results = {}
        
        for priority, policy in self.retention_policies.items():
            # Find events ready for deletion
            expired_events = await self.db.events.find({
                "source_priority": priority,
                "delete_after": {"$lt": now},
                "status": {"$ne": "deleted"}
            }).to_list(None)
            
            if expired_events:
                # Mark as deleted first (soft delete)
                result = await self.db.events.update_many(
                    {
                        "source_priority": priority,
                        "delete_after": {"$lt": now},
                        "status": "active"
                    },
                    {
                        "$set": {
                            "status": "deleted",
                            "deleted_at": now
                        }
                    }
                )
                cleanup_results[priority] = result.modified_count
                
                # Hard delete after 24 hours in deleted status
                hard_delete_cutoff = now - timedelta(hours=24)
                hard_delete_result = await self.db.events.delete_many({
                    "status": "deleted",
                    "deleted_at": {"$lt": hard_delete_cutoff}
                })
                
                logger.info(f"Cleaned up {result.modified_count} {priority} priority events")
                logger.info(f"Hard deleted {hard_delete_result.deleted_count} events")
        
        return cleanup_results
    
    async def get_retention_stats(self) -> Dict:
        """Get statistics on current retention by source"""
        stats = {}
        
        for priority, policy in self.retention_policies.items():
            for source in policy['sources']:
                active_count = await self.db.events.count_documents({
                    "source": source,
                    "status": "active"
                })
                
                expired_count = await self.db.events.count_documents({
                    "source": source,
                    "status": "deleted"
                })
                
                stats[source] = {
                    "active_events": active_count,
                    "expired_events": expired_count,
                    "retention_days": policy['retention_days'],
                    "priority": priority
                }
        
        return stats
    
    def get_source_priority(self, source: str) -> str:
        """Determine source priority for retention policy"""
        for priority, policy in self.retention_policies.items():
            if source in policy['sources']:
                return priority
        return 'low'  # Default to low priority for unknown sources 