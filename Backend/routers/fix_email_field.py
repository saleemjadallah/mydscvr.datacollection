from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from database import get_mongodb
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fix", tags=["Temporary Fix"])

@router.post("/email-verification-field")
async def fix_email_verification_field(
    email: str,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """Temporary endpoint to fix email verification field mismatch"""
    try:
        # Fix both fields to ensure compatibility
        result = await db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "is_email_verified": True,
                    "email_verified": True
                }
            }
        )
        
        if result.modified_count > 0:
            return {"success": True, "message": f"Fixed email verification for {email}"}
        else:
            # Check if user exists
            user = await db.users.find_one({"email": email})
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return {"success": True, "message": "User already has correct fields"}
            
    except Exception as e:
        logger.error(f"Error fixing email field: {e}")
        raise HTTPException(status_code=500, detail=str(e))