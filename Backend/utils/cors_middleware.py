"""
CORS Middleware Utilities
Permanent CORS configuration for critical endpoints like hidden gems
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List
import logging

logger = logging.getLogger(__name__)


class PermanentCORSMiddleware(BaseHTTPMiddleware):
    """
    Permanent CORS middleware that ensures critical endpoints always have CORS enabled
    This middleware specifically protects against configuration changes affecting CORS
    """
    
    def __init__(
        self, 
        app,
        critical_paths: List[str] = None,
        allowed_origins: List[str] = None
    ):
        super().__init__(app)
        # Critical paths that MUST always have CORS enabled
        self.critical_paths = critical_paths or [
            "/api/hidden-gems",
            "/api/events", 
            "/api/notifications"
        ]
        
        # Production origins that MUST always be allowed
        self.allowed_origins = allowed_origins or [
            "https://mydscvr.ai",
            "https://www.mydscvr.ai", 
            "http://mydscvr.ai",
            "http://www.mydscvr.ai",
            "https://mydscvr.xyz",
            "https://www.mydscvr.xyz",
            "http://mydscvr.xyz", 
            "http://www.mydscvr.xyz",
            "http://localhost:8080",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5000",
            "http://localhost:5173"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Add permanent CORS headers for critical endpoints"""
        
        # Check if this is a critical path
        is_critical_path = any(
            request.url.path.startswith(path) 
            for path in self.critical_paths
        )
        
        if is_critical_path:
            logger.debug(f"Applying permanent CORS to critical path: {request.url.path}")
            
            # Get origin from request
            origin = request.headers.get("origin", "")
            
            # Determine response origin
            if origin in self.allowed_origins:
                response_origin = origin
            elif origin.startswith("http://localhost:") or origin.startswith("https://localhost:"):
                # Allow any localhost for development
                response_origin = origin
            else:
                # Default to production origin for unknown origins
                response_origin = "https://mydscvr.ai"
            
            # Handle preflight OPTIONS requests
            if request.method == "OPTIONS":
                response = Response(
                    content="OK",
                    status_code=200,
                    headers={
                        "Access-Control-Allow-Origin": response_origin,
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin, User-Agent, x-session-token",
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Max-Age": "3600",
                        "Content-Type": "text/plain"
                    }
                )
                return response
            
            # Process the request
            response = await call_next(request)
            
            # Add CORS headers to the response
            response.headers["Access-Control-Allow-Origin"] = response_origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "*"
            
            return response
        
        # For non-critical paths, proceed normally
        return await call_next(request)


def add_permanent_cors_headers(response: Response, origin: str = "https://mydscvr.ai"):
    """
    Utility function to add permanent CORS headers to any response
    Use this in route handlers that need guaranteed CORS support
    """
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response


def get_safe_origin(request: Request) -> str:
    """
    Get a safe origin for CORS responses
    Returns the request origin if it's in the allowed list, otherwise returns production origin
    """
    allowed_origins = [
        "https://mydscvr.ai",
        "https://www.mydscvr.ai", 
        "http://mydscvr.ai",
        "http://www.mydscvr.ai",
        "https://mydscvr.xyz",
        "https://www.mydscvr.xyz",
        "http://mydscvr.xyz", 
        "http://www.mydscvr.xyz"
    ]
    
    origin = request.headers.get("origin", "")
    
    if origin in allowed_origins:
        return origin
    elif origin.startswith("http://localhost:") or origin.startswith("https://localhost:"):
        return origin
    else:
        return "https://mydscvr.ai"