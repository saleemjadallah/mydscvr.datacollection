from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class RawEventModel(BaseModel):
    """Schema for raw scraped events collection."""
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    source: str = Field(..., description="Source website identifier")
    source_url: str = Field(..., description="Original URL of the event")
    source_event_id: Optional[str] = Field(None, description="Unique ID from source")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    raw_html: Optional[str] = Field(None, description="Raw HTML content")
    raw_data: Dict[str, Any] = Field(..., description="Structured data extracted from source")
    status: str = Field(default="pending_processing", description="Processing status")
    processing_attempts: int = Field(default=0)
    last_processing_attempt: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class VenueInfo(BaseModel):
    """Venue information schema."""
    
    name: str
    address: Optional[str] = None
    area: Optional[str] = None
    coordinates: Optional[List[float]] = None  # [longitude, latitude]
    amenities: List[str] = Field(default_factory=list)
    parking_available: Optional[bool] = None
    public_transport_access: Optional[bool] = None


class PricingInfo(BaseModel):
    """Pricing information schema."""
    
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    currency: str = "AED"
    pricing_details: Optional[str] = None
    free_options: bool = False
    discounts_available: Optional[str] = None


class FamilySuitability(BaseModel):
    """Family suitability assessment schema."""
    
    age_min: int = 0
    age_max: int = 99
    family_friendly: bool = True
    stroller_friendly: Optional[bool] = None
    indoor_outdoor: Optional[str] = None  # "indoor", "outdoor", "both"
    family_score: Optional[int] = None  # 0-100 family friendliness score
    family_amenities: List[str] = Field(default_factory=list)


class SourceDetails(BaseModel):
    """Source-specific metadata."""
    
    source_name: str
    source_url: str
    last_updated: Optional[datetime] = None
    data_quality_score: Optional[int] = None
    source_reliability: Optional[str] = None


class ProcessedEventModel(BaseModel):
    """Schema for processed events ready for backend sync."""
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    raw_event_id: PyObjectId = Field(..., description="Reference to raw event")
    source_id: str = Field(..., description="Unique identifier from source")
    
    # Core Event Information
    title: str = Field(..., description="Event title")
    description: str = Field(..., description="Full event description")
    ai_summary: Optional[str] = Field(None, description="AI-generated summary")
    
    # Date and Time
    start_date: datetime = Field(..., description="Event start date and time")
    end_date: Optional[datetime] = Field(None, description="Event end date and time")
    timezone: str = Field(default="Asia/Dubai")
    
    # Location
    venue: VenueInfo = Field(..., description="Venue information")
    
    # Pricing
    pricing: PricingInfo = Field(..., description="Pricing information")
    
    # Family Information
    family_suitability: FamilySuitability = Field(..., description="Family suitability assessment")
    
    # Categories and Tags
    categories: List[str] = Field(default_factory=list, description="Event categories")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    
    # Media
    image_urls: List[str] = Field(default_factory=list, description="Event image URLs")
    
    # Source Information
    source_details: SourceDetails = Field(..., description="Source metadata")
    
    # Processing Information
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_version: str = Field(default="1.0.0")
    
    # Backend Sync Status
    sent_to_backend: bool = Field(default=False)
    backend_sync_status: str = Field(default="pending")  # pending, success, failed, retry
    backend_event_id: Optional[str] = Field(None, description="Backend system event ID")
    last_sync_attempt: Optional[datetime] = None
    sync_attempts: int = Field(default=0)
    sync_error_message: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Collection names
COLLECTIONS = {
    "raw_events": "raw_events",
    "processed_events": "processed_events",
    "processing_logs": "processing_logs",
    "sync_logs": "sync_logs"
}


# MongoDB Indexes
INDEXES = {
    "raw_events": [
        {"keys": [("source", 1), ("source_event_id", 1)], "unique": True},
        {"keys": [("scraped_at", -1)]},
        {"keys": [("status", 1)]},
        {"keys": [("source", 1), ("scraped_at", -1)]}
    ],
    "processed_events": [
        {"keys": [("source_id", 1)], "unique": True},
        {"keys": [("start_date", 1)]},
        {"keys": [("backend_sync_status", 1)]},
        {"keys": [("processed_at", -1)]},
        {"keys": [("categories", 1)]},
        {"keys": [("venue.area", 1)]},
        {"keys": [("family_suitability.family_friendly", 1)]}
    ]
} 