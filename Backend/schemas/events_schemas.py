"""
Event schemas for MongoDB-only backend
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class EventResponse(BaseModel):
    """Event response schema for API"""
    id: str = Field(..., description="Event ID")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    category: Optional[str] = Field(None, description="Event category")
    start_date: datetime = Field(..., description="Event start date")
    end_date: Optional[datetime] = Field(None, description="Event end date")
    venue: Optional[Dict[str, Any]] = Field(None, description="Venue information")
    price: Optional[Dict[str, Any]] = Field(None, description="Pricing information")
    family_score: Optional[int] = Field(None, description="Family suitability score")
    age_range: Optional[str] = Field(None, description="Age range")
    tags: List[str] = Field(default_factory=list, description="Event tags")
    image_urls: List[str] = Field(default_factory=list, description="Event image URLs")
    booking_url: Optional[str] = Field(None, description="Event booking URL")
    is_family_friendly: bool = Field(False, description="Family friendly indicator")
    is_saved: bool = Field(False, description="Whether user has saved this event")
    duration_hours: Optional[float] = Field(None, description="Event duration in hours")
    source_name: Optional[str] = Field(None, description="Data source")
    
    # Enhanced fields from Perplexity extraction
    event_url: Optional[str] = Field(None, description="Direct event URL")
    source_url: Optional[str] = Field(None, description="Source URL")
    social_media: Optional[Dict[str, Any]] = Field(None, description="Social media links")
    quality_metrics: Optional[Dict[str, Any]] = Field(None, description="Quality metrics")
    ticket_links: List[str] = Field(default_factory=list, description="Ticket booking links")
    contact_info: Optional[str] = Field(None, description="Contact information")
    target_audience: List[str] = Field(default_factory=list, description="Target audience")
    age_restrictions: Optional[str] = Field(None, description="Age restrictions")
    dress_code: Optional[str] = Field(None, description="Dress code")
    recurring: Optional[bool] = Field(None, description="Is recurring event")
    venue_type: Optional[str] = Field(None, description="Venue type")
    metro_accessible: Optional[bool] = Field(None, description="Metro accessible")
    special_needs_friendly: Optional[bool] = Field(None, description="Special needs friendly")
    language_requirements: Optional[str] = Field(None, description="Language requirements")
    alcohol_served: Optional[bool] = Field(None, description="Alcohol served")
    transportation_notes: Optional[str] = Field(None, description="Transportation notes")
    primary_category: Optional[str] = Field(None, description="Primary category")
    secondary_categories: List[str] = Field(default_factory=list, description="Secondary categories")
    event_type: Optional[str] = Field(None, description="Event type")
    indoor_outdoor: Optional[str] = Field(None, description="Indoor/outdoor setting")
    special_occasion: Optional[str] = Field(None, description="Special occasion")


class EventListResponse(BaseModel):
    """Event list response schema"""
    events: List[EventResponse] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total pages")
    pagination: Optional[Dict[str, Any]] = Field(None, description="Pagination information")
    filters: Optional[Dict[str, Any]] = Field(None, description="Available filters")


class SearchQuery(BaseModel):
    """Search query schema"""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Category filter")
    location: Optional[str] = Field(None, description="Location filter")
    date_from: Optional[datetime] = Field(None, description="Date from filter")
    date_to: Optional[datetime] = Field(None, description="Date to filter")


class SearchSuggestion(BaseModel):
    """Search suggestion schema"""
    text: str = Field(..., description="Suggestion text")
    type: str = Field(..., description="Suggestion type (event, category, area, etc.)")
    count: int = Field(default=1, description="Number of matching items")


class SearchSuggestionsResponse(BaseModel):
    """Search suggestions response schema"""
    suggestions: List[SearchSuggestion] = Field(..., description="List of suggestions")


class SearchFiltersResponse(BaseModel):
    """Search filters response schema"""
    categories: List[str] = Field(..., description="Available categories")
    areas: List[str] = Field(..., description="Available areas")
    price_ranges: List[Dict[str, Any]] = Field(..., description="Available price ranges")
    age_groups: List[str] = Field(..., description="Available age groups")


class SearchFilters(BaseModel):
    """Search filters schema"""
    categories: List[str] = Field(default_factory=list, description="Category filters")
    areas: List[str] = Field(default_factory=list, description="Area filters")
    price_min: Optional[float] = Field(None, description="Minimum price")
    price_max: Optional[float] = Field(None, description="Maximum price")
    family_friendly: Optional[bool] = Field(None, description="Family friendly filter")


class UserEventCreate(BaseModel):
    """User event creation schema"""
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Event description")
    start_date: datetime = Field(..., description="Event start date")
    end_date: Optional[datetime] = Field(None, description="Event end date")
    location: str = Field(..., description="Event location")


class UserEventResponse(BaseModel):
    """User event response schema"""
    id: str = Field(..., description="Event ID")
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Event description")
    start_date: datetime = Field(..., description="Event start date")
    end_date: Optional[datetime] = Field(None, description="Event end date")
    location: str = Field(..., description="Event location")
    created_by: str = Field(..., description="Creator user ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class SuccessResponse(BaseModel):
    """Generic success response schema"""
    success: bool = Field(True, description="Success indicator")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")