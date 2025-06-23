#!/usr/bin/env python3
"""
Automated deduplication runner for DXB Events
Runs after event collection to remove duplicates
"""

import asyncio
import os
import sys
from datetime import datetime
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_mongodb_database
from utils.deduplication import EventDeduplicator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/deduplication.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def run_deduplication():
    """Run the deduplication process"""
    try:
        logger.info("🔍 Starting automated deduplication process...")
        
        # Get database connection
        mongodb = await get_mongodb_database()
        deduplicator = EventDeduplicator(mongodb)
        
        # Get current stats
        logger.info("📊 Getting current database statistics...")
        stats = await deduplicator.get_duplicate_statistics()
        
        total_events = stats.get('total_events', 0)
        estimated_duplicates = stats.get('estimated_duplicates', 0)
        
        logger.info(f"📈 Total events: {total_events}")
        logger.info(f"🔄 Estimated duplicates: {estimated_duplicates}")
        
        if estimated_duplicates == 0:
            logger.info("✅ No duplicates found - database is clean!")
            return
        
        # Find and process duplicates
        logger.info("🔍 Finding potential duplicates...")
        potential_duplicates = await deduplicator.find_potential_duplicates(limit=50)
        
        removed_count = 0
        for duplicate_info in potential_duplicates:
            try:
                # Process each duplicate pair
                similarity_score = duplicate_info.get('similarity_score', 0)
                if similarity_score >= 0.75:  # 75% threshold
                    # Remove the duplicate (keep the older one)
                    duplicate_id = duplicate_info.get('duplicate_id')
                    if duplicate_id:
                        await mongodb.events.delete_one({"_id": duplicate_id})
                        removed_count += 1
                        logger.info(f"🗑️  Removed duplicate: {duplicate_info.get('title', 'Unknown')} (similarity: {similarity_score:.3f})")
            except Exception as e:
                logger.error(f"❌ Error processing duplicate: {e}")
                continue
        
        logger.info(f"✅ Deduplication complete! Removed {removed_count} duplicates")
        
        # Log final stats
        final_stats = await deduplicator.get_duplicate_statistics()
        final_total = final_stats.get('total_events', 0)
        logger.info(f"📊 Final event count: {final_total} (reduced by {total_events - final_total})")
        
    except Exception as e:
        logger.error(f"❌ Error in deduplication process: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_deduplication()) 