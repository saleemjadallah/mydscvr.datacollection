#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv('Mongo.env')

async def fix_user():
    client = AsyncIOMotorClient(os.getenv('MONGODB_URI'))
    db = client['DXB']
    
    # Fix the is_email_verified field for your user
    result = await db.users.update_one(
        {'email': 'saleem86@gmail.com'},
        {'$set': {'is_email_verified': True}}
    )
    
    print(f'Updated {result.modified_count} user(s)')
    
    # Verify the update
    user = await db.users.find_one({'email': 'saleem86@gmail.com'})
    print(f'User email: {user.get("email")}')
    print(f'User is_email_verified: {user.get("is_email_verified")}')
    print(f'User email_verified: {user.get("email_verified")}')
    
    client.close()

if __name__ == "__main__":
    asyncio.run(fix_user())