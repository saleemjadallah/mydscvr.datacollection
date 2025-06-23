#!/usr/bin/env python3
"""
Fix missing status field in existing events
"""

import os
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'Mongo.env'))

async def fix_missing_status():
    """Update all events without status field to have status: 'active'"""
    
    # Connect to MongoDB
    mongodb_uri = os.getenv('Mongo_URI')
    database_name = os.getenv('MONGO_DB_NAME', 'DXB')
    
    client = AsyncIOMotorClient(mongodb_uri)
    db = client[database_name]
    
    try:
        # Count events without status field
        events_without_status = await db.events.count_documents({
            "status": {"$exists": False}
        })
        print(f"Events without status field: {events_without_status}")
        
        # Count events with null status
        events_null_status = await db.events.count_documents({
            "status": None
        })
        print(f"Events with null status: {events_null_status}")
        
        # Update events without status field
        if events_without_status > 0:
            result1 = await db.events.update_many(
                {"status": {"$exists": False}},
                {"$set": {"status": "active", "updated_at": datetime.now()}}
            )
            print(f"✅ Updated {result1.modified_count} events without status field")
        
        # Update events with null status
        if events_null_status > 0:
            result2 = await db.events.update_many(
                {"status": None},
                {"$set": {"status": "active", "updated_at": datetime.now()}}
            )
            print(f"✅ Updated {result2.modified_count} events with null status")
        
        # Final count
        total_active = await db.events.count_documents({"status": "active"})
        total_events = await db.events.count_documents({})
        print(f"📊 Final stats: {total_active} active events out of {total_events} total")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_missing_status())