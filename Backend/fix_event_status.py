#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from datetime import datetime

async def fix_event_status():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]
    
    print("🔧 Fixing Event Status Fields...")
    print("=" * 50)
    
    # Check current status distribution
    print("📊 Current Status Distribution:")
    statuses = await db.events.distinct("status")
    for status in statuses:
        count = await db.events.count_documents({"status": status})
        print(f"  • {status}: {count} events")
    
    # Count events that need status update
    events_without_active_status = await db.events.count_documents({
        "$or": [
            {"status": {"$ne": "active"}},
            {"status": {"$exists": False}},
            {"status": None}
        ]
    })
    
    print(f"\n🎯 Events needing status update: {events_without_active_status}")
    
    if events_without_active_status > 0:
        # Update all events to have status "active"
        result = await db.events.update_many(
            {
                "$or": [
                    {"status": {"$ne": "active"}},
                    {"status": {"$exists": False}},
                    {"status": None}
                ]
            },
            {
                "$set": {
                    "status": "active",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        print(f"✅ Updated {result.modified_count} events to active status")
    
    # Verify the fix
    print("\n📊 Updated Status Distribution:")
    statuses = await db.events.distinct("status")
    for status in statuses:
        count = await db.events.count_documents({"status": status})
        print(f"  • {status}: {count} events")
    
    # Check how many events should now be returned by the API
    current_time = datetime.utcnow()
    api_filter = {
        "status": "active",
        "end_date": {"$gte": current_time}
    }
    
    api_eligible_events = await db.events.count_documents(api_filter)
    print(f"\n🎯 Events that should be returned by API: {api_eligible_events}")
    
    # Show sample of what API should return
    sample_events = await db.events.find(api_filter).limit(3).to_list(length=3)
    print(f"\n📄 Sample events that API will return:")
    for i, event in enumerate(sample_events):
        print(f"  {i+1}. {event.get('title', 'No title')} - {event.get('start_date')} - Status: {event.get('status')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(fix_event_status())