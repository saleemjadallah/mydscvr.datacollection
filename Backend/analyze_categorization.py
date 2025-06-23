#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from collections import Counter
import json

async def analyze_categorization():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]
    
    print("🔍 Analyzing Event Categorization & Tags...")
    print("=" * 60)
    
    # Get all active events
    events = await db.events.find({"status": "active"}).to_list(length=None)
    total_events = len(events)
    print(f"📊 Total active events: {total_events}")
    
    # Analyze current categories
    print(f"\n📂 Current Category Distribution:")
    print("=" * 50)
    
    categories = [event.get('category', 'No Category') for event in events]
    category_counts = Counter(categories)
    
    for category, count in category_counts.most_common():
        percentage = (count / total_events) * 100
        print(f"  {category}: {count} events ({percentage:.1f}%)")
    
    # Analyze tags
    print(f"\n🏷️ Current Tags Analysis:")
    print("=" * 50)
    
    all_tags = []
    events_with_tags = 0
    events_without_tags = 0
    
    for event in events:
        tags = event.get('tags', [])
        if tags and len(tags) > 0:
            all_tags.extend(tags)
            events_with_tags += 1
        else:
            events_without_tags += 1
    
    print(f"Events with tags: {events_with_tags}")
    print(f"Events without tags: {events_without_tags}")
    print(f"Total unique tags: {len(set(all_tags))}")
    
    if all_tags:
        tag_counts = Counter(all_tags)
        print(f"\nTop 15 most common tags:")
        for tag, count in tag_counts.most_common(15):
            print(f"  '{tag}': {count} events")
    
    # Analyze AI categories (if available)
    print(f"\n🤖 AI Categories Analysis:")
    print("=" * 50)
    
    ai_categories = []
    for event in events:
        ai_cats = event.get('categories', [])
        if ai_cats:
            ai_categories.extend(ai_cats)
    
    if ai_categories:
        ai_cat_counts = Counter(ai_categories)
        print(f"Total AI category assignments: {len(ai_categories)}")
        print(f"Unique AI categories: {len(set(ai_categories))}")
        print(f"\nTop AI categories:")
        for cat, count in ai_cat_counts.most_common(10):
            print(f"  '{cat}': {count} events")
    else:
        print("No AI categories found")
    
    # Analyze event titles and descriptions for potential categories
    print(f"\n🔍 Content Analysis for Missing Categories:")
    print("=" * 60)
    
    # Food & Dining keywords
    food_keywords = ['restaurant', 'brunch', 'dinner', 'lunch', 'food', 'dining', 'cuisine', 'chef', 'menu', 'buffet', 'iftar', 'feast']
    food_events = []
    
    # Indoor keywords  
    indoor_keywords = ['mall', 'indoor', 'museum', 'gallery', 'center', 'centre', 'arcade', 'cinema', 'theater', 'aquarium', 'exhibition']
    indoor_events = []
    
    # Kids & Family keywords
    family_keywords = ['kids', 'children', 'family', 'playground', 'edutainment', 'workshop', 'puppet', 'story', 'craft']
    family_events = []
    
    # Adventure/Outdoor keywords
    outdoor_keywords = ['outdoor', 'adventure', 'safari', 'desert', 'beach', 'park', 'garden', 'hiking', 'water', 'marina']
    outdoor_events = []
    
    for event in events:
        title = event.get('title', '').lower()
        description = event.get('description', '').lower()
        content = f"{title} {description}"
        
        # Check for food events
        if any(keyword in content for keyword in food_keywords):
            food_events.append({
                'title': event.get('title'),
                'category': event.get('category'),
                'matched_keywords': [kw for kw in food_keywords if kw in content]
            })
        
        # Check for indoor events
        if any(keyword in content for keyword in indoor_keywords):
            indoor_events.append({
                'title': event.get('title'),
                'category': event.get('category'),
                'matched_keywords': [kw for kw in indoor_keywords if kw in content]
            })
        
        # Check for family events
        if any(keyword in content for keyword in family_keywords):
            family_events.append({
                'title': event.get('title'),
                'category': event.get('category'),
                'matched_keywords': [kw for kw in family_keywords if kw in content]
            })
        
        # Check for outdoor events
        if any(keyword in content for keyword in outdoor_keywords):
            outdoor_events.append({
                'title': event.get('title'),
                'category': event.get('category'),
                'matched_keywords': [kw for kw in outdoor_keywords if kw in content]
            })
    
    print(f"\n🍽️ Potential FOOD & DINING events: {len(food_events)}")
    for i, event in enumerate(food_events[:5], 1):
        print(f"  {i}. {event['title'][:50]} (currently: {event['category']})")
        print(f"     Keywords: {event['matched_keywords']}")
    
    print(f"\n🏢 Potential INDOOR ACTIVITIES events: {len(indoor_events)}")
    for i, event in enumerate(indoor_events[:5], 1):
        print(f"  {i}. {event['title'][:50]} (currently: {event['category']})")
        print(f"     Keywords: {event['matched_keywords']}")
    
    print(f"\n👨‍👩‍👧‍👦 Potential KIDS & FAMILY events: {len(family_events)}")
    for i, event in enumerate(family_events[:5], 1):
        print(f"  {i}. {event['title'][:50]} (currently: {event['category']})")
        print(f"     Keywords: {event['matched_keywords']}")
    
    print(f"\n🌲 Potential OUTDOOR ACTIVITIES events: {len(outdoor_events)}")
    for i, event in enumerate(outdoor_events[:5], 1):
        print(f"  {i}. {event['title'][:50]} (currently: {event['category']})")
        print(f"     Keywords: {event['matched_keywords']}")
    
    # Sample events with poor categorization
    print(f"\n❌ Events with Generic Categories:")
    print("=" * 50)
    
    generic_categories = ['general', 'event', 'entertainment', 'activities']
    generic_events = [e for e in events if e.get('category', '').lower() in generic_categories]
    
    for i, event in enumerate(generic_events[:5], 1):
        print(f"  {i}. {event.get('title', 'Unknown')[:50]}")
        print(f"     Current category: {event.get('category', 'None')}")
        print(f"     Description: {event.get('description', '')[:100]}...")
        print()
    
    client.close()

if __name__ == "__main__":
    asyncio.run(analyze_categorization())