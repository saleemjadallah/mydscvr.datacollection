"""
Webhook endpoints for external data integration - DXB Events API
Phase 4: Data Integration implementation
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, validator
import hashlib
import hmac
import json

from database import get_mongodb
from utils.data_processor import DataProcessor
from utils.deduplication import EventDeduplicator
from utils.image_service import ImageService
from schemas import SuccessResponse
from config import settings

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


# Webhook payload schemas
class TimeOutDubaiEvent(BaseModel):
    """TimeOut Dubai event webhook payload schema"""
    id: str
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    area: Optional[str] = None
    price_aed: Optional[float] = None
    price_max_aed: Optional[float] = None
    category: Optional[str] = None
    tags: List[str] = []
    image_url: Optional[str] = None
    booking_url: Optional[str] = None
    age_min: Optional[int] = 0
    age_max: Optional[int] = 99
    is_family_friendly: Optional[bool] = True
    
    @validator('start_date', 'end_date', pre=True)
    def parse_dates(cls, v):
        if v and isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return datetime.now(timezone.utc)
        return v


class PlatinumListEvent(BaseModel):
    """PlatinumList event webhook payload schema"""
    event_id: str
    name: str
    details: Optional[str] = None
    event_date: str
    end_date: Optional[str] = None
    location: Optional[str] = None
    location_area: Optional[str] = None
    ticket_price: Optional[float] = None
    max_price: Optional[float] = None
    event_type: Optional[str] = None
    event_tags: List[str] = []
    featured_image: Optional[str] = None
    ticket_link: Optional[str] = None
    min_age: Optional[int] = 0
    max_age: Optional[int] = 99
    family_event: Optional[bool] = True


class GenericEvent(BaseModel):
    """Generic event webhook payload schema"""
    source_id: str
    source_name: str
    title: str
    description: Optional[str] = None
    start_datetime: str
    end_datetime: Optional[str] = None
    venue: Optional[Dict[str, Any]] = {}
    pricing: Optional[Dict[str, Any]] = {}
    categories: List[str] = []
    metadata: Dict[str, Any] = {}


class WebhookResponse(BaseModel):
    """Standard webhook response"""
    success: bool
    message: str
    processed_events: int = 0
    duplicates_found: int = 0
    errors: List[str] = []
    event_ids: List[str] = []


# Webhook security
def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature for security"""
    if not secret:
        return True  # Skip verification in development
    
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@router.post("/events/timeout-dubai", response_model=WebhookResponse)
async def receive_timeout_dubai_events(
    events: List[TimeOutDubaiEvent],
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Webhook endpoint for TimeOut Dubai event data
    Receives and processes events from TimeOut Dubai's content management system
    """
    try:
        # Verify webhook signature (in production)
        signature = request.headers.get("X-Webhook-Signature", "")
        payload = await request.body()
        
        if not verify_webhook_signature(payload, signature, getattr(settings, 'timeout_webhook_secret', '')):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Initialize services
        mongodb = await get_mongodb()
        data_processor = DataProcessor(mongodb)
        deduplicator = EventDeduplicator(mongodb)
        image_service = ImageService()
        
        processed_events = []
        duplicates_found = 0
        errors = []
        
        for event_data in events:
            try:
                # Convert TimeOut format to standard format
                standardized_event = {
                    "source_id": event_data.id,
                    "source_name": "TimeOut Dubai",
                    "title": event_data.title,
                    "description": event_data.description,
                    "start_date": event_data.start_date,
                    "end_date": event_data.end_date,
                    "venue_name": event_data.venue_name,
                    "venue_address": event_data.venue_address,
                    "area": event_data.area or "Dubai",
                    "price_min": event_data.price_aed or 0,
                    "price_max": event_data.price_max_aed or event_data.price_aed or 0,
                    "currency": "AED",
                    "category_tags": [event_data.category] if event_data.category else [],
                    "tags": event_data.tags,
                    "image_urls": [event_data.image_url] if event_data.image_url else [],
                    "booking_url": event_data.booking_url,
                    "age_min": event_data.age_min,
                    "age_max": event_data.age_max,
                    "is_family_friendly": event_data.is_family_friendly,
                    "source_data": event_data.dict(),
                    "imported_at": datetime.now(timezone.utc)
                }
                
                # Check for duplicates
                is_duplicate = await deduplicator.is_duplicate_event(standardized_event)
                if is_duplicate:
                    duplicates_found += 1
                    continue
                
                # Process and validate event data
                processed_event = await data_processor.process_event(standardized_event)
                
                # Handle image processing in background
                if processed_event.get("image_urls"):
                    background_tasks.add_task(
                        image_service.process_event_images,
                        processed_event["_id"],
                        processed_event["image_urls"]
                    )
                
                processed_events.append(processed_event["_id"])
                
            except Exception as e:
                errors.append(f"Failed to process event {event_data.id}: {str(e)}")
                continue
        
        return WebhookResponse(
            success=True,
            message=f"Processed {len(processed_events)} events from TimeOut Dubai",
            processed_events=len(processed_events),
            duplicates_found=duplicates_found,
            errors=errors,
            event_ids=processed_events
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post("/events/platinumlist", response_model=WebhookResponse)
async def receive_platinumlist_events(
    events: List[PlatinumListEvent],
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Webhook endpoint for PlatinumList event data
    Receives and processes premium events from PlatinumList
    """
    try:
        # Verify webhook signature
        signature = request.headers.get("X-PlatinumList-Signature", "")
        payload = await request.body()
        
        if not verify_webhook_signature(payload, signature, getattr(settings, 'platinumlist_webhook_secret', '')):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Initialize services
        mongodb = await get_mongodb()
        data_processor = DataProcessor(mongodb)
        deduplicator = EventDeduplicator(mongodb)
        image_service = ImageService()
        
        processed_events = []
        duplicates_found = 0
        errors = []
        
        for event_data in events:
            try:
                # Convert PlatinumList format to standard format
                standardized_event = {
                    "source_id": event_data.event_id,
                    "source_name": "PlatinumList",
                    "title": event_data.name,
                    "description": event_data.details,
                    "start_date": datetime.fromisoformat(event_data.event_date.replace('Z', '+00:00')),
                    "end_date": datetime.fromisoformat(event_data.end_date.replace('Z', '+00:00')) if event_data.end_date else None,
                    "venue_name": event_data.location,
                    "area": event_data.location_area or "Dubai",
                    "price_min": event_data.ticket_price or 0,
                    "price_max": event_data.max_price or event_data.ticket_price or 0,
                    "currency": "AED",
                    "category_tags": [event_data.event_type] if event_data.event_type else [],
                    "tags": event_data.event_tags,
                    "image_urls": [event_data.featured_image] if event_data.featured_image else [],
                    "booking_url": event_data.ticket_link,
                    "age_min": event_data.min_age,
                    "age_max": event_data.max_age,
                    "is_family_friendly": event_data.family_event,
                    "source_data": event_data.dict(),
                    "imported_at": datetime.now(timezone.utc),
                    "is_premium": True  # PlatinumList events are premium
                }
                
                # Check for duplicates
                is_duplicate = await deduplicator.is_duplicate_event(standardized_event)
                if is_duplicate:
                    duplicates_found += 1
                    continue
                
                # Process and validate event data
                processed_event = await data_processor.process_event(standardized_event)
                
                # Handle image processing in background
                if processed_event.get("image_urls"):
                    background_tasks.add_task(
                        image_service.process_event_images,
                        processed_event["_id"],
                        processed_event["image_urls"]
                    )
                
                processed_events.append(processed_event["_id"])
                
            except Exception as e:
                errors.append(f"Failed to process event {event_data.event_id}: {str(e)}")
                continue
        
        return WebhookResponse(
            success=True,
            message=f"Processed {len(processed_events)} premium events from PlatinumList",
            processed_events=len(processed_events),
            duplicates_found=duplicates_found,
            errors=errors,
            event_ids=processed_events
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.post("/events/generic", response_model=WebhookResponse)
async def receive_generic_events(
    events: List[GenericEvent],
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Generic webhook endpoint for any event source
    Flexible schema for integration with various event providers
    """
    try:
        # Basic authentication via API key
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != getattr(settings, 'webhook_api_key', 'dev-key'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Initialize services
        mongodb = await get_mongodb()
        data_processor = DataProcessor(mongodb)
        deduplicator = EventDeduplicator(mongodb)
        image_service = ImageService()
        
        processed_events = []
        duplicates_found = 0
        errors = []
        
        for event_data in events:
            try:
                # Convert generic format to standard format
                venue_info = event_data.venue or {}
                pricing_info = event_data.pricing or {}
                
                standardized_event = {
                    "source_id": event_data.source_id,
                    "source_name": event_data.source_name,
                    "title": event_data.title,
                    "description": event_data.description,
                    "start_date": datetime.fromisoformat(event_data.start_datetime.replace('Z', '+00:00')),
                    "end_date": datetime.fromisoformat(event_data.end_datetime.replace('Z', '+00:00')) if event_data.end_datetime else None,
                    "venue_name": venue_info.get("name"),
                    "venue_address": venue_info.get("address"),
                    "area": venue_info.get("area") or "Dubai",
                    "price_min": pricing_info.get("min", 0),
                    "price_max": pricing_info.get("max", 0),
                    "currency": pricing_info.get("currency", "AED"),
                    "category_tags": event_data.categories,
                    "tags": event_data.metadata.get("tags", []),
                    "image_urls": event_data.metadata.get("images", []),
                    "booking_url": event_data.metadata.get("booking_url"),
                    "age_min": event_data.metadata.get("age_min", 0),
                    "age_max": event_data.metadata.get("age_max", 99),
                    "is_family_friendly": event_data.metadata.get("family_friendly", True),
                    "source_data": event_data.dict(),
                    "imported_at": datetime.now(timezone.utc)
                }
                
                # Check for duplicates
                is_duplicate = await deduplicator.is_duplicate_event(standardized_event)
                if is_duplicate:
                    duplicates_found += 1
                    continue
                
                # Process and validate event data
                processed_event = await data_processor.process_event(standardized_event)
                
                # Handle image processing in background
                if processed_event.get("image_urls"):
                    background_tasks.add_task(
                        image_service.process_event_images,
                        processed_event["_id"],
                        processed_event["image_urls"]
                    )
                
                processed_events.append(processed_event["_id"])
                
            except Exception as e:
                errors.append(f"Failed to process event {event_data.source_id}: {str(e)}")
                continue
        
        return WebhookResponse(
            success=True,
            message=f"Processed {len(processed_events)} events from {event_data.source_name if events else 'unknown source'}",
            processed_events=len(processed_events),
            duplicates_found=duplicates_found,
            errors=errors,
            event_ids=processed_events
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generic webhook processing failed: {str(e)}"
        )


@router.get("/stats", response_model=dict)
async def get_webhook_stats():
    """
    Get webhook processing statistics
    """
    try:
        mongodb = await get_mongodb()
        
        # Get import statistics
        pipeline = [
            {"$match": {"imported_at": {"$exists": True}}},
            {"$group": {
                "_id": "$source_name",
                "total_events": {"$sum": 1},
                "latest_import": {"$max": "$imported_at"}
            }},
            {"$sort": {"total_events": -1}}
        ]
        
        source_stats = await mongodb.events.aggregate(pipeline).to_list(length=None)
        
        # Get today's imports
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_imports = await mongodb.events.count_documents({
            "imported_at": {"$gte": today}
        })
        
        return {
            "total_imported_events": await mongodb.events.count_documents({"imported_at": {"$exists": True}}),
            "today_imports": today_imports,
            "source_breakdown": source_stats,
            "active_sources": len(source_stats),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook stats: {str(e)}"
        )


@router.post("/test", response_model=SuccessResponse)
async def test_webhook_endpoint():
    """
    Test webhook endpoint to verify connectivity
    """
    return SuccessResponse(
        message="Webhook endpoint is operational",
        data={
            "endpoints": [
                "/api/webhooks/events/timeout-dubai",
                "/api/webhooks/events/platinumlist", 
                "/api/webhooks/events/generic"
            ],
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ) 