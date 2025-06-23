#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from Backend.env
load_dotenv('Backend.env')

# Connect to MongoDB using environment variables
mongodb_url = os.getenv('MONGODB_URL', 'mongodb+srv://support:olaabdel88@dxb.tq60png.mongodb.net/?retryWrites=true&w=majority&appName=DXB&tls=true&tlsAllowInvalidCertificates=true')
client = MongoClient(mongodb_url)
db = client[os.getenv('MONGODB_DATABASE', 'DXB')]

# Update user
result = db.users.update_one(
    {'email': 'support@allstarsnews.ai'},
    {'$set': {'is_email_verified': True}}
)

print(f'Updated {result.modified_count} user(s)')

# Verify update
user = db.users.find_one({'email': 'support@allstarsnews.ai'})
print(f'User: {user.get("email")}')
print(f'Email verified: {user.get("is_email_verified", False)}')
print(f'Onboarding completed: {user.get("onboarding_completed", False)}')