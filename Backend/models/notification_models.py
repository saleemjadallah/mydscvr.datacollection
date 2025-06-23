"""
Notification models for MongoDB
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId


class NotificationType(str, Enum):
    """Types of notifications"""
    EVENT_REMINDER = "event_reminder"
    NEW_EVENT = "new_event"
    EVENT_UPDATE = "event_update"
    BOOKING_CONFIRMATION = "booking_confirmation"
    EVENT_CANCELLATION = "event_cancellation"
    SOCIAL_ACTIVITY = "social_activity"
    PROMOTIONAL_OFFER = "promotional_offer"
    SYSTEM = "system"
    ACHIEVEMENT = "achievement"
    WEEKLY_DIGEST = "weekly_digest"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification status"""
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"


class NotificationBase(BaseModel):
    """Base notification model"""
    user_id: str
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    
    title: str
    body: str
    action_url: Optional[str] = None
    
    # Metadata
    event_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    # Status
    status: NotificationStatus = NotificationStatus.UNREAD
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Delivery status
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class Notification(NotificationBase):
    """Notification model for database"""
    id: Optional[str] = Field(alias="_id", default=None)
    
    class Config:
        allow_population_by_field_name = True


class NotificationCreate(BaseModel):
    """Create notification request"""
    user_id: str
    type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    title: str
    body: str
    action_url: Optional[str] = None
    
    event_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    expires_at: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    """Update notification request"""
    status: Optional[NotificationStatus] = None
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None


class NotificationResponse(BaseModel):
    """Notification response model"""
    id: str
    user_id: str
    type: NotificationType
    priority: NotificationPriority
    
    title: str
    body: str
    action_url: Optional[str] = None
    
    event_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    status: NotificationStatus
    read_at: Optional[datetime] = None
    
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    delivered: bool
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def from_notification(cls, notification: Notification) -> "NotificationResponse":
        """Create response from notification model"""
        return cls(
            id=str(notification.id),
            user_id=notification.user_id,
            type=notification.type,
            priority=notification.priority,
            title=notification.title,
            body=notification.body,
            action_url=notification.action_url,
            event_id=notification.event_id,
            data=notification.data,
            status=notification.status,
            read_at=notification.read_at,
            created_at=notification.created_at,
            expires_at=notification.expires_at,
            delivered=notification.delivered
        )


class NotificationSettings(BaseModel):
    """User notification preferences"""
    user_id: str
    
    # Channel preferences
    push_notifications: bool = True
    email_notifications: bool = True
    in_app_notifications: bool = True
    
    # Type preferences
    event_reminders: bool = True
    new_events: bool = True
    event_updates: bool = True
    social_activity: bool = True
    promotional_offers: bool = False
    weekly_digest: bool = True
    
    # Timing preferences
    reminder_minutes: int = 1440  # 24 hours before event
    quiet_hours: bool = False
    quiet_start_hour: int = 22  # 10 PM
    quiet_end_hour: int = 8  # 8 AM
    
    # Muted categories
    muted_event_types: List[str] = Field(default_factory=list)
    muted_users: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationSettingsUpdate(BaseModel):
    """Update notification settings request"""
    push_notifications: Optional[bool] = None
    email_notifications: Optional[bool] = None
    in_app_notifications: Optional[bool] = None
    
    event_reminders: Optional[bool] = None
    new_events: Optional[bool] = None
    event_updates: Optional[bool] = None
    social_activity: Optional[bool] = None
    promotional_offers: Optional[bool] = None
    weekly_digest: Optional[bool] = None
    
    reminder_minutes: Optional[int] = None
    quiet_hours: Optional[bool] = None
    quiet_start_hour: Optional[int] = None
    quiet_end_hour: Optional[int] = None
    
    muted_event_types: Optional[List[str]] = None
    muted_users: Optional[List[str]] = None


class NotificationBatchCreate(BaseModel):
    """Create multiple notifications at once"""
    notifications: List[NotificationCreate]
    
    
class NotificationStats(BaseModel):
    """Notification statistics"""
    total_notifications: int = 0
    unread_notifications: int = 0
    read_notifications: int = 0
    dismissed_notifications: int = 0
    
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_priority: Dict[str, int] = Field(default_factory=dict)
    
    recent_notifications_7_days: int = 0
    read_percentage: float = 0.0
    
    last_notification_at: Optional[datetime] = None
    last_read_at: Optional[datetime] = None