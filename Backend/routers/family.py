"""
MongoDB-based family features router for DXB Events API
Removed PostgreSQL dependencies - MongoDB only implementation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from database import get_mongodb
from services.mongodb_auth import MongoAuthService, get_auth_service
from models.user_models import UserModel
from utils.auth_dependencies import get_current_user as get_current_user_dependency

router = APIRouter(prefix="/api/family", tags=["family"])


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


@router.get("/members", response_model=Dict[str, Any])
async def get_family_members(
    current_user: UserModel = Depends(get_current_verified_user)
):
    """
    Get family members for the current user (MongoDB-based)
    """
    try:
        return {
            "family_members": current_user.family_members or [],
            "total_members": len(current_user.family_members or [])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get family members: {str(e)}"
        )


@router.post("/members", response_model=Dict[str, Any])
async def add_family_member(
    member_data: Dict[str, Any],
    current_user: UserModel = Depends(get_current_verified_user),
    auth_service: MongoAuthService = Depends(get_auth_service),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Add a family member (MongoDB-based)
    """
    try:
        # Update user's family members in MongoDB
        from bson import ObjectId
        
        result = await db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {
                "$push": {"family_members": member_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.matched_count > 0:
            return {
                "success": True,
                "message": "Family member added successfully",
                "member": member_data
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add family member: {str(e)}"
        )


@router.get("/recommendations", response_model=Dict[str, Any])
async def get_family_recommendations(
    current_user: UserModel = Depends(get_current_verified_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get family-friendly event recommendations (MongoDB-based)
    """
    try:
        # Build filter for family-friendly events
        family_filter = {
            "family_suitability.is_family_friendly": True,
            "status": "active"
        }
        
        # Get family-friendly events
        events_cursor = db.events.find(family_filter).sort("start_date", 1).limit(10)
        events = await events_cursor.to_list(length=10)
        
        return {
            "family_recommendations": events,
            "total_recommendations": len(events)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get family recommendations: {str(e)}"
        ) 