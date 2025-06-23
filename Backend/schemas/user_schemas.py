from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgeGroupSchema(str, Enum):
    """Age group schema for API"""
    TODDLER = "toddler"
    PRESCHOOL = "preschool" 
    SCHOOL = "school"
    TEEN = "teen"
    ADULT = "adult"


class FamilyMemberSchema(BaseModel):
    """Family member schema for API requests"""
    name: str = Field(..., min_length=1, max_length=100, description="Family member name")
    age: int = Field(..., ge=0, le=120, description="Age in years")
    age_group: Optional[AgeGroupSchema] = Field(None, description="Auto-calculated age group")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    interests: List[str] = Field(default_factory=list, description="List of interests")
    dietary_restrictions: List[str] = Field(default_factory=list, description="Dietary restrictions")
    accessibility_needs: List[str] = Field(default_factory=list, description="Accessibility requirements")


class OnboardingPreferencesSchema(BaseModel):
    """Onboarding preferences schema for API"""
    # Step 3: Interests
    interests: List[str] = Field(default_factory=list, description="Selected interests")
    
    # Step 4: Location preferences  
    preferred_areas: List[str] = Field(default_factory=list, description="Preferred Dubai areas")
    max_travel_distance: Optional[int] = Field(default=30, ge=1, le=100, description="Max travel distance in KM")
    
    # Step 5: Budget preferences
    budget_min: Optional[float] = Field(default=0, ge=0, description="Minimum budget")
    budget_max: Optional[float] = Field(default=1000, ge=0, description="Maximum budget")
    currency: str = Field(default="AED", description="Currency code")
    
    # Step 5: Schedule preferences
    preferred_days: List[str] = Field(default_factory=list, description="Preferred days of week")
    preferred_times: List[str] = Field(default_factory=list, description="Preferred times of day")
    
    # Additional preferences
    language_preferences: List[str] = Field(default=["English"], description="Language preferences")
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email_notifications": True,
            "push_notifications": True,
            "sms_notifications": False,
            "weekly_digest": True,
            "event_reminders": True,
            "last_minute_deals": True,
            "new_events_in_area": True
        },
        description="Notification preferences"
    )


# Request schemas
class UserRegistrationRequest(BaseModel):
    """User registration request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$', description="Phone number")


class UserLoginRequest(BaseModel):
    """User login request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserUpdateRequest(BaseModel):
    """User profile update request schema"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$', description="Phone number")
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    avatar: Optional[str] = Field(None, description="Avatar URL")
    privacy_settings: Optional[Dict[str, bool]] = Field(None, description="Privacy settings")


class OnboardingCompletionRequest(BaseModel):
    """Onboarding completion request schema"""
    family_members: List[FamilyMemberSchema] = Field(..., description="Family members from Step 2")
    preferences: OnboardingPreferencesSchema = Field(..., description="User preferences from Steps 3-5")


class PasswordChangeRequest(BaseModel):
    """Password change request schema"""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


# Response schemas
class UserProfileResponse(BaseModel):
    """User profile response schema"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar: Optional[str] = Field(None, description="Avatar URL")
    phone_number: Optional[str] = Field(None, description="Phone number")
    date_of_birth: Optional[str] = Field(None, description="Date of birth (ISO format)")
    onboarding_completed: bool = Field(..., description="Whether onboarding is completed")
    family_members: List[FamilyMemberSchema] = Field(default_factory=list, description="Family members")
    preferences: OnboardingPreferencesSchema = Field(..., description="User preferences")
    privacy_settings: Dict[str, bool] = Field(..., description="Privacy settings")
    subscription_type: str = Field(..., description="Subscription type")
    is_email_verified: bool = Field(..., description="Email verification status")
    is_phone_verified: bool = Field(..., description="Phone verification status")
    created_at: str = Field(..., description="Account creation date (ISO format)")
    updated_at: str = Field(..., description="Last update date (ISO format)")


class AuthResponse(BaseModel):
    """Authentication response schema"""
    access_token: str = Field(..., description="JWT access token")
    session_token: str = Field(..., description="Session token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserProfileResponse = Field(..., description="User profile data")


class UserRegistrationResponse(BaseModel):
    """User registration response schema"""
    success: bool = Field(..., description="Registration success status")
    message: str = Field(..., description="Response message")
    user: Optional[UserProfileResponse] = Field(None, description="User profile data")


class MessageResponse(BaseModel):
    """Generic message response schema"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Response message")


class UserStatsResponse(BaseModel):
    """User statistics response schema"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    verified_users: int = Field(..., description="Number of verified users")
    onboarded_users: int = Field(..., description="Number of users who completed onboarding")
    verification_rate: float = Field(..., description="Email verification rate")
    onboarding_completion_rate: float = Field(..., description="Onboarding completion rate")


# Validation schemas
class OnboardingValidationSchema(BaseModel):
    """Schema for validating onboarding data"""
    step: int = Field(..., ge=1, le=6, description="Onboarding step number")
    data: Dict[str, Any] = Field(..., description="Step data")
    
    @validator('data')
    def validate_step_data(cls, v, values):
        step = values.get('step')
        if step == 1:  # Welcome step
            return v  # No specific validation needed
        elif step == 2:  # Family setup
            if 'family_members' not in v:
                raise ValueError("family_members required for step 2")
            if not isinstance(v['family_members'], list):
                raise ValueError("family_members must be a list")
        elif step == 3:  # Interests
            if 'interests' not in v:
                raise ValueError("interests required for step 3")
            if not isinstance(v['interests'], list) or len(v['interests']) < 3:
                raise ValueError("At least 3 interests required")
        elif step == 4:  # Location
            if 'preferred_areas' not in v:
                raise ValueError("preferred_areas required for step 4")
        elif step == 5:  # Budget & Schedule
            if 'budget_max' not in v or 'preferred_days' not in v:
                raise ValueError("budget_max and preferred_days required for step 5")
        elif step == 6:  # Completion
            return v  # Completion step data varies
        return v


# Error response schemas
class ValidationErrorResponse(BaseModel):
    """Validation error response schema"""
    success: bool = Field(default=False, description="Always false for errors")
    message: str = Field(..., description="Error message")
    errors: List[Dict[str, Any]] = Field(..., description="Detailed validation errors")


class AuthErrorResponse(BaseModel):
    """Authentication error response schema"""
    success: bool = Field(default=False, description="Always false for errors")
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Specific error code")