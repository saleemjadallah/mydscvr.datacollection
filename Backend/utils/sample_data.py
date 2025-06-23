"""
Sample data generator for DXB Events Phase 2 testing
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
from bson import ObjectId

def generate_sample_events(count: int = 50) -> List[Dict[str, Any]]:
    """Generate sample event data for testing"""
    
    # Dubai areas
    dubai_areas = [
        "Dubai Marina", "JBR", "Downtown Dubai", "DIFC", "Business Bay",
        "Jumeirah", "Umm Suqeim", "Al Wasl", "Deira", "Bur Dubai",
        "Mall of the Emirates", "Dubai Mall", "City Walk", "La Mer",
        "Al Seef", "Global Village", "IMG Worlds", "Dubai Hills"
    ]
    
    # Event categories
    categories = [
        ["family", "outdoor", "parks"], ["children", "educational", "workshops"],
        ["arts", "cultural", "entertainment"], ["sports", "fitness", "outdoor"],
        ["food", "dining", "family"], ["shopping", "lifestyle", "family"],
        ["entertainment", "shows", "family"], ["educational", "science", "kids"],
        ["outdoor", "adventure", "sports"], ["cultural", "heritage", "family"]
    ]
    
    # Event templates
    event_templates = [
        {
            "title": "Family Fun Day at {area}",
            "description": "Join us for a day of family-friendly activities including games, food, and entertainment suitable for all ages.",
            "duration_hours": 4,
            "price_range": (0, 50),
            "age_range": (0, 99),
            "categories": ["family", "outdoor", "entertainment"]
        },
        {
            "title": "Kids Science Workshop - {area}",
            "description": "Interactive science workshop where children learn through hands-on experiments and activities.",
            "duration_hours": 2,
            "price_range": (75, 150),
            "age_range": (5, 12),
            "categories": ["children", "educational", "science"]
        },
        {
            "title": "Cultural Heritage Tour - {area}",
            "description": "Explore Dubai's rich cultural heritage with guided tours and traditional activities.",
            "duration_hours": 3,
            "price_range": (100, 200),
            "age_range": (8, 99),
            "categories": ["cultural", "heritage", "educational"]
        },
        {
            "title": "Beach Sports Festival - {area}",
            "description": "Beach volleyball, football, and water sports activities for the whole family.",
            "duration_hours": 5,
            "price_range": (50, 120),
            "age_range": (10, 50),
            "categories": ["sports", "outdoor", "beach"]
        },
        {
            "title": "Art & Craft Workshop - {area}",
            "description": "Creative workshops for children and adults to create beautiful art pieces together.",
            "duration_hours": 2.5,
            "price_range": (80, 180),
            "age_range": (6, 99),
            "categories": ["arts", "crafts", "family"]
        },
        {
            "title": "Food Festival - {area}",
            "description": "Taste authentic cuisines from around the world in a family-friendly environment.",
            "duration_hours": 6,
            "price_range": (0, 300),
            "age_range": (0, 99),
            "categories": ["food", "cultural", "family"]
        },
        {
            "title": "Adventure Park Day - {area}",
            "description": "Thrilling rides, games, and activities for adventurous families and children.",
            "duration_hours": 8,
            "price_range": (200, 500),
            "age_range": (8, 60),
            "categories": ["adventure", "entertainment", "family"]
        },
        {
            "title": "Educational Museum Visit - {area}",
            "description": "Interactive museum experience with educational exhibits and hands-on learning.",
            "duration_hours": 3,
            "price_range": (40, 80),
            "age_range": (4, 99),
            "categories": ["educational", "museum", "family"]
        },
        {
            "title": "Music & Dance Show - {area}",
            "description": "Family-friendly musical performances and interactive dance activities.",
            "duration_hours": 2,
            "price_range": (60, 150),
            "age_range": (3, 99),
            "categories": ["music", "dance", "entertainment"]
        },
        {
            "title": "Nature Walk & Wildlife - {area}",
            "description": "Guided nature walks with wildlife spotting and environmental education.",
            "duration_hours": 3,
            "price_range": (30, 70),
            "age_range": (6, 99),
            "categories": ["nature", "educational", "outdoor"]
        }
    ]
    
    venues = [
        {"name": "Dubai Marina Walk", "type": "outdoor"},
        {"name": "JBR Beach", "type": "beach"},
        {"name": "Dubai Mall", "type": "mall"},
        {"name": "Mall of the Emirates", "type": "mall"},
        {"name": "City Walk", "type": "outdoor"},
        {"name": "La Mer", "type": "beach"},
        {"name": "Al Seef", "type": "cultural"},
        {"name": "Global Village", "type": "cultural"},
        {"name": "Jumeirah Public Beach", "type": "beach"},
        {"name": "Dubai Hills Park", "type": "park"}
    ]
    
    events = []
    
    for i in range(count):
        # Select random template and area
        template = random.choice(event_templates)
        area = random.choice(dubai_areas)
        venue = random.choice(venues)
        
        # Generate random dates (next 60 days)
        days_ahead = random.randint(1, 60)
        start_date = datetime.utcnow() + timedelta(days=days_ahead)
        
        # Add random hours to start time
        start_date = start_date.replace(
            hour=random.randint(9, 18),
            minute=random.choice([0, 15, 30, 45]),
            second=0,
            microsecond=0
        )
        
        end_date = start_date + timedelta(hours=template["duration_hours"])
        
        # Generate price
        price_min, price_max = template["price_range"]
        actual_price_min = random.randint(price_min, price_max)
        actual_price_max = actual_price_min + random.randint(0, 100) if actual_price_min > 0 else 0
        
        # Calculate family score
        from utils.recommendations import calculate_event_family_score
        
        event_data = {
            "title": template["title"].format(area=area),
            "description": template["description"],
            "start_date": start_date,
            "end_date": end_date,
            "area": area,
            "venue_name": f"{venue['name']} - {area}",
            "venue_address": f"Address in {area}, Dubai, UAE",
            "price_min": actual_price_min,
            "price_max": actual_price_max if actual_price_max > actual_price_min else None,
            "currency": "AED",
            "age_min": template["age_range"][0],
            "age_max": template["age_range"][1],
            "category_tags": template["categories"],
            "is_family_friendly": True,
            "duration_hours": template["duration_hours"],
            "status": "active",
            "source_name": "Sample Data Generator",
            "booking_url": f"https://book.dxbevents.com/event/{i+1}",
            "image_urls": [
                f"https://images.dxbevents.com/event_{i+1}_1.jpg",
                f"https://images.dxbevents.com/event_{i+1}_2.jpg"
            ],
            "view_count": random.randint(10, 500),
            "save_count": random.randint(2, 50),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Add location coordinates (approximate Dubai coordinates)
        event_data["location"] = {
            "type": "Point",
            "coordinates": [
                55.2708 + random.uniform(-0.3, 0.3),  # Dubai longitude range
                25.2048 + random.uniform(-0.2, 0.2)   # Dubai latitude range
            ]
        }
        
        # Calculate family score
        event_data["family_score"] = calculate_event_family_score(event_data)
        
        events.append(event_data)
    
    return events


async def populate_sample_events(db, count: int = 50):
    """Populate MongoDB with sample events"""
    
    print(f"🌱 Generating {count} sample events...")
    
    # Clear existing sample data
    result = await db.events.delete_many({"source_name": "Sample Data Generator"})
    if result.deleted_count > 0:
        print(f"🧹 Cleared {result.deleted_count} existing sample events")
    
    # Generate and insert new sample data
    sample_events = generate_sample_events(count)
    
    if sample_events:
        result = await db.events.insert_many(sample_events)
        print(f"✅ Inserted {len(result.inserted_ids)} sample events")
        
        # Create text index for search if it doesn't exist
        try:
            await db.events.create_index([
                ("title", "text"),
                ("description", "text"),
                ("category_tags", "text"),
                ("area", "text"),
                ("venue_name", "text")
            ])
            print("✅ Created text search index")
        except Exception as e:
            print(f"ℹ️ Text index already exists or failed to create: {e}")
        
        # Create geospatial index for location searches
        try:
            await db.events.create_index([("location", "2dsphere")])
            print("✅ Created geospatial index")
        except Exception as e:
            print(f"ℹ️ Geospatial index already exists or failed to create: {e}")
        
        return len(result.inserted_ids)
    
    return 0


def get_sample_users_with_families() -> List[Dict[str, Any]]:
    """Generate sample user family data for testing recommendations"""
    
    families = [
        {
            "email": "family1@test.com",
            "profile": {
                "first_name": "Ahmed",
                "last_name": "Al-Rashid",
                "location_preference": "Dubai Marina",
                "budget_range": "medium",
                "preferences": {
                    "event_types": ["family", "outdoor", "cultural"],
                    "interests": ["parks", "museums", "sports"]
                }
            },
            "family_members": [
                {"name": "Fatima", "age": 8, "relationship_type": "child", "interests": ["arts", "crafts", "science"]},
                {"name": "Omar", "age": 12, "relationship_type": "child", "interests": ["sports", "adventure", "technology"]},
                {"name": "Aisha", "age": 35, "relationship_type": "parent", "interests": ["cultural", "educational", "food"]}
            ]
        },
        {
            "email": "expat_family@test.com",
            "profile": {
                "first_name": "James",
                "last_name": "Wilson",
                "location_preference": "JBR",
                "budget_range": "high",
                "preferences": {
                    "event_types": ["entertainment", "beach", "food"],
                    "interests": ["water sports", "dining", "shopping"]
                }
            },
            "family_members": [
                {"name": "Emma", "age": 6, "relationship_type": "child", "interests": ["beach", "animals", "music"]},
                {"name": "Liam", "age": 10, "relationship_type": "child", "interests": ["sports", "games", "beach"]},
                {"name": "Sarah", "age": 32, "relationship_type": "parent", "interests": ["fitness", "wellness", "photography"]}
            ]
        },
        {
            "email": "young_family@test.com",
            "profile": {
                "first_name": "Priya",
                "last_name": "Sharma",
                "location_preference": "Downtown Dubai",
                "budget_range": "low",
                "preferences": {
                    "event_types": ["educational", "free", "parks"],
                    "interests": ["learning", "nature", "community"]
                }
            },
            "family_members": [
                {"name": "Arjun", "age": 4, "relationship_type": "child", "interests": ["animals", "stories", "playground"]},
                {"name": "Raj", "age": 30, "relationship_type": "parent", "interests": ["education", "technology", "reading"]}
            ]
        }
    ]
    
    return families 