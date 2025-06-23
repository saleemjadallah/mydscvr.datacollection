#!/usr/bin/env python3
"""
OTP Verification API Router
Handles OTP generation, verification, and email confirmation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging
from typing import Optional

from models.otp_models import (
    OTPGenerationRequest,
    OTPVerificationRequest, 
    OTPResponse,
    EmailVerificationStatus
)
from services.otp_service import OTPService
from database import get_mongodb

router = APIRouter(prefix="/auth", tags=["otp-verification"])
logger = logging.getLogger(__name__)


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Extract client IP and user agent from request"""
    # Get client IP (handle proxies)
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.headers.get("X-Real-IP") or request.client.host
    
    user_agent = request.headers.get("User-Agent")
    
    return client_ip, user_agent


@router.post("/send-verification-code", response_model=OTPResponse)
async def send_verification_code(
    request: OTPGenerationRequest,
    http_request: Request,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Generate and send OTP verification code to email
    """
    try:
        client_ip, user_agent = get_client_info(http_request)
        
        otp_service = OTPService(db)
        result = await otp_service.generate_and_send_otp(
            request=request,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not result.success:
            # Return appropriate HTTP status based on error type
            if result.details and result.details.get("reason") in ["rate_limit_hour", "rate_limit_day"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in send_verification_code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code"
        )


@router.post("/verify-email", response_model=OTPResponse)
async def verify_email(
    request: OTPVerificationRequest,
    http_request: Request,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Verify OTP code for email confirmation
    """
    try:
        client_ip, user_agent = get_client_info(http_request)
        
        otp_service = OTPService(db)
        result = await otp_service.verify_otp(
            request=request,
            ip_address=client_ip
        )
        
        if not result.success:
            # Return 400 for verification failures
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.message
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in verify_email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email"
        )


@router.post("/resend-verification-code", response_model=OTPResponse)
async def resend_verification_code(
    email: str,
    user_name: str,
    http_request: Request,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Resend OTP verification code
    """
    try:
        client_ip, user_agent = get_client_info(http_request)
        
        otp_service = OTPService(db)
        result = await otp_service.resend_otp(
            email=email,
            user_name=user_name,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        if not result.success:
            if result.details and result.details.get("reason") in ["rate_limit_hour", "rate_limit_day"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.message
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in resend_verification_code: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification code"
        )


@router.get("/email-verification-status/{email}", response_model=EmailVerificationStatus)
async def get_email_verification_status(
    email: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get email verification status
    """
    try:
        otp_service = OTPService(db)
        status_info = await otp_service.get_email_verification_status(email)
        
        return status_info
        
    except Exception as e:
        logger.error(f"❌ Error getting verification status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get verification status"
        )


@router.post("/test-email")
async def test_email_service(
    recipient_email: str,
    recipient_name: str = "Test User"
):
    """
    Test endpoint for email service (development only)
    """
    try:
        from services.email_service import email_service
        
        # Send test OTP email
        result = await email_service.send_otp_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            otp_code="123456",
            expires_in_minutes=10
        )
        
        return {
            "success": result["success"],
            "message": "Test email sent" if result["success"] else "Failed to send test email",
            "details": result
        }
        
    except Exception as e:
        logger.error(f"❌ Error sending test email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test email: {str(e)}"
        )


@router.post("/test-welcome-email")
async def test_welcome_email(
    recipient_email: str,
    recipient_name: str = "Test User"
):
    """
    Test endpoint for welcome email (development only)
    """
    try:
        from services.email_service import email_service
        
        # Send test welcome email
        result = await email_service.send_welcome_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name
        )
        
        return {
            "success": result["success"],
            "message": "Test welcome email sent" if result["success"] else "Failed to send test welcome email",
            "details": result
        }
        
    except Exception as e:
        logger.error(f"❌ Error sending test welcome email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test welcome email: {str(e)}"
        )