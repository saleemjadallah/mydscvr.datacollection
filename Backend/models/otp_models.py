#!/usr/bin/env python3
"""
OTP Verification Models
Database models for OTP verification system
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId
import secrets
import string


class OTPCode(BaseModel):
    """
    OTP Code model for database storage
    """
    id: Optional[str] = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    email: EmailStr
    otp_code: str
    user_name: str
    purpose: str = "email_verification"  # email_verification, password_reset, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    verified: bool = False
    verified_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 5
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    
    @classmethod
    def generate_otp(cls, length: int = 6) -> str:
        """Generate a random OTP code"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @classmethod
    def create_new_otp(
        cls,
        email: str,
        user_name: str,
        purpose: str = "email_verification",
        expires_in_minutes: int = 10,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> "OTPCode":
        """Create a new OTP instance"""
        otp_code = cls.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        
        return cls(
            email=email,
            otp_code=otp_code,
            user_name=user_name,
            purpose=purpose,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def is_expired(self) -> bool:
        """Check if OTP has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_attempts_exceeded(self) -> bool:
        """Check if max attempts exceeded"""
        return self.attempts >= self.max_attempts
    
    def increment_attempts(self) -> None:
        """Increment attempt counter"""
        self.attempts += 1
    
    def verify(self) -> None:
        """Mark OTP as verified"""
        self.verified = True
        self.verified_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        data = self.dict(by_alias=True)
        if "_id" in data and isinstance(data["_id"], str):
            data["_id"] = ObjectId(data["_id"])
        return data


class OTPVerificationRequest(BaseModel):
    """Request model for OTP verification"""
    email: EmailStr
    otp_code: str
    purpose: str = "email_verification"


class OTPGenerationRequest(BaseModel):
    """Request model for OTP generation"""
    email: EmailStr
    user_name: str
    purpose: str = "email_verification"


class OTPResponse(BaseModel):
    """Response model for OTP operations"""
    success: bool
    message: str
    expires_at: Optional[datetime] = None
    attempts_remaining: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class EmailVerificationStatus(BaseModel):
    """Model for email verification status"""
    email: EmailStr
    verified: bool
    verified_at: Optional[datetime] = None
    last_otp_sent: Optional[datetime] = None
    total_attempts: int = 0


class OTPStats(BaseModel):
    """OTP statistics model"""
    total_generated: int
    total_verified: int
    total_expired: int
    total_failed_attempts: int
    success_rate: float
    average_verification_time: Optional[float] = None  # in seconds