#!/usr/bin/env python3
"""
Enhanced AI-Powered Event Categorization & Tagging System
Uses more sophisticated pattern matching and contextual analysis
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import re
import json
from typing import List, Dict, Set

async def enhanced_categorization():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]
    
    print("🚀 Enhanced AI-Powered Event Categorization...")
    print("=" * 60)
    
    # Enhanced categorization rules with more comprehensive patterns
    category_rules = {
        'food_and_dining': {
            'keywords': [
                # Core dining terms
                'brunch', 'dinner', 'lunch', 'breakfast', 'restaurant', 'food', 'dining', 'cuisine', 'chef', 'menu', 'buffet',
                'iftar', 'feast', 'culinary', 'cooking', 'kitchen', 'cafe', 'bistro', 'eatery', 'gastropub',
                # Brunch-specific terms (Dubai favorites)
                'bottomless brunch', 'weekend brunch', 'friday brunch', 'saturday brunch', 'sunday brunch', 
                'unlimited drinks', 'brunch deal', 'brunch special', 'morning brunch', 'late brunch',
                'boozy brunch', 'champagne brunch', 'prosecco brunch', 'mimosas', 'bloody mary',
                # Specific food types
                'pizza', 'sushi', 'steak', 'seafood', 'bbq', 'barbecue', 'grill', 'roast', 'curry', 'pasta', 'burger',
                'sandwich', 'salad', 'soup', 'dessert', 'cake', 'chocolate', 'coffee', 'tea', 'wine', 'cocktail',
                # Dining experiences
                'tasting', 'degustation', 'food festival', 'food truck', 'pop-up', 'michelin', 'fine dining',
                'food court', 'market', 'street food', 'local cuisine', 'international cuisine', 'authentic',
                # Venue types
                'kailash parbat', 'moundoux', 'firelake', 'zeta', 'deep south', 'funny cat'
            ],
            'title_patterns': [
                r'brunch', r'restaurant', r'food', r'dining', r'culinary', r'kitchen', r'cafe', r'bistro',
                r'tasting', r'feast', r'breakfast', r'lunch', r'dinner', r'iftar', r'buffet', r'menu',
                r'chef', r'cooking', r'grill', r'bbq', r'pizza', r'sushi', r'curry', r'wine', r'cocktail'
            ],
            'venue_patterns': [
                r'restaurant', r'cafe', r'bistro', r'kitchen', r'grill', r'bar', r'lounge', r'eatery'
            ],
            'priority': 10
        },
        'indoor_activities': {
            'keywords': [
                # Venue types
                'mall', 'indoor', 'museum', 'gallery', 'center', 'centre', 'arcade', 'cinema', 'theater', 'theatre',
                'aquarium', 'exhibition', 'shopping', 'air-conditioned', 'inside', 'covered',
                # Specific venues
                'dubai mall', 'mall of emirates', 'city centre', 'ibn battuta', 'dubai festival city',
                'world trade centre', 'expo city', 'museum of future', 'green planet', 'dubai aquarium',
                'burj khalifa', 'at the top', 'observation deck',
                # Activities
                'workshop', 'class', 'seminar', 'conference', 'meeting', 'presentation', 'training',
                'escape room', 'bowling', 'ice skating', 'gaming', 'arcade', 'cinema', 'movie',
                'spa', 'wellness', 'massage', 'beauty', 'salon', 'gym', 'fitness center',
                # Art & culture
                'art exhibition', 'gallery', 'painting', 'sculpture', 'photography', 'installation',
                'fashion show', 'runway', 'design', 'creative', 'craft', 'pottery', 'workshop'
            ],
            'title_patterns': [
                r'mall', r'museum', r'gallery', r'indoor', r'exhibition', r'center', r'centre',
                r'workshop', r'class', r'cinema', r'theater', r'spa', r'wellness', r'gym',
                r'art', r'design', r'creative', r'craft', r'fashion', r'shopping'
            ],
            'venue_patterns': [
                r'mall', r'museum', r'gallery', r'center', r'centre', r'cinema', r'theater', r'spa'
            ],
            'priority': 9
        },
        'kids_and_family': {
            'keywords': [
                'family', 'kids', 'children', 'playground', 'edutainment', 'workshop', 'puppet', 'story', 'craft', 
                'toddler', 'baby', 'child-friendly', 'petting zoo', 'animal farm', 'camel rides', 'pony',
                'bounce', 'trampoline', 'play area', 'soft play', 'jungle gym', 'slides', 'swings',
                'educational', 'learning', 'science', 'discovery', 'curiosity lab', 'kidzania',
                'magic show', 'puppet show', 'storytelling', 'face painting', 'balloon', 'clown',
                'theme park', 'legoland', 'img worlds', 'motiongate', 'bollywood parks'
            ],
            'title_patterns': [
                r'family', r'kids', r'children', r'puppet', r'storytelling', r'playground', r'play area',
                r'educational', r'learning', r'discovery', r'magic', r'balloon', r'theme park'
            ],
            'priority': 9
        },
        'outdoor_activities': {
            'keywords': [
                'outdoor', 'adventure', 'safari', 'desert', 'beach', 'park', 'garden', 'hiking', 'nature', 'camping',
                'kite beach', 'jumeirah beach', 'la mer', 'marina beach', 'jbr beach', 'sunset beach',
                'al mamzar', 'zabeel park', 'creek park', 'safa park', 'miracle garden', 'butterfly garden',
                'dubai fountain', 'burj park', 'marina walk', 'the walk', 'boardwalk', 'promenade',
                'cycling', 'jogging', 'running', 'walking', 'picnic', 'bbq', 'barbecue', 'outdoor dining',
                'rooftop', 'terrace', 'balcony', 'open air', 'al fresco', 'under the stars'
            ],
            'title_patterns': [
                r'safari', r'desert', r'outdoor', r'adventure', r'hiking', r'beach', r'park', r'garden',
                r'rooftop', r'terrace', r'open air', r'al fresco', r'cycling', r'running', r'picnic'
            ],
            'priority': 8
        },
        'water_sports': {
            'keywords': [
                'jet ski', 'diving', 'snorkeling', 'boat', 'yacht', 'swimming', 'water park', 'beach', 'marina', 
                'sea', 'ocean', 'aquaventure', 'wild wadi', 'laguna', 'splash pad', 'pool', 'infinity pool',
                'kayak', 'paddle', 'surfing', 'sailing', 'fishing', 'dhow', 'cruise', 'catamaran',
                'underwater', 'scuba', 'snorkel', 'submarine', 'glass bottom boat', 'dolphin', 'whale watching'
            ],
            'title_patterns': [
                r'jet ski', r'diving', r'yacht', r'boat', r'water', r'pool', r'swimming', r'cruise',
                r'sailing', r'fishing', r'aquaventure', r'splash', r'marina', r'dhow'
            ],
            'priority': 9
        },
        'cultural': {
            'keywords': [
                'heritage', 'traditional', 'cultural', 'history', 'mosque', 'souq', 'museum', 'art', 'calligraphy', 
                'arabic', 'emirati', 'uae', 'bedouin', 'pearl diving', 'falconry', 'henna', 'oud', 'dabke',
                'al seef', 'old dubai', 'heritage village', 'bastakia', 'shindagha', 'al fahidi',
                'ramadan', 'eid', 'national day', 'flag day', 'commemoration day', 'spirit of union',
                'silk road', 'china pavilion', 'expo', 'international', 'embassy', 'consulate'
            ],
            'title_patterns': [
                r'heritage', r'cultural', r'traditional', r'mosque', r'arabic', r'emirati', r'ramadan', r'eid',
                r'national day', r'silk road', r'china pavilion', r'al seef', r'old dubai'
            ],
            'priority': 8
        },
        'music_and_concerts': {
            'keywords': [
                'concert', 'music', 'singer', 'band', 'orchestra', 'live music', 'acoustic', 'performance',
                'tribute', 'adele', 'coldplay', 'queen', 'abba', 'metro boomin', 'dj', 'festival',
                'opera', 'symphony', 'jazz', 'rock', 'pop', 'classical', 'world music', 'arabic music',
                'oud', 'piano', 'violin', 'guitar', 'drums', 'vocals', 'choir', 'ensemble'
            ],
            'title_patterns': [
                r'concert', r'live', r'music', r'singer', r'tribute', r'opera', r'symphony', r'festival',
                r'acoustic', r'piano', r'jazz', r'rock', r'pop', r'classical'
            ],
            'priority': 8
        },
        'comedy_and_shows': {
            'keywords': [
                'comedy', 'comedian', 'stand-up', 'humor', 'show', 'performance', 'theater', 'theatre',
                'la perle', 'dragone', 'acrobatics', 'circus', 'magic', 'illusion', 'variety show',
                'cabaret', 'entertainment', 'live show', 'stage', 'drama', 'musical', 'broadway'
            ],
            'title_patterns': [
                r'comedy', r'comedian', r'stand-up', r'la perle', r'show', r'performance', r'theater',
                r'magic', r'circus', r'cabaret', r'musical', r'broadway'
            ],
            'priority': 7
        },
        'sports_and_fitness': {
            'keywords': [
                'sports', 'fitness', 'gym', 'yoga', 'running', 'cycling', 'basketball', 'football', 'tennis',
                'golf', 'swimming', 'marathon', 'triathlon', 'crossfit', 'pilates', 'zumba', 'aerobics',
                'martial arts', 'boxing', 'mma', '971 fighting', 'wrestling', 'judo', 'karate',
                'cricket', 'rugby', 'volleyball', 'badminton', 'squash', 'table tennis', 'bowling'
            ],
            'title_patterns': [
                r'sports', r'fitness', r'yoga', r'running', r'basketball', r'football', r'tennis', r'golf',
                r'marathon', r'gym', r'crossfit', r'boxing', r'mma', r'cricket', r'rugby'
            ],
            'priority': 7
        },
        'business_and_networking': {
            'keywords': [
                'business', 'networking', 'conference', 'seminar', 'workshop', 'professional', 'corporate', 
                'meeting', 'summit', 'forum', 'symposium', 'expo', 'trade show', 'exhibition',
                'leadership', 'entrepreneurship', 'startup', 'innovation', 'technology', 'digital',
                'finance', 'investment', 'real estate', 'marketing', 'sales', 'hr', 'management'
            ],
            'title_patterns': [
                r'conference', r'business', r'networking', r'professional', r'summit', r'forum',
                r'expo', r'trade show', r'leadership', r'startup', r'innovation'
            ],
            'priority': 6
        },
        'tours_and_sightseeing': {
            'keywords': [
                'tour', 'sightseeing', 'abu dhabi', 'sharjah', 'fujairah', 'ras al khaimah', 'ajman',
                'excursion', 'day trip', 'guided tour', 'city tour', 'hop on hop off', 'bus tour',
                'walking tour', 'helicopter tour', 'seaplane', 'balloon', 'burj khalifa', 'burj al arab',
                'palm jumeirah', 'atlantis', 'ferrari world', 'yas island', 'louvre', 'sheikh zayed mosque'
            ],
            'title_patterns': [
                r'from dubai', r'tour', r'abu dhabi', r'sightseeing', r'city tour', r'guided',
                r'excursion', r'day trip', r'helicopter', r'balloon'
            ],
            'priority': 7
        },
        'festivals_and_celebrations': {
            'keywords': [
                'festival', 'celebration', 'eid', 'ramadan', 'national day', 'new year', 'christmas',
                'dubai shopping festival', 'dubai summer surprises', 'dss', 'dsf', 'global village',
                'carnival', 'parade', 'fireworks', 'light show', 'drone show', 'fountain show'
            ],
            'title_patterns': [
                r'festival', r'celebration', r'eid', r'surprises', r'dsf', r'dss', r'global village',
                r'carnival', r'fireworks', r'light show', r'drone'
            ],
            'priority': 6
        }
    }
    
    # Enhanced tag generation with contextual analysis
    enhanced_tag_rules = {
        # Venue-based tags
        'mall-event': ['mall', 'shopping center', 'dubai mall', 'emirates mall', 'city centre'],
        'hotel-event': ['hotel', 'resort', 'spa', 'ritz carlton', 'burj al arab', 'atlantis', 'jumeirah'],
        'beach-event': ['beach', 'seaside', 'waterfront', 'marina', 'corniche', 'boardwalk'],
        'rooftop-event': ['rooftop', 'terrace', 'sky', 'panoramic', 'view', 'overlooking'],
        
        # Experience-based tags
        'family-friendly': ['family', 'kids', 'children', 'toddler', 'baby', 'child-friendly', 'all ages'],
        'adults-only': ['adults only', '18+', '21+', 'mature', 'sophisticated', 'exclusive'],
        'romantic': ['romantic', 'couples', 'date night', 'intimate', 'candlelight', 'sunset'],
        'group-activity': ['group', 'team', 'friends', 'social', 'networking', 'community'],
        
        # Time-based tags
        'morning-event': ['morning', 'sunrise', 'breakfast', 'early', 'dawn'],
        'afternoon-event': ['afternoon', 'lunch', 'midday', 'noon'],
        'evening-event': ['evening', 'dinner', 'sunset', 'dusk', 'night'],
        'weekend-event': ['weekend', 'friday', 'saturday', 'sunday'],
        
        # Activity-based tags
        'educational': ['workshop', 'learning', 'educational', 'seminar', 'training', 'course'],
        'entertainment': ['show', 'performance', 'concert', 'comedy', 'theater', 'music'],
        'adventure': ['adventure', 'extreme', 'thrill', 'adrenaline', 'exciting'],
        'relaxing': ['spa', 'wellness', 'peaceful', 'serene', 'calm', 'meditation', 'yoga'],
        'cultural': ['heritage', 'traditional', 'cultural', 'arabic', 'emirati', 'historical'],
        'luxury': ['luxury', 'premium', 'exclusive', 'vip', 'five-star', 'high-end'],
        
        # Food & Dining specific tags
        'brunch-event': ['brunch', 'bottomless brunch', 'weekend brunch', 'friday brunch', 'saturday brunch', 'sunday brunch'],
        'brunch': ['brunch', 'bottomless brunch', 'weekend brunch', 'friday brunch', 'saturday brunch', 'sunday brunch'],
        'dinner-event': ['dinner', 'evening meal', 'supper'],
        'buffet-event': ['buffet', 'all you can eat', 'unlimited'],
        'fine-dining': ['fine dining', 'michelin', 'gourmet', 'chef', 'tasting menu'],
        'casual-dining': ['casual', 'bistro', 'cafe', 'pub', 'street food'],
        
        # Indoor activity specific tags
        'air-conditioned': ['indoor', 'air-conditioned', 'climate controlled', 'covered'],
        'hands-on': ['workshop', 'interactive', 'hands-on', 'diy', 'craft'],
        'tech-event': ['technology', 'digital', 'vr', 'ar', 'gaming', 'esports'],
        'wellness-event': ['spa', 'massage', 'beauty', 'health', 'wellness', 'fitness'],
        
        # Price-based tags
        'free-event': ['free', 'complimentary', 'no charge', 'no cost', 'gratis'],
        'budget-friendly': ['affordable', 'budget', 'cheap', 'economical', 'reasonable'],
        'premium-event': ['expensive', 'luxury', 'premium', 'exclusive', 'high-end']
    }
    
    # Get all events
    events = await db.events.find({"status": "active"}).to_list(length=None)
    print(f"Processing {len(events)} events with enhanced AI categorization...")
    
    updated_count = 0
    category_stats = {}
    tag_stats = {}
    
    for event in events:
        title = event.get('title', '').lower()
        description = event.get('description', '').lower()
        venue_name = event.get('venue', {}).get('name', '').lower()
        area = event.get('venue', {}).get('area', '').lower()
        
        # Combine all text for analysis
        full_content = f"{title} {description} {venue_name} {area}"
        
        # Enhanced category detection
        best_category = None
        highest_score = 0
        category_matches = {}
        
        for category, rules in category_rules.items():
            score = 0
            matches = []
            
            # Keyword matching with context awareness
            for keyword in rules['keywords']:
                if keyword in full_content:
                    # Give higher weight to title matches
                    if keyword in title:
                        score += 5
                        matches.append(f"title:{keyword}")
                    # Medium weight for venue matches
                    elif keyword in venue_name:
                        score += 3
                        matches.append(f"venue:{keyword}")
                    # Lower weight for description matches
                    elif keyword in description:
                        score += 2
                        matches.append(f"desc:{keyword}")
                    else:
                        score += 1
                        matches.append(f"area:{keyword}")
            
            # Pattern matching with higher weights
            for pattern in rules['title_patterns']:
                if re.search(pattern, title):
                    score += 8
                    matches.append(f"pattern:{pattern}")
            
            # Venue pattern matching
            if 'venue_patterns' in rules:
                for pattern in rules['venue_patterns']:
                    if re.search(pattern, venue_name):
                        score += 6
                        matches.append(f"venue_pattern:{pattern}")
            
            # Apply priority weighting
            final_score = score * rules['priority']
            category_matches[category] = {
                'score': final_score,
                'raw_score': score,
                'matches': matches
            }
            
            if final_score > highest_score:
                highest_score = final_score
                best_category = category
        
        # Enhanced tag generation
        generated_tags = set()
        
        for tag, keywords in enhanced_tag_rules.items():
            matches = [keyword for keyword in keywords if keyword in full_content]
            if matches:
                generated_tags.add(tag)
                # Add specific matches as additional tags
                for match in matches[:2]:  # Limit to avoid tag explosion
                    if len(match.split()) == 1 and len(match) > 3:  # Single meaningful words
                        generated_tags.add(match.replace(' ', '-'))
        
        # Smart pricing analysis
        pricing = event.get('pricing', {})
        base_price = pricing.get('base_price', 0)
        
        if base_price == 0:
            generated_tags.add('free')
            generated_tags.add('free-event')
        elif base_price > 1000:
            generated_tags.add('luxury')
            generated_tags.add('premium-event')
        elif base_price > 500:
            generated_tags.add('premium')
        elif base_price < 100:
            generated_tags.add('budget-friendly')
        
        # Time-based tag analysis
        start_date = event.get('start_date')
        if start_date:
            hour = start_date.hour if hasattr(start_date, 'hour') else 12
            if 6 <= hour < 12:
                generated_tags.add('morning-event')
            elif 12 <= hour < 17:
                generated_tags.add('afternoon-event')
            elif hour >= 17:
                generated_tags.add('evening-event')
        
        # Convert tags set to sorted list
        generated_tags = sorted(list(generated_tags))
        
        # Update event if changes detected
        current_category = event.get('category', '')
        current_tags = event.get('tags', [])
        
        update_needed = False
        update_data = {}
        
        if best_category and best_category != current_category:
            update_data['category'] = best_category
            update_needed = True
        
        if set(generated_tags) != set(current_tags):
            update_data['tags'] = generated_tags
            update_needed = True
        
        if update_needed:
            await db.events.update_one(
                {"_id": event["_id"]},
                {"$set": update_data}
            )
            updated_count += 1
            
            event_title = event.get('title', 'Unknown')[:60]
            print(f"Updated: {event_title}")
            if 'category' in update_data:
                print(f"  Category: {current_category or 'none'} → {best_category}")
                if best_category in category_matches:
                    matches = category_matches[best_category]['matches'][:3]
                    print(f"  Matches: {matches}")
            if 'tags' in update_data:
                new_tag_count = len(generated_tags)
                print(f"  Tags: {new_tag_count} tags ({generated_tags[:5]}{'...' if new_tag_count > 5 else ''})")
        
        # Track statistics
        final_category = best_category or current_category or 'uncategorized'
        category_stats[final_category] = category_stats.get(final_category, 0) + 1
        
        for tag in generated_tags:
            tag_stats[tag] = tag_stats.get(tag, 0) + 1
    
    # Print comprehensive results
    print(f"\n✅ Enhanced AI Categorization Complete!")
    print(f"Updated {updated_count} events out of {len(events)} total")
    print("=" * 80)
    
    print(f"\n📊 New Category Distribution:")
    print("-" * 50)
    for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(events)) * 100
        print(f"  {category:<25}: {count:>3} events ({percentage:>5.1f}%)")
    
    print(f"\n🏷️  Most Common Tags:")
    print("-" * 50)
    top_tags = sorted(tag_stats.items(), key=lambda x: x[1], reverse=True)[:20]
    for tag, count in top_tags:
        percentage = (count / len(events)) * 100
        print(f"  {tag:<25}: {count:>3} events ({percentage:>5.1f}%)")
    
    client.close()
    print(f"\n🎉 Enhanced categorization complete! Food & dining and indoor activities should now be properly detected.")

if __name__ == "__main__":
    asyncio.run(enhanced_categorization())