#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import re

async def improve_categorization():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]
    
    print("🚀 Improving Event Categorization & Tags...")
    print("=" * 60)
    
    # Define comprehensive categorization rules
    category_rules = {
        'food_and_dining': {
            'keywords': ['brunch', 'dinner', 'lunch', 'restaurant', 'food', 'dining', 'cuisine', 'chef', 'menu', 'buffet', 'iftar', 'feast', 'culinary', 'cooking', 'breakfast'],
            'title_patterns': [r'brunch', r'restaurant week', r'food', r'dining', r'culinary'],
            'priority': 10  # High priority for food events
        },
        'kids_and_family': {
            'keywords': ['family', 'kids', 'children', 'playground', 'edutainment', 'workshop', 'puppet', 'story', 'craft', 'toddler', 'baby', 'child-friendly'],
            'title_patterns': [r'family', r'kids', r'children', r'puppet', r'storytelling'],
            'priority': 9
        },
        'indoor_activities': {
            'keywords': ['mall', 'indoor', 'museum', 'gallery', 'center', 'centre', 'arcade', 'cinema', 'theater', 'aquarium', 'exhibition', 'shopping'],
            'title_patterns': [r'museum', r'gallery', r'mall', r'indoor', r'exhibition'],
            'priority': 8
        },
        'outdoor_activities': {
            'keywords': ['outdoor', 'adventure', 'safari', 'desert', 'beach', 'park', 'garden', 'hiking', 'nature', 'camping'],
            'title_patterns': [r'safari', r'desert', r'outdoor', r'adventure', r'hiking'],
            'priority': 8
        },
        'water_sports': {
            'keywords': ['jet ski', 'diving', 'snorkeling', 'boat', 'yacht', 'swimming', 'water park', 'beach', 'marina', 'sea', 'ocean'],
            'title_patterns': [r'jet ski', r'diving', r'yacht', r'boat', r'water'],
            'priority': 9
        },
        'cultural': {
            'keywords': ['heritage', 'traditional', 'cultural', 'history', 'mosque', 'souq', 'museum', 'art', 'calligraphy', 'arabic'],
            'title_patterns': [r'heritage', r'cultural', r'traditional', r'mosque', r'arabic'],
            'priority': 8
        },
        'music_and_concerts': {
            'keywords': ['concert', 'music', 'singer', 'band', 'orchestra', 'live music', 'acoustic', 'performance'],
            'title_patterns': [r'concert', r'live @', r'music', r'singer'],
            'priority': 7
        },
        'comedy_and_shows': {
            'keywords': ['comedy', 'comedian', 'stand-up', 'humor', 'show', 'performance', 'theater'],
            'title_patterns': [r'comedy', r'comedian', r'stand-up'],
            'priority': 7
        },
        'sports_and_fitness': {
            'keywords': ['sports', 'fitness', 'gym', 'yoga', 'running', 'cycling', 'basketball', 'football', 'tennis'],
            'title_patterns': [r'sports', r'fitness', r'yoga', r'running', r'basketball'],
            'priority': 7
        },
        'business_and_networking': {
            'keywords': ['business', 'networking', 'conference', 'seminar', 'workshop', 'professional', 'corporate', 'meeting'],
            'title_patterns': [r'conference', r'business', r'networking', r'professional'],
            'priority': 6
        },
        'tours_and_sightseeing': {
            'keywords': ['tour', 'sightseeing', 'abu dhabi', 'sharjah', 'excursion', 'day trip'],
            'title_patterns': [r'from dubai:', r'tour', r'abu dhabi', r'sightseeing'],
            'priority': 7
        },
        'festivals_and_celebrations': {
            'keywords': ['festival', 'celebration', 'eid', 'ramadan', 'national day', 'new year', 'christmas'],
            'title_patterns': [r'festival', r'celebration', r'eid', r'surprises'],
            'priority': 6
        }
    }
    
    # Tag generation rules
    tag_rules = {
        'family-friendly': ['family', 'kids', 'children', 'toddler'],
        'indoor': ['mall', 'museum', 'gallery', 'center', 'indoor', 'air-conditioned'],
        'outdoor': ['outdoor', 'beach', 'park', 'garden', 'desert', 'safari'],
        'free': ['free', 'complimentary', 'no charge'],
        'premium': ['vip', 'luxury', 'exclusive', 'premium', 'five-star'],
        'educational': ['workshop', 'learning', 'educational', 'seminar', 'conference'],
        'cultural': ['heritage', 'traditional', 'cultural', 'arabic', 'emirati'],
        'adventure': ['adventure', 'extreme', 'thrill', 'safari', 'climbing'],
        'relaxing': ['spa', 'wellness', 'peaceful', 'serene', 'calm'],
        'social': ['networking', 'meetup', 'community', 'social'],
        'weekend': ['weekend', 'friday', 'saturday', 'sunday'],
        'evening': ['evening', 'night', 'sunset', 'after dark'],
        'water-activities': ['water', 'swimming', 'diving', 'jet ski', 'boat', 'yacht'],
        'food': ['food', 'dining', 'restaurant', 'brunch', 'lunch', 'dinner'],
        'entertainment': ['show', 'performance', 'concert', 'comedy', 'theater']
    }
    
    # Get all events
    events = await db.events.find({"status": "active"}).to_list(length=None)
    print(f"Processing {len(events)} events...")
    
    updated_count = 0
    category_stats = {}
    
    for event in events:
        title = event.get('title', '').lower()
        description = event.get('description', '').lower()
        content = f"{title} {description}"
        
        # Determine best category
        best_category = None
        highest_priority = 0
        highest_score = 0
        
        for category, rules in category_rules.items():
            score = 0
            
            # Check keyword matches
            keyword_matches = sum(1 for keyword in rules['keywords'] if keyword in content)
            score += keyword_matches * 2
            
            # Check title pattern matches (higher weight)
            pattern_matches = sum(1 for pattern in rules['title_patterns'] if re.search(pattern, title))
            score += pattern_matches * 5
            
            # Apply priority weighting
            weighted_score = score * rules['priority']
            
            if weighted_score > highest_score or (weighted_score == highest_score and rules['priority'] > highest_priority):
                highest_score = weighted_score
                highest_priority = rules['priority']
                best_category = category
        
        # Generate tags
        generated_tags = []
        for tag, keywords in tag_rules.items():
            if any(keyword in content for keyword in keywords):
                generated_tags.append(tag)
        
        # Add price-based tags
        pricing = event.get('pricing', {})
        base_price = pricing.get('base_price', 0)
        if base_price == 0:
            generated_tags.append('free')
        elif base_price > 500:
            generated_tags.append('premium')
        elif base_price < 100:
            generated_tags.append('budget-friendly')
        
        # Update event if category or tags changed
        current_category = event.get('category', '')
        current_tags = event.get('tags', [])
        
        update_needed = False
        update_data = {}
        
        if best_category and best_category != current_category:
            update_data['category'] = best_category
            update_needed = True
        
        if generated_tags != current_tags:
            update_data['tags'] = generated_tags
            update_needed = True
        
        if update_needed:
            await db.events.update_one(
                {"_id": event["_id"]},
                {"$set": update_data}
            )
            updated_count += 1
            
            print(f"Updated: {event.get('title', 'Unknown')[:50]}")
            if 'category' in update_data:
                print(f"  Category: {current_category} → {best_category}")
            if 'tags' in update_data:
                print(f"  Tags: {generated_tags[:5]}...")  # Show first 5 tags
        
        # Track category stats
        final_category = best_category or current_category
        category_stats[final_category] = category_stats.get(final_category, 0) + 1
    
    print(f"\n✅ Updated {updated_count} events")
    print(f"\n📊 New Category Distribution:")
    print("=" * 50)
    
    for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(events)) * 100
        print(f"  {category}: {count} events ({percentage:.1f}%)")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(improve_categorization())