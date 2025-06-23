"""
Rate limiting utilities for API endpoint protection
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status
import asyncio


class RateLimiter:
    """Simple in-memory rate limiter using sliding window"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        
    def is_allowed(self, identifier: str) -> Tuple[bool, Dict[str, any]]:
        """
        Check if request is allowed for the given identifier
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        user_requests = self.requests[identifier]
        while user_requests and user_requests[0] < window_start:
            user_requests.popleft()
        
        # Check if limit exceeded
        current_requests = len(user_requests)
        is_allowed = current_requests < self.max_requests
        
        if is_allowed:
            user_requests.append(now)
        
        # Calculate reset time
        reset_time = int(now + self.window_seconds) if user_requests else int(now)
        
        rate_info = {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - current_requests - (1 if is_allowed else 0)),
            "reset": reset_time,
            "retry_after": None if is_allowed else self.window_seconds
        }
        
        return is_allowed, rate_info


class AsyncRateLimiter:
    """Async version of rate limiter with Redis-like interface"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
        
    async def is_allowed(self, identifier: str) -> Tuple[bool, Dict[str, any]]:
        """Async version of is_allowed"""
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Clean old requests
            user_requests = self.requests[identifier]
            while user_requests and user_requests[0] < window_start:
                user_requests.popleft()
            
            # Check if limit exceeded
            current_requests = len(user_requests)
            is_allowed = current_requests < self.max_requests
            
            if is_allowed:
                user_requests.append(now)
            
            # Calculate reset time
            reset_time = int(now + self.window_seconds) if user_requests else int(now)
            
            rate_info = {
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - current_requests - (1 if is_allowed else 0)),
                "reset": reset_time,
                "retry_after": None if is_allowed else self.window_seconds
            }
            
            return is_allowed, rate_info


# Global rate limiters for different endpoints
auth_limiter = RateLimiter(max_requests=10, window_seconds=60)  # 10 auth attempts per minute
api_limiter = RateLimiter(max_requests=1000, window_seconds=60)  # 1000 API calls per minute
search_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 searches per minute


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check for forwarded IP first (behind proxy)
    forwarded_ip = request.headers.get("X-Forwarded-For")
    if forwarded_ip:
        return forwarded_ip.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def rate_limit_dependency(limiter: RateLimiter):
    """Dependency factory for rate limiting"""
    
    def rate_limit(request: Request):
        client_ip = get_client_ip(request)
        is_allowed, rate_info = limiter.is_allowed(client_ip)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(rate_info["retry_after"])
                }
            )
        
        # Add rate limit headers to successful responses
        request.state.rate_limit_info = rate_info
        return True
    
    return rate_limit


def user_rate_limit_dependency(limiter: RateLimiter):
    """Dependency factory for user-based rate limiting"""
    
    def rate_limit(request: Request, user_id: Optional[str] = None):
        # Use user ID if available, otherwise fall back to IP
        identifier = user_id if user_id else get_client_ip(request)
        is_allowed, rate_info = limiter.is_allowed(identifier)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(rate_info["retry_after"])
                }
            )
        
        request.state.rate_limit_info = rate_info
        return True
    
    return rate_limit


# Pre-configured rate limit dependencies
auth_rate_limit = rate_limit_dependency(auth_limiter)
api_rate_limit = rate_limit_dependency(api_limiter)
search_rate_limit = rate_limit_dependency(search_limiter) 