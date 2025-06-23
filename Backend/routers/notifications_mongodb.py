"""
MongoDB-based notification system router for DXB Events API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import logging

from database import get_mongodb
from models.notification_models import (
    Notification, NotificationCreate, NotificationUpdate,
    NotificationResponse, NotificationSettings, NotificationSettingsUpdate,
    NotificationStats, NotificationBatchCreate,
    NotificationType, NotificationPriority, NotificationStatus
)
from utils.auth_dependencies import get_current_user_dependency
from services.email_service import email_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for notification operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.notifications = db.notifications
        self.notification_settings = db.notification_settings
        
    async def create_notification(self, notification_data: NotificationCreate) -> Notification:
        """Create a new notification"""
        notification = Notification(**notification_data.dict())
        
        # Convert to dict for MongoDB
        notification_dict = notification.dict()
        notification_dict["_id"] = ObjectId()
        
        # Insert into database
        result = await self.notifications.insert_one(notification_dict)
        notification.id = str(result.inserted_id)
        
        return notification
    
    async def create_batch_notifications(self, batch_data: NotificationBatchCreate) -> List[Notification]:
        """Create multiple notifications at once"""
        notifications = []
        notification_dicts = []
        
        for notification_data in batch_data.notifications:
            notification = Notification(**notification_data.dict())
            notification_dict = notification.dict()
            notification_dict["_id"] = ObjectId()
            notification_dicts.append(notification_dict)
            notifications.append(notification)
        
        # Batch insert
        if notification_dicts:
            result = await self.notifications.insert_many(notification_dicts)
            for i, inserted_id in enumerate(result.inserted_ids):
                notifications[i].id = str(inserted_id)
        
        return notifications
    
    async def get_user_notifications(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None
    ) -> tuple[List[Notification], int]:
        """Get user notifications with pagination"""
        
        # Build query
        query = {"user_id": user_id}
        
        # Filter by read status
        if unread_only:
            query["status"] = NotificationStatus.UNREAD
        
        # Filter by type
        if notification_type:
            query["type"] = notification_type
        
        # Filter out expired notifications
        query["$or"] = [
            {"expires_at": None},
            {"expires_at": {"$gt": datetime.utcnow()}}
        ]
        
        # Get total count
        total = await self.notifications.count_documents(query)
        
        # Get notifications with pagination
        cursor = self.notifications.find(query).sort("created_at", -1).skip(skip).limit(limit)
        notifications = []
        
        async for doc in cursor:
            doc["id"] = str(doc["_id"])
            notifications.append(Notification(**doc))
        
        return notifications, total
    
    async def get_notification_by_id(self, notification_id: str, user_id: str) -> Optional[Notification]:
        """Get a specific notification"""
        try:
            doc = await self.notifications.find_one({
                "_id": ObjectId(notification_id),
                "user_id": user_id
            })
            
            if doc:
                doc["id"] = str(doc["_id"])
                return Notification(**doc)
            return None
        except:
            return None
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read"""
        result = await self.notifications.update_one(
            {
                "_id": ObjectId(notification_id),
                "user_id": user_id,
                "status": NotificationStatus.UNREAD
            },
            {
                "$set": {
                    "status": NotificationStatus.READ,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all user notifications as read"""
        result = await self.notifications.update_many(
            {
                "user_id": user_id,
                "status": NotificationStatus.UNREAD
            },
            {
                "$set": {
                    "status": NotificationStatus.READ,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count
    
    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        result = await self.notifications.delete_one({
            "_id": ObjectId(notification_id),
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    async def clear_all_notifications(self, user_id: str) -> int:
        """Clear all user notifications"""
        result = await self.notifications.delete_many({
            "user_id": user_id
        })
        
        return result.deleted_count
    
    async def get_notification_stats(self, user_id: str) -> NotificationStats:
        """Get user notification statistics"""
        stats = NotificationStats()
        
        # Get counts by status
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        async for doc in self.notifications.aggregate(pipeline):
            status = doc["_id"]
            count = doc["count"]
            
            if status == NotificationStatus.UNREAD:
                stats.unread_notifications = count
            elif status == NotificationStatus.READ:
                stats.read_notifications = count
            elif status == NotificationStatus.DISMISSED:
                stats.dismissed_notifications = count
            
            stats.total_notifications += count
        
        # Get counts by type
        type_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$type",
                "count": {"$sum": 1}
            }}
        ]
        
        async for doc in self.notifications.aggregate(type_pipeline):
            stats.by_type[doc["_id"]] = doc["count"]
        
        # Get counts by priority
        priority_pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$priority",
                "count": {"$sum": 1}
            }}
        ]
        
        async for doc in self.notifications.aggregate(priority_pipeline):
            stats.by_priority[doc["_id"]] = doc["count"]
        
        # Get recent notifications count
        week_ago = datetime.utcnow() - timedelta(days=7)
        stats.recent_notifications_7_days = await self.notifications.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": week_ago}
        })
        
        # Calculate read percentage
        if stats.total_notifications > 0:
            stats.read_percentage = round(
                (stats.read_notifications / stats.total_notifications) * 100, 2
            )
        
        # Get last notification timestamps
        last_notification = await self.notifications.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        if last_notification:
            stats.last_notification_at = last_notification.get("created_at")
        
        last_read = await self.notifications.find_one(
            {"user_id": user_id, "status": NotificationStatus.READ},
            sort=[("read_at", -1)]
        )
        if last_read:
            stats.last_read_at = last_read.get("read_at")
        
        return stats
    
    async def get_user_settings(self, user_id: str) -> NotificationSettings:
        """Get user notification settings"""
        doc = await self.notification_settings.find_one({"user_id": user_id})
        
        if doc:
            return NotificationSettings(**doc)
        
        # Return default settings if not found
        return NotificationSettings(user_id=user_id)
    
    async def update_user_settings(
        self,
        user_id: str,
        settings_update: NotificationSettingsUpdate
    ) -> NotificationSettings:
        """Update user notification settings"""
        
        # Get current settings or create new
        current_settings = await self.get_user_settings(user_id)
        
        # Update with new values
        update_data = settings_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Apply updates
        for field, value in update_data.items():
            setattr(current_settings, field, value)
        
        # Save to database
        await self.notification_settings.replace_one(
            {"user_id": user_id},
            current_settings.dict(),
            upsert=True
        )
        
        return current_settings


# API Endpoints

@router.get("/", response_model=Dict[str, Any])
async def get_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    notification_type: Optional[NotificationType] = Query(None, description="Filter by type"),
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Get user's notifications with pagination and filtering"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    
    # Calculate offset
    skip = (page - 1) * limit
    
    # Get notifications
    notifications, total = await service.get_user_notifications(
        user_id=user_id,
        skip=skip,
        limit=limit,
        unread_only=unread_only,
        notification_type=notification_type
    )
    
    # Convert to response format
    notification_responses = [
        NotificationResponse.from_notification(n) for n in notifications
    ]
    
    # Get unread count
    unread_count = await service.notifications.count_documents({
        "user_id": user_id,
        "status": NotificationStatus.UNREAD
    })
    
    # Calculate pagination info
    pages = (total + limit - 1) // limit
    
    return {
        "notifications": notification_responses,
        "pagination": {
            "page": page,
            "per_page": limit,
            "total": total,
            "pages": pages
        },
        "unread_count": unread_count
    }


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Create a new notification (internal use)"""
    
    service = NotificationService(db)
    notification = await service.create_notification(notification_data)
    
    # TODO: Add background task for email/push notification if enabled
    
    return NotificationResponse.from_notification(notification)


@router.post("/batch", response_model=List[NotificationResponse])
async def create_batch_notifications(
    batch_data: NotificationBatchCreate,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Create multiple notifications at once (internal use)"""
    
    service = NotificationService(db)
    notifications = await service.create_batch_notifications(batch_data)
    
    return [NotificationResponse.from_notification(n) for n in notifications]


@router.put("/{notification_id}/read", response_model=Dict[str, Any])
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Mark a specific notification as read"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    success = await service.mark_as_read(notification_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already read"
        )
    
    return {
        "success": True,
        "message": "Notification marked as read",
        "notification_id": notification_id
    }


@router.put("/mark-all-read", response_model=Dict[str, Any])
async def mark_all_notifications_read(
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Mark all user's notifications as read"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    updated_count = await service.mark_all_as_read(user_id)
    
    return {
        "success": True,
        "message": "All notifications marked as read",
        "updated_count": updated_count
    }


@router.delete("/{notification_id}", response_model=Dict[str, Any])
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Delete a specific notification"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    success = await service.delete_notification(notification_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return {
        "success": True,
        "message": "Notification deleted successfully",
        "notification_id": notification_id
    }


@router.delete("/", response_model=Dict[str, Any])
async def clear_all_notifications(
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Clear all user notifications"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    deleted_count = await service.clear_all_notifications(user_id)
    
    return {
        "success": True,
        "message": "All notifications cleared",
        "deleted_count": deleted_count
    }


@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings(
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Get user's notification preferences"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    settings = await service.get_user_settings(user_id)
    
    return settings


@router.put("/settings", response_model=NotificationSettings)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Update user's notification preferences"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    updated_settings = await service.update_user_settings(user_id, settings_update)
    
    return updated_settings


@router.get("/stats", response_model=NotificationStats)
async def get_notification_stats(
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Get user's notification statistics"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    stats = await service.get_notification_stats(user_id)
    
    return stats


@router.post("/test", response_model=NotificationResponse)
async def send_test_notification(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Send a test notification to verify notification system"""
    
    user_id = str(current_user["_id"])
    service = NotificationService(db)
    
    # Create test notification
    test_notification_data = NotificationCreate(
        user_id=user_id,
        type=NotificationType.SYSTEM,
        priority=NotificationPriority.NORMAL,
        title="Test Notification",
        body="This is a test notification to verify your notification settings are working properly.",
        data={"test": True}
    )
    
    notification = await service.create_notification(test_notification_data)
    
    # TODO: Send test email if email notifications are enabled
    
    return NotificationResponse.from_notification(notification)


# Helper functions for creating notifications

async def create_event_reminder(
    db: AsyncIOMotorDatabase,
    user_id: str,
    event: Dict[str, Any],
    minutes_before: int = 1440
) -> Notification:
    """Create an event reminder notification"""
    
    service = NotificationService(db)
    
    hours = minutes_before // 60
    time_text = f"{hours} hours" if hours > 1 else "1 hour"
    
    notification_data = NotificationCreate(
        user_id=user_id,
        type=NotificationType.EVENT_REMINDER,
        priority=NotificationPriority.HIGH,
        title=f"Event Reminder: {event.get('title', 'Event')}",
        body=f"Don't forget! Your event starts in {time_text} at {event.get('venue', {}).get('name', 'the venue')}.",
        action_url=f"/events/{event.get('_id')}",
        event_id=str(event.get('_id')),
        data={
            "event_title": event.get('title'),
            "event_start": event.get('start_date'),
            "venue_name": event.get('venue', {}).get('name')
        }
    )
    
    return await service.create_notification(notification_data)


async def create_new_event_notification(
    db: AsyncIOMotorDatabase,
    user_id: str,
    event: Dict[str, Any]
) -> Notification:
    """Create a new event notification"""
    
    service = NotificationService(db)
    
    notification_data = NotificationCreate(
        user_id=user_id,
        type=NotificationType.NEW_EVENT,
        priority=NotificationPriority.NORMAL,
        title="New Event Added!",
        body=f"{event.get('title')} - {event.get('category', 'Event')} at {event.get('venue', {}).get('name', 'Dubai')}",
        action_url=f"/events/{event.get('_id')}",
        event_id=str(event.get('_id')),
        data={
            "event_title": event.get('title'),
            "event_category": event.get('category'),
            "venue_name": event.get('venue', {}).get('name')
        }
    )
    
    return await service.create_notification(notification_data)