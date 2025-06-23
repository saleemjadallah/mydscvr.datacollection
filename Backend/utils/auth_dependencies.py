"""
Consolidated Authentication Dependencies
Standardized auth dependencies for consistent use across all routers
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Dict, Any, Optional
import logging

from database import get_mongodb
from services.mongodb_auth import MongoAuthService
from models.user_models import UserModel

logger = logging.getLogger(__name__)

# Security scheme for JWT token extraction
security = HTTPBearer()


# Core auth service dependency
async def get_auth_service(db: AsyncIOMotorDatabase = Depends(get_mongodb)) -> MongoAuthService:
    """Get MongoDB auth service instance"""
    return MongoAuthService(db)


# Standard authentication dependency (returns dict for backward compatibility)
async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: MongoAuthService = Depends(get_auth_service),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token
    Returns: dict with user data for backward compatibility
    """
    try:
        token = credentials.credentials
        logger.info(f"🔍 Verifying token for request...")
        user_id = auth_service._verify_access_token(token)
        
        if not user_id:
            logger.error(f"❌ Token verification failed - no user_id extracted")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.info(f"✅ Token verified, user_id: {user_id}")
        
        # Try to find user with ObjectId first (standard format)
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            logger.warning(f"⚠️ User not found with ObjectId({user_id}), trying string format...")
            # Try with string ID (some users have string IDs in the database)
            user = await db.users.find_one({"_id": user_id})
            if not user:
                logger.error(f"❌ User not found with either ObjectId or string format: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            else:
                logger.info(f"✅ User found with string ID format")
        else:
            logger.info(f"✅ User found with ObjectId format")
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Ensure _id is converted to string for JSON serialization
        if isinstance(user.get("_id"), ObjectId):
            user["_id"] = str(user["_id"])
        user["id"] = user["_id"]  # Add id field for compatibility
        
        logger.info(f"✅ User authenticated successfully: {user.get('email', 'unknown')}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Verified user dependency (returns UserModel for type safety)
async def get_current_verified_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: MongoAuthService = Depends(get_auth_service)
) -> UserModel:
    """
    Get current authenticated and email-verified user
    Returns: UserModel for type safety
    """
    try:
        user = await auth_service.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email verification required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Verified user authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Optional authentication dependency (for endpoints that work with/without auth)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    auth_service: MongoAuthService = Depends(get_auth_service),
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
) -> Optional[Dict[str, Any]]:
    """
    Get current user if authenticated, None if not
    Useful for endpoints that enhance functionality when authenticated
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user_dependency(credentials, auth_service, db)
    except HTTPException:
        return None


# User ID extraction dependency (for simple use cases)
async def get_current_user_id(
    current_user: Dict[str, Any] = Depends(get_current_user_dependency)
) -> str:
    """
    Extract user ID from authenticated user
    Returns: string user ID
    """
    return current_user["_id"]


# Admin user dependency (for admin-only endpoints)
async def get_current_admin_user(
    current_user: UserModel = Depends(get_current_verified_user)
) -> UserModel:
    """
    Get current authenticated admin user
    Returns: UserModel for admin users only
    """
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# Superuser dependency (for superuser-only endpoints)
async def get_current_superuser(
    current_user: UserModel = Depends(get_current_verified_user)
) -> UserModel:
    """
    Get current authenticated superuser
    Returns: UserModel for superusers only
    """
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )
    
    return current_user


# Convenience aliases for backward compatibility
get_current_user = get_current_user_dependency  # Alias for existing code
get_authenticated_user = get_current_user_dependency  # Alternative name