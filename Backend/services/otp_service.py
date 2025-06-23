#!/usr/bin/env python3
"""
OTP Verification Service
Handles OTP generation, verification, and email sending
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.otp_models import (
    OTPCode, 
    OTPVerificationRequest, 
    OTPGenerationRequest, 
    OTPResponse,
    EmailVerificationStatus
)
from services.email_service import email_service
from database import get_mongodb

logger = logging.getLogger(__name__)


class OTPService:
    """Service for handling OTP verification operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.otp_collection = db.otp_codes
        self.users_collection = db.users
        
        # Rate limiting settings
        self.max_otps_per_hour = 5
        self.max_otps_per_day = 10
        self.cleanup_interval_hours = 1
    
    async def _cleanup_expired_otps(self):
        """Clean up expired OTP codes"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            result = await self.otp_collection.delete_many({
                "$or": [
                    {"expires_at": {"$lt": datetime.utcnow()}},
                    {"created_at": {"$lt": cutoff_time}}
                ]
            })
            if result.deleted_count > 0:
                logger.info(f"🧹 Cleaned up {result.deleted_count} expired OTP codes")
        except Exception as e:
            logger.error(f"❌ Error cleaning up OTPs: {e}")
    
    async def _check_rate_limits(self, email: str) -> Dict[str, Any]:
        """Check if email has exceeded rate limits"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Count OTPs in last hour
        hour_count = await self.otp_collection.count_documents({
            "email": email,
            "created_at": {"$gte": hour_ago}
        })
        
        # Count OTPs in last day
        day_count = await self.otp_collection.count_documents({
            "email": email,
            "created_at": {"$gte": day_ago}
        })
        
        if hour_count >= self.max_otps_per_hour:
            return {
                "allowed": False,
                "reason": "rate_limit_hour",
                "message": f"Too many OTP requests. Please wait before requesting another code.",
                "retry_after": 3600 - int((now - hour_ago).total_seconds())
            }
        
        if day_count >= self.max_otps_per_day:
            return {
                "allowed": False,
                "reason": "rate_limit_day",
                "message": f"Daily OTP limit reached. Please try again tomorrow.",
                "retry_after": 86400 - int((now - day_ago).total_seconds())
            }
        
        return {"allowed": True}
    
    async def generate_and_send_otp(
        self,
        request: OTPGenerationRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OTPResponse:
        """
        Generate new OTP and send via email
        """
        try:
            # Clean up expired OTPs first
            await self._cleanup_expired_otps()
            
            # Check rate limits
            rate_check = await self._check_rate_limits(request.email)
            if not rate_check["allowed"]:
                return OTPResponse(
                    success=False,
                    message=rate_check["message"],
                    details={"reason": rate_check["reason"], "retry_after": rate_check.get("retry_after")}
                )
            
            # Invalidate any existing OTPs for this email and purpose
            await self.otp_collection.update_many(
                {
                    "email": request.email,
                    "purpose": request.purpose,
                    "verified": False
                },
                {"$set": {"verified": True, "verified_at": datetime.utcnow()}}
            )
            
            # Create new OTP
            otp_instance = OTPCode.create_new_otp(
                email=request.email,
                user_name=request.user_name,
                purpose=request.purpose,
                expires_in_minutes=10,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Store in database
            await self.otp_collection.insert_one(otp_instance.to_dict())
            
            # Send email based on purpose
            if request.purpose == "password_reset":
                email_result = await email_service.send_password_reset_email(
                    recipient_email=request.email,
                    recipient_name=request.user_name,
                    reset_code=otp_instance.otp_code,
                    expires_in_minutes=15
                )
            else:
                email_result = await email_service.send_otp_email(
                    recipient_email=request.email,
                    recipient_name=request.user_name,
                    otp_code=otp_instance.otp_code,
                    expires_in_minutes=10
                )
            
            if not email_result["success"]:
                logger.error(f"❌ Failed to send OTP email: {email_result}")
                return OTPResponse(
                    success=False,
                    message="Failed to send verification email. Please try again.",
                    details=email_result
                )
            
            logger.info(f"✅ OTP generated and sent to {request.email}")
            
            return OTPResponse(
                success=True,
                message="Verification code sent to your email",
                expires_at=otp_instance.expires_at,
                details={
                    "email_sent": True,
                    "expires_in_minutes": 10
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error generating OTP: {e}")
            return OTPResponse(
                success=False,
                message="Failed to generate verification code. Please try again.",
                details={"error": str(e)}
            )
    
    async def verify_otp(
        self,
        request: OTPVerificationRequest,
        ip_address: Optional[str] = None
    ) -> OTPResponse:
        """
        Verify OTP code
        """
        try:
            # Find the OTP
            otp_doc = await self.otp_collection.find_one({
                "email": request.email,
                "purpose": request.purpose,
                "verified": False
            })
            
            if not otp_doc:
                return OTPResponse(
                    success=False,
                    message="No valid verification code found. Please request a new one.",
                    details={"reason": "not_found"}
                )
            
            # Convert ObjectId to string for the model
            if "_id" in otp_doc:
                otp_doc["_id"] = str(otp_doc["_id"])
            otp_instance = OTPCode(**otp_doc)
            
            # Check if expired
            if otp_instance.is_expired():
                await self.otp_collection.update_one(
                    {"_id": otp_doc["_id"]},
                    {"$set": {"verified": True, "verified_at": datetime.utcnow()}}
                )
                return OTPResponse(
                    success=False,
                    message="Verification code has expired. Please request a new one.",
                    details={"reason": "expired"}
                )
            
            # Check if max attempts exceeded
            if otp_instance.is_attempts_exceeded():
                await self.otp_collection.update_one(
                    {"_id": otp_doc["_id"]},
                    {"$set": {"verified": True, "verified_at": datetime.utcnow()}}
                )
                return OTPResponse(
                    success=False,
                    message="Too many incorrect attempts. Please request a new verification code.",
                    details={"reason": "max_attempts"}
                )
            
            # Increment attempts
            await self.otp_collection.update_one(
                {"_id": otp_doc["_id"]},
                {"$inc": {"attempts": 1}}
            )
            
            # Verify code
            if otp_instance.otp_code != request.otp_code:
                attempts_remaining = max(0, otp_instance.max_attempts - otp_instance.attempts - 1)
                return OTPResponse(
                    success=False,
                    message=f"Incorrect verification code. {attempts_remaining} attempts remaining.",
                    attempts_remaining=attempts_remaining,
                    details={"reason": "incorrect_code"}
                )
            
            # Success! Mark as verified
            await self.otp_collection.update_one(
                {"_id": otp_doc["_id"]},
                {
                    "$set": {
                        "verified": True,
                        "verified_at": datetime.utcnow()
                    }
                }
            )
            
            # Update user verification status if this is email verification
            if request.purpose == "email_verification":
                await self.users_collection.update_one(
                    {"email": request.email},
                    {
                        "$set": {
                            "email_verified": True,
                            "email_verified_at": datetime.utcnow()
                        }
                    },
                    upsert=True
                )
                
                # Send welcome email
                try:
                    await email_service.send_welcome_email(
                        recipient_email=request.email,
                        recipient_name=otp_instance.user_name
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to send welcome email: {e}")
            
            logger.info(f"✅ OTP verified successfully for {request.email}")
            
            return OTPResponse(
                success=True,
                message="Email verified successfully! Welcome to MyDSCVR!",
                details={
                    "verified_at": datetime.utcnow().isoformat(),
                    "purpose": request.purpose
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error verifying OTP: {e}")
            return OTPResponse(
                success=False,
                message="Failed to verify code. Please try again.",
                details={"error": str(e)}
            )
    
    async def get_email_verification_status(self, email: str) -> EmailVerificationStatus:
        """
        Get email verification status
        """
        try:
            # Check user verification status
            user_doc = await self.users_collection.find_one({"email": email})
            
            # Get latest OTP info
            latest_otp = await self.otp_collection.find_one(
                {"email": email, "purpose": "email_verification"},
                sort=[("created_at", -1)]
            )
            
            total_attempts = await self.otp_collection.count_documents({
                "email": email,
                "purpose": "email_verification"
            })
            
            return EmailVerificationStatus(
                email=email,
                verified=user_doc.get("email_verified", False) if user_doc else False,
                verified_at=user_doc.get("email_verified_at") if user_doc else None,
                last_otp_sent=latest_otp.get("created_at") if latest_otp else None,
                total_attempts=total_attempts
            )
            
        except Exception as e:
            logger.error(f"❌ Error getting verification status: {e}")
            return EmailVerificationStatus(
                email=email,
                verified=False,
                total_attempts=0
            )
    
    async def resend_otp(
        self,
        email: str,
        user_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> OTPResponse:
        """
        Resend OTP (convenience method)
        """
        request = OTPGenerationRequest(
            email=email,
            user_name=user_name,
            purpose="email_verification"
        )
        
        return await self.generate_and_send_otp(
            request=request,
            ip_address=ip_address,
            user_agent=user_agent
        )


# Helper function to get OTP service instance
async def get_otp_service() -> OTPService:
    """Get OTP service instance with database connection"""
    db = await get_mongodb()
    return OTPService(db)