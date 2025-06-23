#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import os
from dotenv import load_dotenv
import sys

load_dotenv('Mongo.env')

async def reset_password(email: str, new_password: str):
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['DXB']
    
    # Hash the new password
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    # Update user password and ensure email is verified
    result = await db.users.update_one(
        {'email': email},
        {
            '$set': {
                'password_hash': password_hash.decode('utf-8'),
                'is_email_verified': True,
                'email_verified': True
            }
        }
    )
    
    if result.matched_count > 0:
        print(f'✅ Password reset successfully for {email}')
        print(f'✅ Email verification status also set to verified')
        print(f'📝 New password: {new_password}')
    else:
        print(f'❌ User not found: {email}')
    
    client.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_user_password.py <email> <new_password>")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    asyncio.run(reset_password(email, new_password))