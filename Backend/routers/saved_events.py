"""
MongoDB-based saved events management router for DXB Events API
Removed PostgreSQL dependencies - MongoDB only implementation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from database import get_mongodb
from services.mongodb_auth import MongoAuthService
from models.user_models import UserModel
from utils.auth_dependencies import get_current_user as get_current_user_dependency, get_auth_service
from routers.events import _convert_event_to_response

router = APIRouter(prefix="/api/saved-events", tags=["saved-events"])


async def get_current_verified_user(
    current_user: UserModel = Depends(get_current_user_dependency)
) -> UserModel:
    """Get current verified user (MongoDB-based)"""
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


@router.get("/list", response_model=Dict[str, Any])
async def get_saved_events(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    area: Optional[str] = Query(None, description="Filter by Dubai area"),
    sort_by: str = Query("saved_date", description="Sort by: saved_date, event_date, title, price"),
    current_user: UserModel = Depends(get_current_verified_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get all saved events for the current user with filtering and pagination (MongoDB-based)
    """
    try:
        # Get user's saved event IDs from MongoDB
        saved_event_ids = current_user.saved_events or []
        
        if not saved_event_ids:
            return {
                "saved_events": [],
                "pagination": {
                    "page": page,
                    "per_page": limit,
                    "total": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }
        
        # Build MongoDB filter
        mongo_filter = {"_id": {"$in": saved_event_ids}}
        if category:
            mongo_filter["category_tags"] = {"$in": [category]}
        if area:
            mongo_filter["area"] = area
        
        # Build sort criteria
        sort_mapping = {
            "saved_date": [("_id", 1)],
            "event_date": [("start_date", 1)],
            "title": [("title", 1)],
            "price": [("price_min", 1)]
        }
        sort_criteria = sort_mapping.get(sort_by, [("start_date", 1)])
        
        # Get total count
        total_count = await db.events.count_documents(mongo_filter)
        
        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit
        skip = (page - 1) * limit
        
        # Get events from MongoDB
        events_cursor = db.events.find(mongo_filter).sort(sort_criteria).skip(skip).limit(limit)
        events = await events_cursor.to_list(length=limit)
        
        # Convert to response format
        event_responses = []
        for event in events:
            event_responses.append(await _convert_event_to_response(event))
        
        return {
            "saved_events": event_responses,
            "pagination": {
                "page": page,
                "per_page": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved events: {str(e)}"
        )


@router.get("/categories", response_model=Dict[str, Any])
async def get_saved_events_categories(
    current_user: UserModel = Depends(get_current_verified_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get all categories from user's saved events (MongoDB-based)
    """
    try:
        saved_event_ids = current_user.saved_events or []
        
        if not saved_event_ids:
            return {"categories": []}
        
        # Get categories from saved events
        pipeline = [
            {"$match": {"_id": {"$in": saved_event_ids}}},
            {"$unwind": "$category_tags"},
            {"$group": {"_id": "$category_tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        categories_cursor = db.events.aggregate(pipeline)
        categories = []
        
        async for category in categories_cursor:
            categories.append({
                "name": category["_id"],
                "count": category["count"]
            })
        
        return {"categories": categories}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved events categories: {str(e)}"
        )


@router.get("/stats", response_model=Dict[str, Any])
async def get_saved_events_stats(
    current_user: UserModel = Depends(get_current_verified_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get statistics for user's saved events (MongoDB-based)
    """
    try:
        saved_event_ids = current_user.saved_events or []
        hearted_event_ids = current_user.hearted_events or []
        
        stats = {
            "total_saved": len(saved_event_ids),
            "total_hearted": len(hearted_event_ids),
            "total_interactions": len(set(saved_event_ids + hearted_event_ids))
        }
        
        if saved_event_ids:
            # Get category breakdown
            pipeline = [
                {"$match": {"_id": {"$in": saved_event_ids}}},
                {"$unwind": "$category_tags"},
                {"$group": {"_id": "$category_tags", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
            
            categories_cursor = db.events.aggregate(pipeline)
            top_categories = []
            
            async for category in categories_cursor:
                top_categories.append({
                    "name": category["_id"],
                    "count": category["count"]
                })
            
            stats["top_categories"] = top_categories
        else:
            stats["top_categories"] = []
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get saved events stats: {str(e)}"
        )


# Legacy endpoints for backward compatibility - redirect to MongoDB auth endpoints
@router.post("/{event_id}/save")
async def legacy_save_event(
    event_id: str,
    current_user: UserModel = Depends(get_current_verified_user),
    auth_service: MongoAuthService = Depends(get_auth_service)
):
    """
    Legacy save event endpoint - redirects to MongoDB implementation
    """
    try:
        success, message = await auth_service.save_event(current_user.id, event_id)
        
        if success:
            return {
                "success": True,
                "message": message or "Event saved successfully",
                "data": {"event_id": event_id, "status": "saved"}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message or "Failed to save event"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save event: {str(e)}"
        )


@router.delete("/{event_id}/save")
async def legacy_unsave_event(
    event_id: str,
    current_user: UserModel = Depends(get_current_verified_user),
    auth_service: MongoAuthService = Depends(get_auth_service)
):
    """
    Legacy unsave event endpoint - redirects to MongoDB implementation
    """
    try:
        success, message = await auth_service.unsave_event(current_user.id, event_id)
        
        if success:
            return {
                "success": True,
                "message": message or "Event removed from favorites",
                "data": {"event_id": event_id, "status": "unsaved"}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message or "Failed to unsave event"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsave event: {str(e)}"
        ) 