"""
Data processing and validation utilities for DXB Events API
Phase 4: Data Integration implementation
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid
from .deduplication import EventDeduplicator

# Dubai areas constant (local to avoid import issues)
DUBAI_AREAS = [
    "Dubai Marina", "JBR", "Downtown Dubai", "DIFC", "Business Bay",
    "Jumeirah", "Umm Suqeim", "Al Wasl", "Deira", "Bur Dubai",
    "Mall of the Emirates", "Dubai Mall", "City Walk", "La Mer",
    "Al Seef", "Global Village", "IMG Worlds", "Dubai Hills"
]


class DataProcessor:
    """
    Comprehensive data processor for event validation and normalization
    """
    
    def __init__(self, mongodb: AsyncIOMotorDatabase):
        self.mongodb = mongodb
        self.deduplicator = EventDeduplicator(mongodb)
        
        # Dubai area mappings for normalization
        self.area_aliases = {
            "downtown": "Downtown Dubai",
            "jbr": "JBR",
            "marina": "Dubai Marina",
            "creek": "Dubai Creek",
            "deira": "Deira",
            "bur_dubai": "Bur Dubai",
            "jumeirah": "Jumeirah",
            "satwa": "Satwa",
            "karama": "Karama",
            "discovery_gardens": "Discovery Gardens",
            "motor_city": "Motor City",
            "arabian_ranches": "Arabian Ranches",
            "emirates_hills": "Emirates Hills",
            "palm_jumeirah": "Palm Jumeirah",
            "dubai_hills": "Dubai Hills",
            "business_bay": "Business Bay",
            "difc": "DIFC",
            "festival_city": "Festival City"
        }
        
        # Category mappings for standardization
        self.category_mappings = {
            "kids": "family",
            "children": "family",
            "family_fun": "family",
            "music": "entertainment",
            "concert": "entertainment",
            "show": "entertainment",
            "theater": "entertainment",
            "exhibition": "culture",
            "art": "culture",
            "museum": "culture",
            "sports": "sports",
            "fitness": "sports",
            "workshop": "educational",
            "class": "educational",
            "course": "educational",
            "food": "dining",
            "restaurant": "dining",
            "shopping": "shopping",
            "outdoor": "outdoor",
            "beach": "outdoor",
            "park": "outdoor"
        }
    
    async def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing function that validates and normalizes event data
        """
        try:
            # Generate unique event ID
            event_id = self._generate_event_id(event_data)
            
            # Start with processed event
            processed_event = {
                "_id": event_id,
                **event_data
            }
            
            # Process individual fields
            processed_event = await self._normalize_title(processed_event)
            processed_event = await self._validate_dates(processed_event)
            processed_event = await self._normalize_pricing(processed_event)
            processed_event = await self._normalize_area(processed_event)
            processed_event = await self._normalize_categories(processed_event)
            processed_event = await self._process_venue_data(processed_event)
            processed_event = await self._validate_family_data(processed_event)
            processed_event = await self._calculate_metrics(processed_event)
            processed_event = await self._add_search_fields(processed_event)
            
            # Check for duplicates before saving
            is_duplicate = await self.deduplicator.is_duplicate_event(processed_event)
            if is_duplicate:
                print(f"🔄 DataProcessor: Duplicate detected and skipped: {processed_event.get('title', 'Unknown')}")
                return None  # Return None to indicate event was skipped due to duplication
            
            # Save to MongoDB
            await self.mongodb.events.insert_one(processed_event)
            print(f"✅ DataProcessor: Successfully processed and stored: {processed_event.get('title', 'Unknown')}")
            
            return processed_event
            
        except Exception as e:
            raise Exception(f"Data processing failed: {str(e)}")
    
    def _generate_event_id(self, event_data: Dict[str, Any]) -> str:
        """Generate unique event ID"""
        source_id = event_data.get("source_id", "")
        source_name = event_data.get("source_name", "unknown")
        title = event_data.get("title", "untitled")
        
        # Create deterministic ID based on source and title
        base_string = f"{source_name}:{source_id}:{title}"
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, base_string))
    
    async def _normalize_title(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and clean event title"""
        title = event.get("title", "").strip()
        
        if not title:
            title = "Untitled Event"
        
        # Remove excessive whitespace and special characters
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'[^\w\s\-\(\)\[\]&.,!]', '', title)
        
        # Capitalize properly
        title = title.title()
        
        event["title"] = title
        return event
    
    async def _validate_dates(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize event dates"""
        now = datetime.now(timezone.utc)
        
        # Process start date
        start_date = event.get("start_date")
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                start_date = now + timedelta(days=1)  # Default to tomorrow
        elif not isinstance(start_date, datetime):
            start_date = now + timedelta(days=1)
        
        # Process end date
        end_date = event.get("end_date")
        if end_date:
            if isinstance(end_date, str):
                try:
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    end_date = start_date + timedelta(hours=2)
            elif not isinstance(end_date, datetime):
                end_date = start_date + timedelta(hours=2)
        else:
            end_date = start_date + timedelta(hours=2)  # Default 2-hour duration
        
        # Ensure end_date is after start_date
        if end_date <= start_date:
            end_date = start_date + timedelta(hours=2)
        
        # Calculate duration
        duration_hours = (end_date - start_date).total_seconds() / 3600
        
        event.update({
            "start_date": start_date,
            "end_date": end_date,
            "duration_hours": round(duration_hours, 2)
        })
        
        return event
    
    async def _normalize_pricing(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize pricing information"""
        price_min = event.get("price_min", 0)
        price_max = event.get("price_max", 0)
        currency = event.get("currency", "AED")
        
        # Ensure prices are numbers
        try:
            price_min = float(price_min) if price_min is not None else 0
        except (ValueError, TypeError):
            price_min = 0
        
        try:
            price_max = float(price_max) if price_max is not None else price_min
        except (ValueError, TypeError):
            price_max = price_min
        
        # Ensure logical pricing
        if price_max < price_min:
            price_max = price_min
        
        # Normalize currency
        currency = currency.upper()
        if currency not in ["AED", "USD", "EUR", "GBP"]:
            currency = "AED"
        
        # Convert to AED if needed (simplified conversion)
        if currency != "AED":
            conversion_rates = {"USD": 3.67, "EUR": 4.0, "GBP": 4.5}
            rate = conversion_rates.get(currency, 1)
            price_min *= rate
            price_max *= rate
            currency = "AED"
        
        # Determine budget category
        budget_category = "low"
        if price_min > 200:
            budget_category = "high"
        elif price_min > 50:
            budget_category = "medium"
        
        event.update({
            "price_min": round(price_min, 2),
            "price_max": round(price_max, 2),
            "currency": currency,
            "budget_category": budget_category
        })
        
        return event
    
    async def _normalize_area(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize Dubai area information"""
        area = event.get("area", "").strip().lower()
        
        # Map area aliases
        normalized_area = self.area_aliases.get(area, area)
        
        # Check if it's a valid Dubai area
        if normalized_area.title() not in DUBAI_AREAS:
            # Try partial matching
            for dubai_area in DUBAI_AREAS:
                if area in dubai_area.lower() or dubai_area.lower() in area:
                    normalized_area = dubai_area
                    break
            else:
                normalized_area = "Dubai"  # Default fallback
        else:
            normalized_area = normalized_area.title()
        
        event["area"] = normalized_area
        return event
    
    async def _normalize_categories(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event categories and tags"""
        category_tags = event.get("category_tags", [])
        tags = event.get("tags", [])
        
        # Ensure categories are lists
        if isinstance(category_tags, str):
            category_tags = [category_tags]
        if isinstance(tags, str):
            tags = [tags]
        
        # Normalize categories
        normalized_categories = []
        for category in category_tags:
            if isinstance(category, str):
                category = category.lower().strip()
                normalized_category = self.category_mappings.get(category, category)
                if normalized_category not in normalized_categories:
                    normalized_categories.append(normalized_category)
        
        # Default category if none provided
        if not normalized_categories:
            normalized_categories = ["general"]
        
        # Clean and normalize tags
        normalized_tags = []
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                clean_tag = re.sub(r'[^\w\s]', '', tag.strip().lower())
                if clean_tag and clean_tag not in normalized_tags:
                    normalized_tags.append(clean_tag)
        
        event.update({
            "category_tags": normalized_categories,
            "tags": normalized_tags
        })
        
        return event
    
    async def _process_venue_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate venue information"""
        venue_name = event.get("venue_name", "").strip()
        venue_address = event.get("venue_address", "").strip()
        
        if not venue_name:
            venue_name = f"Venue in {event.get('area', 'Dubai')}"
        
        # Extract coordinates if available
        latitude = event.get("latitude")
        longitude = event.get("longitude")
        
        try:
            if latitude is not None:
                latitude = float(latitude)
            if longitude is not None:
                longitude = float(longitude)
        except (ValueError, TypeError):
            latitude = longitude = None
        
        # Default Dubai coordinates if not provided
        if latitude is None or longitude is None:
            # Central Dubai coordinates
            latitude = 25.276987
            longitude = 55.296249
        
        event.update({
            "venue_name": venue_name,
            "venue_address": venue_address or "Dubai, UAE",
            "latitude": latitude,
            "longitude": longitude
        })
        
        return event
    
    async def _validate_family_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize family-related data"""
        age_min = event.get("age_min", 0)
        age_max = event.get("age_max", 99)
        is_family_friendly = event.get("is_family_friendly", True)
        
        # Ensure ages are valid
        try:
            age_min = int(age_min) if age_min is not None else 0
            age_max = int(age_max) if age_max is not None else 99
        except (ValueError, TypeError):
            age_min = 0
            age_max = 99
        
        # Logical age validation
        if age_min < 0:
            age_min = 0
        if age_max > 120:
            age_max = 99
        if age_max < age_min:
            age_max = age_min + 1
        
        # Determine family friendliness
        if age_min <= 12:  # Suitable for children
            is_family_friendly = True
        
        # Calculate family score based on various factors
        family_score = self._calculate_family_score(event, age_min, age_max)
        
        event.update({
            "age_min": age_min,
            "age_max": age_max,
            "is_family_friendly": is_family_friendly,
            "family_score": family_score
        })
        
        return event
    
    def _calculate_family_score(self, event: Dict[str, Any], age_min: int, age_max: int) -> int:
        """Calculate family suitability score (0-100)"""
        score = 50  # Base score
        
        # Age range scoring
        if age_min <= 5:  # Suitable for toddlers
            score += 20
        elif age_min <= 12:  # Suitable for children
            score += 15
        
        if age_max >= 60:  # Suitable for grandparents
            score += 10
        
        # Category scoring
        categories = event.get("category_tags", [])
        family_categories = ["family", "educational", "outdoor", "culture"]
        for category in categories:
            if category in family_categories:
                score += 10
                break
        
        # Pricing scoring (affordable = more family-friendly)
        price_min = event.get("price_min", 0)
        if price_min == 0:  # Free events
            score += 15
        elif price_min <= 50:  # Affordable
            score += 10
        elif price_min <= 100:  # Moderate
            score += 5
        else:  # Expensive
            score -= 5
        
        # Duration scoring (not too long for families)
        duration = event.get("duration_hours", 2)
        if 1 <= duration <= 3:  # Ideal duration
            score += 10
        elif duration <= 5:  # Acceptable
            score += 5
        
        # Area scoring (family-friendly areas)
        area = event.get("area", "")
        family_areas = ["JBR", "Dubai Marina", "Jumeirah", "Festival City", "Dubai Hills"]
        if area in family_areas:
            score += 5
        
        return max(0, min(100, score))
    
    async def _calculate_metrics(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate additional metrics for the event"""
        now = datetime.now(timezone.utc)
        start_date = event.get("start_date", now)
        
        # Calculate days until event
        days_until = (start_date - now).days if start_date > now else 0
        
        # Initialize engagement metrics
        view_count = 0
        save_count = 0
        popularity_score = 0
        
        # Calculate base popularity score
        popularity_factors = {
            "is_free": 10 if event.get("price_min", 0) == 0 else 0,
            "family_friendly": 15 if event.get("is_family_friendly") else 0,
            "weekend": 10 if start_date.weekday() >= 5 else 0,
            "prime_time": 5 if 10 <= start_date.hour <= 18 else 0,
            "good_duration": 10 if 1 <= event.get("duration_hours", 0) <= 4 else 0
        }
        
        popularity_score = sum(popularity_factors.values())
        
        event.update({
            "days_until": days_until,
            "view_count": view_count,
            "save_count": save_count,
            "popularity_score": popularity_score,
            "engagement_rate": 0.0,
            "recommendation_score": popularity_score * event.get("family_score", 50) / 100
        })
        
        return event
    
    async def _add_search_fields(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Add fields optimized for search functionality"""
        title = event.get("title", "")
        description = event.get("description", "")
        categories = event.get("category_tags", [])
        tags = event.get("tags", [])
        venue_name = event.get("venue_name", "")
        area = event.get("area", "")
        
        # Create comprehensive search text
        search_text = " ".join([
            title,
            description or "",
            venue_name,
            area,
            " ".join(categories),
            " ".join(tags)
        ]).lower()
        
        # Extract keywords for search
        keywords = list(set([
            word.strip() for word in re.findall(r'\w+', search_text)
            if len(word.strip()) > 2
        ]))
        
        # Add search metadata
        event.update({
            "search_text": search_text,
            "keywords": keywords,
            "search_boost": event.get("family_score", 50) / 100,
            "indexed_at": datetime.now(timezone.utc)
        })
        
        return event
    
    async def validate_event_data(self, event: Dict[str, Any]) -> List[str]:
        """Validate event data and return list of validation errors"""
        errors = []
        
        # Required fields validation
        required_fields = ["title", "start_date", "source_name"]
        for field in required_fields:
            if not event.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Date validation
        start_date = event.get("start_date")
        if start_date and isinstance(start_date, datetime):
            if start_date < datetime.now(timezone.utc) - timedelta(days=1):
                errors.append("Event start date is too far in the past")
        
        # Price validation
        price_min = event.get("price_min")
        if price_min is not None and price_min < 0:
            errors.append("Price cannot be negative")
        
        # Age validation
        age_min = event.get("age_min", 0)
        age_max = event.get("age_max", 99)
        if age_min > age_max:
            errors.append("Minimum age cannot be greater than maximum age")
        
        return errors 