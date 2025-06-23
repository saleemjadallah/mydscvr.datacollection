#!/usr/bin/env python3
"""
Quick test script to verify the enhancement system works
before running the full enhancement on existing events
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pymongo import MongoClient
from loguru import logger
from dotenv import load_dotenv

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import our enhanced extraction system
from perplexity_events_extractor import DubaiEventsPerplexityExtractor

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'Mongo.env'))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'AI_API.env'))

async def test_enhancement():
    """
    Test the enhancement system with a sample event
    """
    logger.info("🧪 Testing enhancement system...")
    
    # Connect to MongoDB to get a sample event
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
    
    # Get a sample event that doesn't have enhanced fields
    sample_event = events_collection.find_one({
        "$or": [
            {"social_media": {"$exists": False}},
            {"event_url": {"$exists": False}}
        ]
    })
    
    if not sample_event:
        logger.info("✅ All events already have enhanced fields!")
        return
    
    logger.info(f"📋 Testing with event: {sample_event.get('title', 'Unknown')}")
    
    # Initialize enhanced extractor
    extractor = DubaiEventsPerplexityExtractor()
    
    # Create search query for this event
    title = sample_event.get("title", "")
    venue_name = sample_event.get("venue", {}).get("name", "")
    area = sample_event.get("venue", {}).get("area", "Dubai")
    
    search_query = f'"{title}" "{venue_name}" {area} Dubai event'
    logger.info(f"🔍 Search query: {search_query}")
    
    # Extract enhanced data
    try:
        extraction_result = await extractor.search_and_extract_events(search_query)
        extracted_events = extraction_result.get('events', [])
        
        if extracted_events:
            logger.info(f"✅ Successfully extracted {len(extracted_events)} enhanced events")
            
            # Show what fields would be added
            first_result = extracted_events[0]
            enhanced_fields = []
            
            if first_result.get("social_media"):
                enhanced_fields.append("social_media")
            if first_result.get("event_url"):
                enhanced_fields.append("event_url")
            if first_result.get("quality_metrics"):
                enhanced_fields.append("quality_metrics")
            if first_result.get("target_audience"):
                enhanced_fields.append("target_audience")
            if first_result.get("venue_type"):
                enhanced_fields.append("venue_type")
            
            logger.info(f"📊 Would add these fields: {enhanced_fields}")
            
            # Show sample data
            logger.info("📋 Sample enhanced data:")
            if first_result.get("social_media"):
                logger.info(f"  Social Media: {first_result['social_media']}")
            if first_result.get("event_url"):
                logger.info(f"  Event URL: {first_result['event_url']}")
            if first_result.get("target_audience"):
                logger.info(f"  Target Audience: {first_result['target_audience']}")
            
            logger.info("✅ Enhancement test completed successfully!")
            
        else:
            logger.warning("⚠️ No enhanced data extracted")
            
    except Exception as e:
        logger.error(f"❌ Enhancement test failed: {e}")
        raise
    
    finally:
        client.close()

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )
    
    # Run the test
    asyncio.run(test_enhancement())