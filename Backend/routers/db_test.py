"""
Database testing router for DXB Events API
Testing database connections and Phase 2 sample data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_mongodb

router = APIRouter(prefix="/api/db", tags=["database"])


@router.get("/test")
async def test_mongodb_connection(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """Test MongoDB connection and basic operations"""
    try:
        # Test connection
        await db.command("ping")
        
        # Test collection access
        collections = await db.list_collection_names()
        
        # Test basic operations
        test_doc = {"test": "connection", "timestamp": "2025-01-15T10:00:00Z"}
        result = await db.test_collection.insert_one(test_doc)
        
        # Clean up test document
        await db.test_collection.delete_one({"_id": result.inserted_id})
        
        return {
            "status": "success",
            "message": "MongoDB connection successful",
            "database": "DXB",
            "collections": collections,
            "test_operation": "passed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB connection failed: {str(e)}")


@router.post("/populate-sample-events")
async def populate_sample_events_endpoint(
    count: int = Query(50, ge=10, le=200, description="Number of sample events to create"),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Populate database with sample events for testing Phase 2 functionality
    """
    try:
        from utils.sample_data import populate_sample_events
        
        result_count = await populate_sample_events(db, count)
        
        return {
            "message": f"Successfully populated {result_count} sample events",
            "count": result_count,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to populate sample events: {str(e)}"
        )


@router.get("/events-stats")
async def get_events_stats(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """
    Get statistics about events in the database
    """
    try:
        # Total events
        total_events = await db.events.count_documents({})
        
        # Active events
        active_events = await db.events.count_documents({"status": "active"})
        
        # Family friendly events
        family_events = await db.events.count_documents({"is_family_friendly": True})
        
        # Categories distribution
        categories_pipeline = [
            {"$unwind": "$category_tags"},
            {"$group": {"_id": "$category_tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        categories = await db.events.aggregate(categories_pipeline).to_list(length=10)
        
        # Areas distribution
        areas_pipeline = [
            {"$group": {"_id": "$area", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        areas = await db.events.aggregate(areas_pipeline).to_list(length=10)
        
        return {
            "total_events": total_events,
            "active_events": active_events,
            "family_friendly_events": family_events,
            "top_categories": categories,
            "top_areas": areas,
            "database_status": "connected"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get events stats: {str(e)}"
        ) 