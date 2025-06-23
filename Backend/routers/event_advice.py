from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING, ASCENDING
from bson import ObjectId
import os
from dotenv import load_dotenv

from models.advice_models import (
    EventAdviceModel, 
    EventAdviceStatsModel,
    AdviceFilterModel,
    CreateAdviceModel,
    AdviceInteractionModel,
    AdviceCategory,
    AdviceType
)
from utils.auth_dependencies import get_current_user
from models.user_models import UserModel

load_dotenv()

router = APIRouter(prefix="/api/advice", tags=["Event Advice"])

# MongoDB connection
try:
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    client = MongoClient(MONGO_URL)
    db = client.DXB
    advice_collection = db.event_advice
    events_collection = db.events
    users_collection = db.users
except Exception as e:
    print(f"MongoDB connection error: {e}")
    advice_collection = None


@router.get("/event/{event_id}", response_model=List[EventAdviceModel])
async def get_event_advice(
    event_id: str,
    category: Optional[AdviceCategory] = None,
    advice_type: Optional[AdviceType] = None,
    verified_only: bool = False,
    featured_only: bool = False,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("helpfulness_rating", description="helpfulness_rating, created_at"),
    sort_order: str = Query("desc", description="asc or desc")
):
    """Get advice for a specific event"""
    if not advice_collection:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Build query
        query = {"event_id": event_id}
        
        if category:
            query["category"] = category.value
        
        if advice_type:
            query["advice_type"] = advice_type.value
        
        if verified_only:
            query["is_verified"] = True
        
        if featured_only:
            query["is_featured"] = True
        
        # Build sort
        sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
        sort_field = sort_by
        
        # Execute query
        cursor = advice_collection.find(query).sort(sort_field, sort_direction).skip(offset).limit(limit)
        advice_list = []
        
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            advice_list.append(EventAdviceModel(**doc))
        
        return advice_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching advice: {str(e)}")


@router.post("/create", response_model=EventAdviceModel)
async def create_advice(
    advice_data: CreateAdviceModel,
    current_user: UserModel = Depends(get_current_user)
):
    """Create new advice for an event"""
    if not advice_collection:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Verify event exists
        event = events_collection.find_one({"_id": ObjectId(advice_data.event_id)})
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Check if user already provided advice for this event
        existing_advice = advice_collection.find_one({
            "event_id": advice_data.event_id,
            "user_id": str(current_user.id)
        })
        
        if existing_advice:
            raise HTTPException(
                status_code=400, 
                detail="You have already provided advice for this event. You can update your existing advice instead."
            )
        
        # Create advice document
        advice_doc = {
            "event_id": advice_data.event_id,
            "user_id": str(current_user.id),
            "user_name": current_user.name or current_user.email.split('@')[0],
            "user_avatar": getattr(current_user, 'avatar_url', None),
            "title": advice_data.title,
            "content": advice_data.content,
            "category": advice_data.category.value,
            "advice_type": advice_data.advice_type.value,
            "experience_date": advice_data.experience_date,
            "venue_familiarity": advice_data.venue_familiarity,
            "similar_events_attended": advice_data.similar_events_attended,
            "helpfulness_rating": 0.0,
            "helpfulness_votes": 0,
            "is_verified": False,
            "is_featured": False,
            "helpful_users": [],
            "reported_by": [],
            "tags": advice_data.tags,
            "language": advice_data.language,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = advice_collection.insert_one(advice_doc)
        advice_doc["_id"] = str(result.inserted_id)
        
        return EventAdviceModel(**advice_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating advice: {str(e)}")


@router.put("/update/{advice_id}", response_model=EventAdviceModel)
async def update_advice(
    advice_id: str,
    advice_data: CreateAdviceModel,
    current_user: UserModel = Depends(get_current_user)
):
    """Update existing advice"""
    if not advice_collection:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Find existing advice
        existing_advice = advice_collection.find_one({"_id": ObjectId(advice_id)})
        if not existing_advice:
            raise HTTPException(status_code=404, detail="Advice not found")
        
        # Check ownership
        if existing_advice["user_id"] != str(current_user.id):
            raise HTTPException(status_code=403, detail="You can only update your own advice")
        
        # Update document
        update_data = {
            "title": advice_data.title,
            "content": advice_data.content,
            "category": advice_data.category.value,
            "advice_type": advice_data.advice_type.value,
            "experience_date": advice_data.experience_date,
            "venue_familiarity": advice_data.venue_familiarity,
            "similar_events_attended": advice_data.similar_events_attended,
            "tags": advice_data.tags,
            "language": advice_data.language,
            "updated_at": datetime.utcnow()
        }
        
        advice_collection.update_one(
            {"_id": ObjectId(advice_id)},
            {"$set": update_data}
        )
        
        # Return updated advice
        updated_advice = advice_collection.find_one({"_id": ObjectId(advice_id)})
        updated_advice["_id"] = str(updated_advice["_id"])
        
        return EventAdviceModel(**updated_advice)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating advice: {str(e)}")


@router.post("/interact/{advice_id}")
async def interact_with_advice(
    advice_id: str,
    interaction_type: str,
    reason: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user)
):
    """Mark advice as helpful, not helpful, or report it"""
    if not advice_collection:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    if interaction_type not in ["helpful", "not_helpful", "report"]:
        raise HTTPException(status_code=400, detail="Invalid interaction type")
    
    try:
        # Find advice
        advice = advice_collection.find_one({"_id": ObjectId(advice_id)})
        if not advice:
            raise HTTPException(status_code=404, detail="Advice not found")
        
        user_id = str(current_user.id)
        
        if interaction_type == "helpful":
            # Add user to helpful_users if not already there
            if user_id not in advice.get("helpful_users", []):
                advice_collection.update_one(
                    {"_id": ObjectId(advice_id)},
                    {
                        "$addToSet": {"helpful_users": user_id},
                        "$inc": {"helpfulness_votes": 1}
                    }
                )
                
                # Recalculate helpfulness rating
                updated_advice = advice_collection.find_one({"_id": ObjectId(advice_id)})
                helpfulness_rating = min(5.0, updated_advice["helpfulness_votes"] * 0.1)
                
                advice_collection.update_one(
                    {"_id": ObjectId(advice_id)},
                    {"$set": {"helpfulness_rating": helpfulness_rating}}
                )
        
        elif interaction_type == "not_helpful":
            # Remove user from helpful_users if there
            if user_id in advice.get("helpful_users", []):
                advice_collection.update_one(
                    {"_id": ObjectId(advice_id)},
                    {
                        "$pull": {"helpful_users": user_id},
                        "$inc": {"helpfulness_votes": -1}
                    }
                )
                
                # Recalculate helpfulness rating
                updated_advice = advice_collection.find_one({"_id": ObjectId(advice_id)})
                helpfulness_rating = max(0.0, updated_advice["helpfulness_votes"] * 0.1)
                
                advice_collection.update_one(
                    {"_id": ObjectId(advice_id)},
                    {"$set": {"helpfulness_rating": helpfulness_rating}}
                )
        
        elif interaction_type == "report":
            # Add user to reported_by if not already there
            if user_id not in advice.get("reported_by", []):
                advice_collection.update_one(
                    {"_id": ObjectId(advice_id)},
                    {"$addToSet": {"reported_by": user_id}}
                )
        
        return {"message": f"Advice {interaction_type} recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording interaction: {str(e)}")


@router.get("/stats/{event_id}", response_model=EventAdviceStatsModel)
async def get_advice_stats(event_id: str):
    """Get advice statistics for an event"""
    if not advice_collection:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Aggregate stats
        pipeline = [
            {"$match": {"event_id": event_id}},
            {
                "$group": {
                    "_id": None,
                    "total_advice": {"$sum": 1},
                    "average_helpfulness": {"$avg": "$helpfulness_rating"},
                    "verified_count": {"$sum": {"$cond": ["$is_verified", 1, 0]}},
                    "featured_count": {"$sum": {"$cond": ["$is_featured", 1, 0]}},
                    "categories": {"$push": "$category"},
                    "advice_types": {"$push": "$advice_type"},
                    "all_tags": {"$push": "$tags"}
                }
            }
        ]
        
        result = list(advice_collection.aggregate(pipeline))
        
        if not result:
            return EventAdviceStatsModel(
                event_id=event_id,
                total_advice=0,
                average_helpfulness=0.0,
                advice_by_category={},
                advice_by_type={},
                verified_advice_count=0,
                featured_advice_count=0,
                recent_advice_count=0,
                top_tags=[]
            )
        
        stats = result[0]
        
        # Count categories
        advice_by_category = {}
        for category in stats.get("categories", []):
            advice_by_category[category] = advice_by_category.get(category, 0) + 1
        
        # Count advice types
        advice_by_type = {}
        for advice_type in stats.get("advice_types", []):
            advice_by_type[advice_type] = advice_by_type.get(advice_type, 0) + 1
        
        # Count recent advice (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = advice_collection.count_documents({
            "event_id": event_id,
            "created_at": {"$gte": thirty_days_ago}
        })
        
        # Get top tags
        all_tags = []
        for tag_list in stats.get("all_tags", []):
            all_tags.extend(tag_list)
        
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        top_tags = sorted(tag_counts.keys(), key=lambda x: tag_counts[x], reverse=True)[:5]
        
        return EventAdviceStatsModel(
            event_id=event_id,
            total_advice=stats.get("total_advice", 0),
            average_helpfulness=round(stats.get("average_helpfulness", 0.0), 2),
            advice_by_category=advice_by_category,
            advice_by_type=advice_by_type,
            verified_advice_count=stats.get("verified_count", 0),
            featured_advice_count=stats.get("featured_count", 0),
            recent_advice_count=recent_count,
            top_tags=top_tags
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@router.delete("/delete/{advice_id}")
async def delete_advice(
    advice_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """Delete advice (only by owner or admin)"""
    if not advice_collection:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        # Find advice
        advice = advice_collection.find_one({"_id": ObjectId(advice_id)})
        if not advice:
            raise HTTPException(status_code=404, detail="Advice not found")
        
        # Check ownership or admin status
        is_admin = getattr(current_user, 'is_admin', False)
        if advice["user_id"] != str(current_user.id) and not is_admin:
            raise HTTPException(status_code=403, detail="You can only delete your own advice")
        
        # Delete advice
        advice_collection.delete_one({"_id": ObjectId(advice_id)})
        
        return {"message": "Advice deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting advice: {str(e)}")


@router.get("/categories", response_model=List[str])
async def get_advice_categories():
    """Get all available advice categories"""
    return [category.value for category in AdviceCategory]


@router.get("/types", response_model=List[str])
async def get_advice_types():
    """Get all available advice types"""
    return [advice_type.value for advice_type in AdviceType]


@router.get("/user/{user_id}", response_model=List[EventAdviceModel])
async def get_user_advice(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user)
):
    """Get advice provided by a specific user"""
    if not advice_collection:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    # Only allow users to see their own advice or public advice
    if user_id != str(current_user.id):
        # For now, return empty list for other users' advice
        # In the future, you might want to return public advice only
        return []
    
    try:
        cursor = advice_collection.find(
            {"user_id": user_id}
        ).sort("created_at", DESCENDING).skip(offset).limit(limit)
        
        advice_list = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            advice_list.append(EventAdviceModel(**doc))
        
        return advice_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user advice: {str(e)}") 