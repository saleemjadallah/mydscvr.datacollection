from fastapi import APIRouter, Depends, HTTPException
from database import get_mongodb, test_mongodb_connection
from schemas import SuccessResponse
import datetime

router = APIRouter(prefix="/api/test", tags=["Database Testing"])


@router.get("/mongodb")
async def test_mongodb():
    """Test MongoDB Atlas connection and show database info"""
    try:
        result = await test_mongodb_connection()
        return {
            "success": True,
            "message": "MongoDB Atlas connection test",
            "data": result,
            "timestamp": datetime.datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB connection failed: {str(e)}"
        )


@router.get("/mongodb/collections")
async def list_mongodb_collections(db = Depends(get_mongodb)):
    """List all collections in the MongoDB database"""
    try:
        collections = await db.list_collection_names()
        return {
            "success": True,
            "message": f"Collections in DXB database",
            "data": {
                "collections": collections,
                "count": len(collections)
            },
            "timestamp": datetime.datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list collections: {str(e)}"
        )


@router.post("/mongodb/sample-event")
async def create_sample_event(db = Depends(get_mongodb)):
    """Create a sample event in MongoDB for testing"""
    try:
        sample_event = {
            "title": "Test Family Event - Dubai Marina",
            "description": "A sample family-friendly event for testing the DXB Events platform",
            "start_date": datetime.datetime.utcnow() + datetime.timedelta(days=7),
            "end_date": datetime.datetime.utcnow() + datetime.timedelta(days=7, hours=3),
            "venue_name": "Dubai Marina Mall",
            "venue_address": "Dubai Marina, Dubai, UAE",
            "location": {
                "lat": 25.0775,
                "lng": 55.1394
            },
            "price_min": 0,
            "price_max": 50,
            "currency": "AED",
            "age_min": 0,
            "age_max": 99,
            "category_tags": ["family", "outdoor", "dubai-marina"],
            "source_name": "test-data",
            "is_family_friendly": True,
            "family_score": 85,
            "area": "Dubai Marina",
            "language": "en",
            "is_active": True,
            "created_at": datetime.datetime.utcnow()
        }
        
        # Insert the sample event
        result = await db.events.insert_one(sample_event)
        
        return {
            "success": True,
            "message": "Sample event created successfully",
            "data": {
                "event_id": str(result.inserted_id),
                "event_title": sample_event["title"]
            },
            "timestamp": datetime.datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create sample event: {str(e)}"
        )


@router.get("/mongodb/events")
async def list_events(limit: int = 10, db = Depends(get_mongodb)):
    """List events from MongoDB"""
    try:
        cursor = db.events.find().limit(limit)
        events = []
        
        async for event in cursor:
            # Convert ObjectId to string for JSON serialization
            event["_id"] = str(event["_id"])
            events.append(event)
        
        return {
            "success": True,
            "message": f"Retrieved {len(events)} events from MongoDB",
            "data": {
                "events": events,
                "count": len(events)
            },
            "timestamp": datetime.datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve events: {str(e)}"
        )


@router.delete("/mongodb/events")
async def clear_test_events(db = Depends(get_mongodb)):
    """Clear all test events from MongoDB"""
    try:
        result = await db.events.delete_many({"source_name": "test-data"})
        
        return {
            "success": True,
            "message": f"Deleted {result.deleted_count} test events",
            "data": {
                "deleted_count": result.deleted_count
            },
            "timestamp": datetime.datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete test events: {str(e)}"
        ) 