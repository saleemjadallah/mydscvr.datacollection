#!/usr/bin/env python3
"""
Debug script to test search functionality
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import re
import traceback

async def test_search_pipeline():
    client = AsyncIOMotorClient(settings.mongodb_url, tls=True, tlsAllowInvalidCertificates=True)
    db = client[settings.mongodb_database]
    
    try:
        print("Testing MongoDB search aggregation pipeline...")
        
        # Test 1: Basic count
        total_count = await db.events.count_documents({"status": "active"})
        print(f"Total active events: {total_count}")
        
        # Test 2: Simple brunch search
        query = "brunch"
        query_lower = query.lower().strip()
        
        pipeline = []
        
        # Stage 1: Base match with text search
        match_stage = {
            "status": "active",
            "$or": [
                {"title": {"$regex": f".*{re.escape(query_lower)}.*", "$options": "i"}},
                {"tags": {"$regex": f".*{re.escape(query_lower)}.*", "$options": "i"}},
                {"category": {"$regex": f".*{re.escape(query_lower)}.*", "$options": "i"}},
                {"venue.name": {"$regex": f".*{re.escape(query_lower)}.*", "$options": "i"}},
                {"description": {"$regex": f".*{re.escape(query_lower)}.*", "$options": "i"}}
            ]
        }
        
        pipeline.append({"$match": match_stage})
        pipeline.append({"$sort": {"start_date": 1}})
        pipeline.append({"$limit": 10})
        
        print(f"Executing pipeline with {len(pipeline)} stages")
        print(f"Match stage OR conditions: {len(match_stage['$or'])}")
        
        # Execute aggregation
        events = await db.events.aggregate(pipeline).to_list(10)
        print(f"Found {len(events)} events matching '{query}'")
        
        for i, event in enumerate(events):
            print(f"{i+1}. {event.get('title')} | Category: {event.get('category')} | Tags: {event.get('tags', [])[:3]}")
        
        # Test 3: Count using separate aggregation
        count_pipeline = [
            {"$match": match_stage},
            {"$count": "total"}
        ]
        
        count_result = await db.events.aggregate(count_pipeline).to_list(1)
        total_matches = count_result[0]["total"] if count_result else 0
        print(f"Total matching events: {total_matches}")
        
        return True
        
    except Exception as e:
        print(f"Error in search test: {str(e)}")
        traceback.print_exc()
        return False
    finally:
        client.close()

if __name__ == "__main__":
    success = asyncio.run(test_search_pipeline())
    print(f"Search test {'PASSED' if success else 'FAILED'}")