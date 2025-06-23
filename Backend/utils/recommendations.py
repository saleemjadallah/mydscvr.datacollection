"""
MongoDB-based recommendation engine for DXB Events API
Removed PostgreSQL dependencies - MongoDB only implementation
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.user_models import UserModel


class MongoRecommendationEngine:
    """MongoDB-based recommendation engine for events"""
    
    def __init__(self, mongo_db: AsyncIOMotorDatabase):
        self.mongo_db = mongo_db
    
    async def get_user_recommendations(
        self, 
        user: UserModel, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a user based on their preferences and interactions
        """
        try:
            # Get user's preferences
            preferences = user.preferences or {}
            interests = preferences.get("interests", [])
            preferred_areas = preferences.get("preferred_areas", [])
            budget_max = preferences.get("budget_max", 1000)
            
            # Build recommendation filter
            recommendation_filter = {
                "status": "active",
                "start_date": {"$gte": datetime.utcnow()}
            }
            
            # Add preference-based filters
            if interests:
                recommendation_filter["category_tags"] = {"$in": interests}
            
            if preferred_areas:
                recommendation_filter["area"] = {"$in": preferred_areas}
            
            if budget_max:
                recommendation_filter["price_min"] = {"$lte": budget_max}
            
            # Get recommended events
            events_cursor = self.mongo_db.events.find(recommendation_filter).sort("start_date", 1).limit(limit)
            events = await events_cursor.to_list(length=limit)
            
            return events
            
        except Exception as e:
            print(f"Error getting user recommendations: {e}")
            return []
    
    async def get_family_recommendations(
        self, 
        user: UserModel, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get family-friendly recommendations
        """
        try:
            # Build family-friendly filter
            family_filter = {
                "status": "active",
                "start_date": {"$gte": datetime.utcnow()},
                "family_suitability.is_family_friendly": True
            }
            
            # Consider user preferences if available
            preferences = user.preferences or {}
            if preferences.get("preferred_areas"):
                family_filter["area"] = {"$in": preferences["preferred_areas"]}
            
            if preferences.get("budget_max"):
                family_filter["price_min"] = {"$lte": preferences["budget_max"]}
            
            # Get family-friendly events
            events_cursor = self.mongo_db.events.find(family_filter).sort("start_date", 1).limit(limit)
            events = await events_cursor.to_list(length=limit)
            
            return events
            
        except Exception as e:
            print(f"Error getting family recommendations: {e}")
            return []
    
    async def get_similar_events(
        self, 
        event_id: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get events similar to a given event
        """
        try:
            # Get the reference event
            from bson import ObjectId
            reference_event = await self.mongo_db.events.find_one({"_id": ObjectId(event_id)})
            
            if not reference_event:
                return []
            
            # Build similarity filter
            similarity_filter = {
                "_id": {"$ne": ObjectId(event_id)},
                "status": "active",
                "start_date": {"$gte": datetime.utcnow()}
            }
            
            # Add category similarity
            if reference_event.get("category_tags"):
                similarity_filter["category_tags"] = {"$in": reference_event["category_tags"]}
            
            # Add area similarity
            if reference_event.get("area"):
                similarity_filter["area"] = reference_event["area"]
            
            # Get similar events
            events_cursor = self.mongo_db.events.find(similarity_filter).sort("start_date", 1).limit(limit)
            events = await events_cursor.to_list(length=limit)
            
            return events
            
        except Exception as e:
            print(f"Error getting similar events: {e}")
            return []
    
    async def get_trending_events(
        self, 
        limit: int = 10,
        time_window_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get trending events based on popularity metrics
        """
        try:
            # Calculate time window
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=time_window_days)
            
            # Build trending filter
            trending_filter = {
                "status": "active",
                "start_date": {"$gte": start_date, "$lte": end_date}
            }
            
            # Sort by popularity metrics (save_count, view_count, etc.)
            events_cursor = self.mongo_db.events.find(trending_filter).sort([
                ("save_count", -1),
                ("view_count", -1),
                ("start_date", 1)
            ]).limit(limit)
            
            events = await events_cursor.to_list(length=limit)
            
            return events
            
        except Exception as e:
            print(f"Error getting trending events: {e}")
            return []


# Legacy compatibility wrapper
class FamilyRecommendationEngine(MongoRecommendationEngine):
    """Legacy wrapper for family recommendations"""
    
    def __init__(self, mongo_db: AsyncIOMotorDatabase, postgres_db=None):
        # Ignore postgres_db parameter for MongoDB-only implementation
        super().__init__(mongo_db)


def calculate_event_family_score(event_data: Dict[str, Any]) -> int:
    """
    Calculate family suitability score for an event (0-100)
    Used when creating/updating events
    """
    score = 50  # Base score
    
    # Age range appropriateness
    age_min = event_data.get('age_min', 0)
    age_max = event_data.get('age_max', 99)
    
    if age_min <= 12 and age_max >= 5:  # Good for children
        score += 20
    if age_min <= 18 and age_max >= 13:  # Good for teens
        score += 15
    if age_min == 0 and age_max >= 60:  # All ages welcome
        score += 10
    
    # Category-based scoring
    categories = event_data.get('category_tags', [])
    family_friendly_categories = [
        'family', 'children', 'kids', 'educational', 'outdoor', 'sports',
        'arts', 'cultural', 'entertainment', 'workshops', 'parks'
    ]
    
    category_matches = len(set(categories) & set(family_friendly_categories))
    if category_matches > 0:
        score += min(15, category_matches * 5)
    
    # Price considerations
    price_min = event_data.get('price_min', 0)
    if price_min == 0:  # Free events
        score += 10
    elif price_min <= 50:  # Affordable
        score += 5
    elif price_min > 500:  # Expensive
        score -= 10
    
    # Duration considerations
    duration = event_data.get('duration_hours')
    if duration:
        if 1 <= duration <= 3:  # Good duration for families
            score += 5
        elif duration > 6:  # Too long
            score -= 5
    
    # Venue amenities (if available)
    amenities = event_data.get('amenities', {})
    if isinstance(amenities, dict):
        if amenities.get('parking'):
            score += 3
        if amenities.get('stroller_friendly'):
            score += 5
        if amenities.get('family_restrooms'):
            score += 3
    
    return max(0, min(100, score)) 