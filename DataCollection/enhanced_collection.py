#!/usr/bin/env python3
"""
Fix storage issue and store the 233 collected events
"""

import asyncio
import json
from perplexity_events_extractor import DubaiEventsPerplexityExtractor
from perplexity_storage import PerplexityEventsStorage
from loguru import logger

async def collect_and_store_events():
    try:
        extractor = DubaiEventsPerplexityExtractor()
        storage = PerplexityEventsStorage()
        
        logger.info('🚀 Starting event discovery...')
        
        # Get the events data
        all_events = await extractor.discover_events_by_categories()
        
        logger.info(f'📊 Total unique events found: {len(all_events)}')
        logger.info(f'🔍 Sample event type: {type(all_events[0]) if all_events else "No events"}')
        
        if all_events:
            # Debug: Print first event structure
            logger.info(f'📋 First event keys: {list(all_events[0].keys()) if all_events else "None"}')
            
            # Create extraction session
            session_id = storage.create_extraction_session('fixed_collection_enhanced_dedup')
            logger.info(f'📝 Created session: {session_id}')
            
            # Store events one by one to identify exact issue
            stored_count = 0
            for i, event in enumerate(all_events):
                try:
                    # Verify event is a dictionary
                    if not isinstance(event, dict):
                        logger.error(f"❌ Event {i} is not a dict: {type(event)}")
                        continue
                    
                    # Store single event with deduplication
                    result = await storage.store_events([event], session_id)
                    
                    if result.get('stored_count', 0) > 0:
                        stored_count += 1
                        if stored_count % 10 == 0:
                            logger.info(f"✅ Stored {stored_count} events so far...")
                    
                except Exception as e:
                    logger.error(f"❌ Error storing event {i}: {e}")
                    logger.error(f"Event data: {json.dumps(event, indent=2, default=str)}")
                    continue
            
            logger.info(f"✅ Successfully stored {stored_count} out of {len(all_events)} events")
            
            # Update session
            storage.update_extraction_session(session_id, {
                'total_events': len(all_events),
                'stored_events': stored_count,
                'status': 'completed'
            })
        
        storage.close()
        return len(all_events) if all_events else 0
        
    except Exception as e:
        logger.error(f'❌ Error: {e}')
        import traceback
        logger.error(f'Full traceback: {traceback.format_exc()}')
        return 0

if __name__ == "__main__":
    result = asyncio.run(collect_and_store_events())
    logger.success(f'✅ Collection completed! Total events discovered: {result}')