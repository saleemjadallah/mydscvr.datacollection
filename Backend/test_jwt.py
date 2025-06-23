#!/usr/bin/env python3

import sys
import os
sys.path.append('/Users/saleemjadallah/Desktop/DXB-events/Backend')

from utils.jwt_config import JWTConfig
from config import settings

# Test token from the frontend error
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ODUwMzlkNDczMjc4Mjg5ZmQwOTUwNmIiLCJpYXQiOjE3NTAyMzI5MzksInR5cGUiOiJhY2Nlc3MiLCJleHAiOjE3NTA4Mzc3Mzl9.sKd9WrMaLNk42tRBD55xgxoNXUkq-6Z1ifmh8Fsq97Q"

print("Testing JWT Token Verification")
print("="*50)
print(f"JWT Secret: {settings.JWT_SECRET}")
print(f"JWT Algorithm: {settings.algorithm}")
print()

# Test with JWTConfig
print("Testing with JWTConfig.verify_token:")
payload = JWTConfig.verify_token(token)
print(f"Payload: {payload}")
print()

print("Testing with JWTConfig.get_user_id_from_token:")
user_id = JWTConfig.get_user_id_from_token(token)
print(f"User ID: {user_id}")
print()

# Test direct jwt decoding
import jwt
try:
    print("Testing direct jwt.decode:")
    direct_payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.algorithm])
    print(f"Direct decode success: {direct_payload}")
except Exception as e:
    print(f"Direct decode error: {e}")