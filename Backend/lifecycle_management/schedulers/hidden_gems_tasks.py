from celery import current_app
from datetime import datetime, timedelta, date
import asyncio
import logging
import random
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from bson import ObjectId

logger = logging.getLogger(__name__)

# Get MongoDB client for tasks
def get_mongodb_client():
    client = AsyncIOMotorClient(
        settings.mongodb_url,
        tls=True,
        tlsAllowInvalidCertificates=True  # For development/testing
    )
    return client[settings.mongodb_database]

@current_app.task(bind=True, name='lifecycle_management.schedulers.hidden_gems_tasks.create_daily_hidden_gem')
def create_daily_hidden_gem(self, *args, **kwargs):
    """Create daily hidden gem with fallback logic"""
    async def run_gem_creation():
        try:
            mongodb = get_mongodb_client()
            
            # Check if today's gem already exists
            today = date.today()
            existing_gem = await mongodb.hidden_gems.find_one({
                "gem_date": {
                    "$gte": datetime.combine(today, datetime.min.time()),
                    "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
                }
            })
            
            if existing_gem:
                logger.info(f"Hidden gem already exists for today: {existing_gem.get('gem_title', 'Unknown')}")
                return {
                    "status": "already_exists",
                    "gem_title": existing_gem.get('gem_title', 'Unknown'),
                    "gem_id": existing_gem.get('gem_id', 'Unknown'),
                    "timestamp": datetime.now().isoformat(),
                    "task_id": self.request.id
                }
            
            # Try AI-powered creation first (if Perplexity API is available)
            try:
                from routers.hidden_gems import HiddenGemService
                service = HiddenGemService(mongodb)
                
                # Get all active events
                events_cursor = mongodb.events.find({"status": "active"})
                all_events = await events_cursor.to_list(length=None)
                
                # Get previous gems to avoid repetition
                previous_gems_cursor = service.collection.find(
                    {"gem_date": {"$gte": datetime.now() - timedelta(days=7)}},
                    {"gem_title": 1}
                )
                previous_gems_docs = await previous_gems_cursor.to_list(length=7)
                previous_gems = [doc.get("gem_title", "") for doc in previous_gems_docs]
                
                # Try AI creation
                gem_data = await service.discover_daily_gem_with_ai(all_events, previous_gems)
                hidden_gem = await service.save_hidden_gem(gem_data)
                
                logger.info(f"✨ AI-created daily hidden gem: {hidden_gem.gem_title}")
                return {
                    "status": "ai_created",
                    "gem_title": hidden_gem.gem_title,
                    "gem_id": hidden_gem.gem_id,
                    "event_id": hidden_gem.event_id,
                    "method": "perplexity_ai",
                    "timestamp": datetime.now().isoformat(),
                    "task_id": self.request.id
                }
                
            except Exception as ai_error:
                logger.warning(f"AI gem creation failed: {ai_error}. Falling back to manual creation.")
                
                # Fallback to manual creation
                gem_result = await create_fallback_hidden_gem(mongodb)
                
                if gem_result:
                    logger.info(f"🔮 Fallback gem created: {gem_result['gem_title']}")
                    return {
                        "status": "fallback_created",
                        "gem_title": gem_result['gem_title'],
                        "gem_id": gem_result['gem_id'],
                        "event_id": gem_result['event_id'],
                        "method": "fallback_algorithm",
                        "timestamp": datetime.now().isoformat(),
                        "task_id": self.request.id
                    }
                else:
                    raise Exception("Both AI and fallback creation failed")
            
        except Exception as e:
            logger.error(f"Daily hidden gem creation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_gem_creation())

async def create_fallback_hidden_gem(mongodb):
    """Create a hidden gem without AI when API is not available"""
    
    # Get a good selection of active events
    pipeline = [
        {
            "$match": {
                "status": "active"
            }
        },
        {
            "$sample": {"size": 100}  # Get larger sample for better selection
        }
    ]
    
    events = await mongodb.events.aggregate(pipeline).to_list(length=100)
    
    if not events:
        logger.error("No active events found for hidden gem creation")
        return None
    
    # Score and select the best event for a hidden gem
    scored_events = []
    for event in events:
        score = score_event_for_gem(event)
        if score > 0:  # Only consider events with positive score
            scored_events.append((event, score))
    
    if not scored_events:
        # If no events scored positively, just use the first available
        selected_event = events[0]
        logger.warning("No events scored positively, using first available event")
    else:
        # Sort by score and pick the best
        scored_events.sort(key=lambda x: x[1], reverse=True)
        selected_event = scored_events[0][0]
        logger.info(f"Selected event with score {scored_events[0][1]}: {selected_event.get('title', 'Unknown')}")
    
    # Generate compelling gem content
    gem_content = generate_gem_content(selected_event)
    
    # Insert into database
    await mongodb.hidden_gems.insert_one(gem_content)
    
    return {
        "gem_title": gem_content['gem_title'],
        "gem_id": gem_content['gem_id'],
        "event_id": gem_content['event_id']
    }

def score_event_for_gem(event):
    """Score an event for its suitability as a hidden gem"""
    score = 0
    title = event.get('title', '').lower()
    category = event.get('category', '').lower()
    venue_name = event.get('venue', {}).get('name', '').lower()
    area = event.get('venue', {}).get('area', '').lower()
    
    # Preferred categories and terms (higher score)
    preferred_terms = [
        'art', 'cultural', 'music', 'show', 'exhibition', 'workshop', 
        'rooftop', 'heritage', 'traditional', 'gallery', 'theater',
        'intimate', 'exclusive', 'private', 'boutique', 'hidden',
        'secret', 'local', 'authentic', 'unique', 'special'
    ]
    
    # Terms that make it less suitable for hidden gem (negative score)
    avoid_terms = [
        'mall', 'shopping center', 'festival city mall', 'emirates mall',
        'dubai mall', 'massive', 'huge', 'mega', 'commercial',
        'tourist trap', 'mainstream', 'popular'
    ]
    
    # Preferred areas (cultural districts)
    cultural_areas = [
        'al fahidi', 'bastakiya', 'al seef', 'la mer', 'city walk',
        'alserkal avenue', 'dubai design district', 'd3', 'business bay',
        'dubai marina', 'jumeirah', 'downtown', 'old dubai', 'deira'
    ]
    
    # Score based on preferred terms
    for term in preferred_terms:
        if term in title:
            score += 3
        if term in category:
            score += 2
        if term in venue_name:
            score += 2
    
    # Penalty for avoid terms
    for term in avoid_terms:
        if term in title or term in venue_name:
            score -= 5
    
    # Bonus for cultural areas
    for area_name in cultural_areas:
        if area_name in area:
            score += 2
    
    # Category-based scoring
    category_scores = {
        'cultural': 5,
        'arts': 5,
        'music_and_concerts': 4,
        'workshops': 4,
        'exhibitions': 4,
        'food_and_dining': 3,
        'outdoor_activities': 3,
        'indoor_activities': 2,
        'tours_and_sightseeing': 2
    }
    
    for cat, cat_score in category_scores.items():
        if cat in category:
            score += cat_score
    
    # Pricing consideration (not too expensive, not free)
    pricing = event.get('pricing', {})
    base_price = pricing.get('base_price', 0)
    if base_price:
        if 50 <= base_price <= 500:  # Sweet spot for hidden gems
            score += 2
        elif base_price > 1000:  # Too expensive
            score -= 3
    
    return score

def generate_gem_content(event):
    """Generate compelling hidden gem content for an event"""
    
    event_title = event.get('title', 'Mysterious Dubai Experience')
    venue_data = event.get('venue', {})
    venue_name = venue_data.get('name', 'Secret Location')
    area = venue_data.get('area', 'Dubai')
    category = event.get('category', 'cultural').replace('_', ' ').title()
    
    # Generate varied gem titles
    title_templates = [
        f"Exclusive {category} Discovery in {area}",
        f"Hidden {category} Gem of {area}",
        f"{area}'s Best-Kept {category} Secret",
        f"Intimate {category} Experience in {area}",
        f"Secret {category} Haven in {area}"
    ]
    
    # Generate varied taglines
    tagline_templates = [
        f"A hidden {category.lower()} gem that Dubai insiders cherish",
        f"An exclusive {category.lower()} experience most people never discover",
        f"The {category.lower()} secret that locals don't want tourists to find",
        f"A carefully guarded {category.lower()} treasure in {area}",
        f"Dubai's most authentic {category.lower()} experience"
    ]
    
    # Generate varied mystery teasers
    teaser_templates = [
        f"🎭 Step into {area}'s best-kept cultural secret. This {category.lower()} experience has been quietly enchanting locals who know where to look...",
        f"🔮 Hidden away in {area}, this {category.lower()} venue operates in plain sight yet remains invisible to the tourist crowds...",
        f"✨ Discover the {category.lower()} experience that {area} locals consider their most precious secret...",
        f"🎨 In the heart of {area}, a {category.lower()} gem awaits those who seek authentic Dubai experiences...",
        f"🌟 This {category.lower()} sanctuary in {area} has been nurturing culture lovers for years, away from mainstream attention..."
    ]
    
    # Randomly select templates for variety
    selected_title = random.choice(title_templates)
    selected_tagline = random.choice(tagline_templates)
    selected_teaser = random.choice(teaser_templates)
    
    # Generate gem ID
    gem_id = f"gem_{datetime.now().strftime('%Y%m%d')}_{str(event['_id'])[:8]}"
    
    return {
        'gem_id': gem_id,
        'event_id': str(event['_id']),
        'gem_title': selected_title,
        'gem_tagline': selected_tagline,
        'mystery_teaser': selected_teaser,
        'revealed_description': f"Discover {event_title} at {venue_name} - an authentic {category.lower()} experience that represents the true spirit of Dubai's cultural landscape. Away from tourist crowds, this venue offers genuine connection with the city's artistic soul.",
        'why_hidden_gem': f"This {category.lower()} venue in {area} operates under the radar, known primarily to cultural enthusiasts and locals who appreciate authentic experiences over commercial attractions.",
        'exclusivity_level': 'MEDIUM',
        'gem_category': f'{category} Discovery',
        'experience_level': 'Intimate',
        'best_for': ['culture_seekers', 'art_lovers', 'authentic_experiences', 'locals'],
        'gem_score': random.randint(75, 95),
        'scoring_breakdown': {
            'uniqueness': random.randint(7, 10),
            'exclusivity': random.randint(6, 9),
            'cultural_significance': random.randint(7, 10),
            'photo_opportunity': random.randint(6, 9),
            'insider_knowledge': random.randint(7, 10),
            'value_for_money': random.randint(6, 9)
        },
        'discovery_hints': [
            f'🏛️ Hidden in {area}',
            f'🎨 {category} enthusiasts\' sanctuary',
            '⭐ Known by cultural insiders',
            '📱 Minimal social media presence'
        ],
        'insider_tips': [
            'Arrive with an open mind and curious spirit',
            'Perfect opportunity for authentic photography',
            'Engage with locals for the full experience',
            'Check operating hours as they may vary'
        ],
        'gem_date': datetime.now(),
        'reveal_time': '12:00 PM UAE time',
        'expires_at': datetime.now() + timedelta(days=1),
        'reveal_count': 0,
        'share_count': 0,
        'event_details': {
            'title': event_title,
            'description': event.get('description', f'An exclusive {category.lower()} experience showcasing Dubai\'s authentic cultural side. Located in {area}, this venue offers intimate access to the city\'s artistic heritage.'),
            'date': event.get('start_date', 'Ongoing'),
            'time': 'Check venue for specific times',
            'location': f'{venue_name}, {area}',
            'price': f"AED {event.get('pricing', {}).get('base_price', 'Contact for pricing')}",
            'capacity': 'Limited - intimate setting',
            'highlights': [
                f'Authentic {category.lower()} experience',
                f'Located in cultural {area}',
                'Favored by local enthusiasts',
                'Intimate and personal setting',
                'Rich cultural immersion',
                'Photography opportunities'
            ],
            'what_to_bring': [
                'Camera for capturing memories',
                'Comfortable attire',
                'Curious and open mindset',
                'Respect for local culture'
            ],
            'booking_info': 'Contact venue directly or visit their official channels for reservations',
            'cancellation_policy': 'Please check with organizer for specific cancellation terms'
        }
    }

@current_app.task(bind=True, name='lifecycle_management.schedulers.hidden_gems_tasks.cleanup_expired_gems')
def cleanup_expired_gems(self, *args, **kwargs):
    """Clean up expired hidden gems to maintain database efficiency"""
    async def run_cleanup():
        try:
            mongodb = get_mongodb_client()
            
            # Find and remove gems older than 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            # Count expired gems first
            expired_count = await mongodb.hidden_gems.count_documents({
                "gem_date": {"$lt": cutoff_date}
            })
            
            if expired_count > 0:
                # Delete expired gems
                delete_result = await mongodb.hidden_gems.delete_many({
                    "gem_date": {"$lt": cutoff_date}
                })
                
                logger.info(f"Cleaned up {delete_result.deleted_count} expired hidden gems")
                
                return {
                    "status": "completed",
                    "expired_gems_removed": delete_result.deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "timestamp": datetime.now().isoformat(),
                    "task_id": self.request.id
                }
            else:
                logger.info("No expired hidden gems found")
                return {
                    "status": "no_action_needed",
                    "expired_gems_removed": 0,
                    "timestamp": datetime.now().isoformat(),
                    "task_id": self.request.id
                }
                
        except Exception as e:
            logger.error(f"Hidden gems cleanup failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": self.request.id
            }
    
    return asyncio.run(run_cleanup())