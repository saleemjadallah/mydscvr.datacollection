from datetime import datetime, timedelta
from typing import List, Dict
import logging
from .source_based_cleanup import SourceBasedRetentionManager

logger = logging.getLogger(__name__)

class ScrapingDataHandler:
    def __init__(self, retention_manager: SourceBasedRetentionManager, db_client):
        self.retention_manager = retention_manager
        self.db = db_client
    
    async def store_scraped_events(self, source: str, events: List[dict]) -> int:
        """Store scraped events with automatic retention setup"""
        stored_count = 0
        
        for event_data in events:
            # Check for duplicates
            if await self.is_duplicate_event(source, event_data):
                continue
            
            # Set source priority and retention
            priority = self.retention_manager.get_source_priority(source)
            retention_days = self.retention_manager.retention_policies[priority]['retention_days']
            
            # Calculate delete_after if event has end_date
            delete_after = None
            if event_data.get('end_date'):
                delete_after = event_data['end_date'] + timedelta(days=retention_days)
            
            # Prepare event document
            event_doc = {
                **event_data,
                "source": source,
                "source_priority": priority,
                "retention_days": retention_days,
                "delete_after": delete_after,
                "status": "active",
                "scraped_at": datetime.now(),
                "view_count": 0,
                "save_count": 0,
                "click_count": 0
            }
            
            # Ensure required fields are present
            if 'created_at' not in event_doc:
                event_doc['created_at'] = datetime.now()
            if 'last_updated' not in event_doc:
                event_doc['last_updated'] = datetime.now()
            
            # Insert to database
            await self.db.events.insert_one(event_doc)
            stored_count += 1
        
        logger.info(f"Stored {stored_count} new events from {source}")
        return stored_count
    
    async def is_duplicate_event(self, source: str, event_data: dict) -> bool:
        """Check if event already exists"""
        # Simple duplicate check based on title and date
        existing = await self.db.events.find_one({
            "source": source,
            "title": event_data.get('title'),
            "start_date": event_data.get('start_date'),
            "status": {"$ne": "deleted"}
        })
        return existing is not None
    
    async def update_event_retention(self, event_id: str, new_source: str = None) -> bool:
        """Update retention policy for a specific event"""
        try:
            event = await self.db.events.find_one({"_id": event_id})
            if not event:
                return False
            
            source = new_source or event.get('source')
            if not source:
                return False
            
            priority = self.retention_manager.get_source_priority(source)
            retention_days = self.retention_manager.retention_policies[priority]['retention_days']
            
            # Calculate new delete_after date
            delete_after = None
            if event.get('end_date'):
                delete_after = event['end_date'] + timedelta(days=retention_days)
            
            # Update the event
            await self.db.events.update_one(
                {"_id": event_id},
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
            
            return True
        except Exception as e:
            logger.error(f"Error updating event retention: {e}")
            return False
    
    async def bulk_update_source_retention(self, old_source: str, new_source: str) -> Dict[str, int]:
        """Bulk update retention policies when source changes"""
        try:
            # Get all events from old source
            events = await self.db.events.find({"source": old_source}).to_list(None)
            
            if not events:
                return {"updated": 0, "errors": 0}
            
            new_priority = self.retention_manager.get_source_priority(new_source)
            new_retention_days = self.retention_manager.retention_policies[new_priority]['retention_days']
            
            updated_count = 0
            error_count = 0
            
            for event in events:
                try:
                    # Calculate new delete_after date
                    delete_after = None
                    if event.get('end_date'):
                        delete_after = event['end_date'] + timedelta(days=new_retention_days)
                    
                    # Update the event
                    await self.db.events.update_one(
                        {"_id": event["_id"]},
                        {
                            "$set": {
                                "source": new_source,
                                "source_priority": new_priority,
                                "retention_days": new_retention_days,
                                "delete_after": delete_after,
                                "last_updated": datetime.now()
                            }
                        }
                    )
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating event {event.get('_id')}: {e}")
                    error_count += 1
            
            logger.info(f"Bulk updated {updated_count} events from {old_source} to {new_source}")
            return {"updated": updated_count, "errors": error_count}
            
        except Exception as e:
            logger.error(f"Error in bulk update: {e}")
            return {"updated": 0, "errors": 1} 