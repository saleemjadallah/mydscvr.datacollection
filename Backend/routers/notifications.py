"""
MongoDB-based notifications router for DXB Events API
Removed PostgreSQL dependencies - MongoDB only implementation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from database import get_mongodb
from services.mongodb_auth import MongoAuthService, get_auth_service
from models.user_models import UserModel
from utils.auth_dependencies import get_current_user as get_current_user_dependency

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


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
async def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    current_user: UserModel = Depends(get_current_verified_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get user notifications (MongoDB-based)
    """
    try:
        # Build filter for user notifications
        filter_criteria = {"user_id": current_user.id}
        if unread_only:
            filter_criteria["read"] = False
        
        # Get total count
        total_count = await db.notifications.count_documents(filter_criteria)
        
        # Calculate pagination
        total_pages = (total_count + limit - 1) // limit
        skip = (page - 1) * limit
        
        # Get notifications
        notifications_cursor = db.notifications.find(filter_criteria).sort("created_at", -1).skip(skip).limit(limit)
        notifications = await notifications_cursor.to_list(length=limit)
        
        return {
            "notifications": notifications,
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
            detail=f"Failed to get notifications: {str(e)}"
        )


@router.post("/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: str,
    current_user: UserModel = Depends(get_current_verified_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Mark a notification as read
    """
    try:
        result = await db.notifications.update_one(
            {"_id": notification_id, "user_id": current_user.id},
            {"$set": {"read": True, "read_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return {
            "success": True,
            "message": "Notification marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.get("/unread-count")
async def get_unread_count(
    current_user: UserModel = Depends(get_current_verified_user),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get count of unread notifications
    """
    try:
        unread_count = await db.notifications.count_documents({
            "user_id": current_user.id,
            "read": False
        })
        
        return {
            "unread_count": unread_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unread count: {str(e)}"
        ) 