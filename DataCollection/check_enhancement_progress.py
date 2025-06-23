#!/usr/bin/env python3
"""
Script to check the progress of event enhancement
Shows statistics about how many events have been enhanced
"""

import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'Mongo.env'))

def check_enhancement_progress():
    """
    Check and display enhancement progress statistics
    """
    # Connect to MongoDB
    mongodb_uri = os.getenv('Mongo_URI')
    database_name = os.getenv('MONGO_DB_NAME', 'DXB')
    
    client = MongoClient(
        mongodb_uri,
        serverSelectionTimeoutMS=5000,
        tlsInsecure=True
    )
    
    # Test connection
    client.admin.command('ping')
    
    db = client[database_name]
    events_collection = db['events']
    
    logger.info("📊 ENHANCEMENT PROGRESS REPORT")
    logger.info("=" * 50)
    
    # Total events
    total_events = events_collection.count_documents({})
    logger.info(f"📈 Total events in collection: {total_events}")
    
    # Events with enhanced fields
    enhanced_events = events_collection.count_documents({
        "$and": [
            {"social_media": {"$exists": True}},
            {"event_url": {"$exists": True}},
            {"quality_metrics": {"$exists": True}}
        ]
    })
    
    # Events with at least some enhanced fields
    partially_enhanced = events_collection.count_documents({
        "$or": [
            {"social_media": {"$exists": True}},
            {"event_url": {"$exists": True}},
            {"quality_metrics": {"$exists": True}},
            {"target_audience": {"$exists": True}},
            {"venue_type": {"$exists": True}}
        ]
    })
    
    # Events enhanced today
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    enhanced_today = events_collection.count_documents({
        "enhancement_metadata.enhanced_at": {"$gte": today_start}
    })
    
    # Recent events (last 6 months) needing enhancement
    six_months_ago = datetime.now() - timedelta(days=180)
    recent_events_total = events_collection.count_documents({
        "start_date": {"$gte": six_months_ago}
    })
    
    recent_events_needing_enhancement = events_collection.count_documents({
        "$and": [
            {"start_date": {"$gte": six_months_ago}},
            {
                "$or": [
                    {"social_media": {"$exists": False}},
                    {"event_url": {"$exists": False}},
                    {"quality_metrics": {"$exists": False}},
                    {"target_audience": {"$exists": False}},
                    {"venue_type": {"$exists": False}}
                ]
            }
        ]
    })
    
    logger.info(f"✅ Fully enhanced events: {enhanced_events}")
    logger.info(f"🔄 Partially enhanced events: {partially_enhanced}")
    logger.info(f"🆕 Enhanced today: {enhanced_today}")
    logger.info("")
    logger.info(f"📅 Recent events (last 6 months): {recent_events_total}")
    logger.info(f"⏳ Recent events needing enhancement: {recent_events_needing_enhancement}")
    
    if total_events > 0:
        enhancement_rate = (enhanced_events / total_events) * 100
        logger.info(f"📊 Overall enhancement rate: {enhancement_rate:.1f}%")
    
    if recent_events_total > 0:
        recent_enhancement_rate = ((recent_events_total - recent_events_needing_enhancement) / recent_events_total) * 100
        logger.info(f"📊 Recent events enhancement rate: {recent_enhancement_rate:.1f}%")
    
    logger.info("")
    
    # Show breakdown by enhanced fields
    logger.info("📋 FIELD-SPECIFIC BREAKDOWN:")
    logger.info("-" * 30)
    
    field_stats = {}
    fields_to_check = [
        "social_media",
        "event_url", 
        "quality_metrics",
        "target_audience",
        "venue_type",
        "age_restrictions",
        "transportation_notes",
        "contact_info"
    ]
    
    for field in fields_to_check:
        count = events_collection.count_documents({field: {"$exists": True}})
        percentage = (count / total_events) * 100 if total_events > 0 else 0
        logger.info(f"  {field}: {count} ({percentage:.1f}%)")
    
    logger.info("")
    
    # Show recent enhancement activity
    logger.info("🕒 RECENT ENHANCEMENT ACTIVITY:")
    logger.info("-" * 35)
    
    # Last 24 hours
    yesterday = datetime.now() - timedelta(days=1)
    enhanced_24h = events_collection.count_documents({
        "enhancement_metadata.enhanced_at": {"$gte": yesterday}
    })
    
    # Last week
    last_week = datetime.now() - timedelta(days=7)
    enhanced_week = events_collection.count_documents({
        "enhancement_metadata.enhanced_at": {"$gte": last_week}
    })
    
    logger.info(f"  Last 24 hours: {enhanced_24h} events")
    logger.info(f"  Last 7 days: {enhanced_week} events")
    
    logger.info("=" * 50)
    
    # Close connection
    client.close()

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )
    
    check_enhancement_progress()