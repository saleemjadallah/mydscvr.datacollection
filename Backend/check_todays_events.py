#!/usr/bin/env python3
"""Check if new events were added today"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime

async def check_todays_events():
    load_dotenv('Mongo.env')
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client.DXB
    
    # Check events created today
    today_start = datetime(2025, 6, 18)
    events_today = await db.events.count_documents({"created_at": {"$gte": today_start}})
    print(f"Events created today (2025-06-18): {events_today}")
    
    # Get latest event
    latest = await db.events.find_one({}, sort=[("created_at", -1)])
    if latest:
        print(f"Latest event created: {latest.get('created_at')}")
        print(f"Latest event title: {latest.get('title')}")
    
    # Check total active events
    total_active = await db.events.count_documents({"status": "active"})
    print(f"Total active events: {total_active}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_todays_events())