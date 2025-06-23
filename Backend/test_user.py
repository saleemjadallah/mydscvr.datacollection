#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/saleemjadallah/Desktop/DXB-events/Backend')

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from config import settings

async def test_user():
    print("Testing User Authentication Issues")
    print("="*50)
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]
    
    user_id = "685039d473278289fd09506b"
    print(f"Looking for user ID: {user_id}")
    
    try:
        # Check if user exists
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            print("✅ User found in database")
            print(f"   Email: {user.get('email')}")
            print(f"   Is Active: {user.get('is_active', True)}")
            print(f"   Email Verified: {user.get('is_email_verified', False)}")
            print(f"   Hearted Events: {len(user.get('hearted_events', []))}")
            print(f"   Saved Events: {len(user.get('saved_events', []))}")
        else:
            print("❌ User not found in database")
            
            # Check if there are any users at all
            total_users = await db.users.count_documents({})
            print(f"Total users in database: {total_users}")
            
            # Show a few user IDs for comparison
            sample_users = await db.users.find({}, {"_id": 1, "email": 1}).limit(5).to_list(5)
            print("Sample user IDs:")
            for u in sample_users:
                print(f"   {u['_id']} - {u.get('email')}")
    
    except Exception as e:
        print(f"❌ Error checking user: {e}")
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_user())