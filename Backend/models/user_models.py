from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from bson import ObjectId
import bcrypt
from enum import Enum


def validate_object_id(v: Union[str, ObjectId]) -> str:
    """Validate and convert ObjectId to string"""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str):
        if ObjectId.is_valid(v):
            return v
        else:
            raise ValueError("Invalid ObjectId format")
    raise ValueError("Invalid ObjectId type")


class AgeGroup(str, Enum):
    """Age group enumeration"""
    TODDLER = "toddler"  # 0-3
    PRESCHOOL = "preschool"  # 4-5
    SCHOOL = "school"  # 6-12
    TEEN = "teen"  # 13-17
    ADULT = "adult"  # 18+


class FamilyMemberModel(BaseModel):
    """Family member model for onboarding"""
    id: str = Field(default_factory=lambda: str(ObjectId()))
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=120)
    age_group: AgeGroup
    avatar_url: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    dietary_restrictions: List[str] = Field(default_factory=list)
    accessibility_needs: List[str] = Field(default_factory=list)

    @validator('age_group', pre=True, always=True)
    def set_age_group(cls, v, values):
        if 'age' in values:
            age = values['age']
            if age <= 3:
                return AgeGroup.TODDLER
            elif age <= 5:
                return AgeGroup.PRESCHOOL
            elif age <= 12:
                return AgeGroup.SCHOOL
            elif age <= 17:
                return AgeGroup.TEEN
            else:
                return AgeGroup.ADULT
        return v or AgeGroup.ADULT


class OnboardingPreferences(BaseModel):
    """User preferences from onboarding flow"""
    # Interests (Step 3)
    interests: List[str] = Field(default_factory=list)
    
    # Location preferences (Step 4)
    preferred_areas: List[str] = Field(default_factory=list)
    max_travel_distance: Optional[int] = Field(default=30, description="Max distance in KM")
    
    # Budget preferences (Step 5)
    budget_min: Optional[float] = Field(default=0, ge=0)
    budget_max: Optional[float] = Field(default=1000, ge=0)
    currency: str = Field(default="AED")
    
    # Schedule preferences (Step 5)
    preferred_days: List[str] = Field(default_factory=list)  # ['monday', 'tuesday', etc.]
    preferred_times: List[str] = Field(default_factory=list)  # ['morning', 'afternoon', 'evening']
    
    # Additional preferences
    language_preferences: List[str] = Field(default=["English"])
    notification_preferences: Dict[str, bool] = Field(default_factory=lambda: {
        "email_notifications": True,
        "push_notifications": True,
        "sms_notifications": False,
        "weekly_digest": True,
        "event_reminders": True,
        "last_minute_deals": True,
        "new_events_in_area": True
    })


class UserModel(BaseModel):
    """Main user model for MongoDB storage"""
    id: Optional[str] = Field(default=None, alias="_id")
    
    # Authentication
    email: EmailStr = Field(..., description="User email address")
    password_hash: Optional[str] = Field(None, description="Hashed password (not required for OAuth users)")
    
    # OAuth authentication
    google_id: Optional[str] = Field(None, description="Google OAuth user ID")
    auth_provider: str = Field(default="email", description="Authentication provider: email, google, or both")
    
    # Profile information
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    avatar: Optional[str] = Field(None, description="Avatar URL")
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    date_of_birth: Optional[datetime] = None
    
    # Onboarding status
    onboarding_completed: bool = Field(default=False)
    onboarding_completed_at: Optional[datetime] = None
    
    # Family information (from onboarding Step 2)
    family_members: List[FamilyMemberModel] = Field(default_factory=list)
    
    # User preferences (from onboarding Steps 3-5)
    preferences: OnboardingPreferences = Field(default_factory=OnboardingPreferences)
    
    # Account settings
    is_email_verified: bool = Field(default=False)
    is_phone_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    email_verified: bool = Field(default=False)  # Alternative name for compatibility
    
    # Privacy settings
    privacy_settings: Dict[str, bool] = Field(default_factory=lambda: {
        "profile_visible": True,
        "show_activity": True,
        "allow_friend_requests": True,
        "share_attendance": False
    })
    
    # Event-related data
    saved_events: List[str] = Field(default_factory=list)  # Event IDs
    hearted_events: List[str] = Field(default_factory=list)  # Event IDs - NEW!
    attended_events: List[str] = Field(default_factory=list)  # Event IDs
    event_ratings: Dict[str, float] = Field(default_factory=dict)  # Event ID -> Rating (1-5)
    event_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Event interaction timestamps for analytics
    event_interactions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # Event ID -> interaction data
    
    # Subscription and notifications
    subscription_type: str = Field(default="free")  # free, premium, family
    subscription_expires_at: Optional[datetime] = None
    
    # Location data
    current_location: Optional[Dict[str, float]] = None  # {"lat": 25.2048, "lng": 55.2708}
    home_location: Optional[Dict[str, float]] = None
    
    # Analytics and engagement
    last_login_at: Optional[datetime] = None
    login_count: int = Field(default=0)
    app_usage_stats: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('id', pre=True, always=True)
    def validate_id(cls, v):
        if v is None:
            return str(ObjectId())
        return validate_object_id(v)
    
    @validator('display_name', pre=True, always=True)
    def set_display_name(cls, v, values):
        if v:
            return v
        first = values.get('first_name', '')
        last = values.get('last_name', '')
        if first and last:
            return f"{first} {last}"
        elif first:
            return first
        elif 'email' in values:
            return values['email'].split('@')[0]
        return None
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash"""
        if not self.password_hash:
            return False  # OAuth users don't have passwords
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_profile_dict(self) -> Dict[str, Any]:
        """Convert to profile dictionary for frontend"""
        return {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "avatar": self.avatar,
            "phone_number": self.phone_number,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "onboarding_completed": self.onboarding_completed,
            "family_members": [member.dict() for member in self.family_members],
            "preferences": self.preferences.dict(),
            "privacy_settings": self.privacy_settings,
            "subscription_type": self.subscription_type,
            "is_email_verified": self.is_email_verified,
            "is_phone_verified": self.is_phone_verified,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str, datetime: str}
    }


class UserRegistrationModel(BaseModel):
    """Model for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')


class UserLoginModel(BaseModel):
    """Model for user login"""
    email: EmailStr
    password: str


class GoogleUserModel(BaseModel):
    """Model for Google OAuth user creation"""
    email: EmailStr
    name: Optional[str] = None
    google_id: str


class UserUpdateModel(BaseModel):
    """Model for updating user profile"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    date_of_birth: Optional[datetime] = None
    avatar: Optional[str] = None
    privacy_settings: Optional[Dict[str, bool]] = None


class OnboardingCompletionModel(BaseModel):
    """Model for completing onboarding flow"""
    family_members: List[FamilyMemberModel]
    preferences: OnboardingPreferences


class UserSessionModel(BaseModel):
    """Model for user session data"""
    user_id: str
    session_token: str
    expires_at: datetime
    device_info: Optional[Dict[str, str]] = None
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('user_id', pre=True, always=True)
    def validate_user_id(cls, v):
        return validate_object_id(v)


# Type aliases for easier imports
User = UserModel
FamilyMember = FamilyMemberModel
UserRegistration = UserRegistrationModel
UserLogin = UserLoginModel
UserUpdate = UserUpdateModel
OnboardingCompletion = OnboardingCompletionModel
UserSession = UserSessionModel