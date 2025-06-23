#!/usr/bin/env python3
"""
One-time script to enhance existing events collection with social media, event URLs, 
and other advanced fields using our enhanced Perplexity extraction code.

This script will:
1. Fetch existing events from MongoDB that lack enhanced fields
2. Use Perplexity AI to extract social media, event URLs, and advanced metadata
3. Update the existing events with the new enhanced fields
4. Preserve all existing event data while adding new fields
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pymongo import MongoClient
from bson import ObjectId
from loguru import logger
from dotenv import load_dotenv

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Backend'))

# Import our enhanced extraction system
from perplexity_events_extractor import DubaiEventsPerplexityExtractor

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'Mongo.env'))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'AI_API.env'))

class ExistingEventsEnhancer:
    """
    One-time enhancement tool for existing events collection
    """
    
    def __init__(self):
        # MongoDB connection
        self.mongodb_uri = os.getenv('Mongo_URI')
        self.database_name = os.getenv('MONGO_DB_NAME', 'DXB')
        
        if not self.mongodb_uri:
            raise ValueError("MongoDB URI not found. Set Mongo_URI in Mongo.env file.")
        
        # Connect to MongoDB
        self.client = MongoClient(
            self.mongodb_uri,
            serverSelectionTimeoutMS=5000,
            tlsInsecure=True
        )
        
        # Test connection
        self.client.admin.command('ping')
        
        self.db = self.client[self.database_name]
        self.events_collection = self.db['events']
        
        # Initialize enhanced extractor
        self.extractor = DubaiEventsPerplexityExtractor()
        
        # Statistics tracking
        self.stats = {
            "total_events": 0,
            "events_needing_enhancement": 0,
            "successfully_enhanced": 0,
            "failed_enhancements": 0,
            "skipped_events": 0,
            "start_time": datetime.now()
        }
        
        logger.info(f"✅ Connected to MongoDB: {self.database_name}")
        logger.info(f"✅ Enhanced extractor initialized")
    
    def get_events_needing_enhancement(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get existing events that lack enhanced fields
        """
        # Query for events that don't have enhanced fields
        query = {
            "$or": [
                {"social_media": {"$exists": False}},
                {"event_url": {"$exists": False}},
                {"quality_metrics": {"$exists": False}},
                {"target_audience": {"$exists": False}},
                {"venue_type": {"$exists": False}}
            ],
            # Only enhance events that are not too old (within last 6 months or future events)
            "start_date": {"$gte": datetime.now() - timedelta(days=180)}
        }
        
        # Count total events needing enhancement
        total_count = self.events_collection.count_documents(query)
        logger.info(f"📊 Found {total_count} events needing enhancement")
        
        # Fetch events
        cursor = self.events_collection.find(query).sort("start_date", 1)
        if limit:
            cursor = cursor.limit(limit)
        
        events = list(cursor)
        logger.info(f"📋 Retrieved {len(events)} events for enhancement")
        
        self.stats["total_events"] = total_count
        self.stats["events_needing_enhancement"] = len(events)
        
        return events
    
    def create_enhancement_query(self, event: Dict[str, Any]) -> str:
        """
        Create a targeted query for enhancing a specific event
        """
        title = event.get("title", "")
        venue_name = event.get("venue", {}).get("name", "")
        area = event.get("venue", {}).get("area", "Dubai")
        start_date = event.get("start_date")
        
        # Format date for search
        date_str = ""
        if start_date:
            if isinstance(start_date, datetime):
                date_str = start_date.strftime("%B %Y")
            elif isinstance(start_date, str):
                try:
                    parsed_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    date_str = parsed_date.strftime("%B %Y")
                except:
                    date_str = ""
        
        # Create comprehensive search query
        query_parts = [f'"{title}"']
        
        if venue_name and venue_name != "TBA":
            query_parts.append(f'"{venue_name}"')
        
        if area:
            query_parts.append(area)
        
        if date_str:
            query_parts.append(date_str)
        
        # Add Dubai context
        query_parts.append("Dubai event")
        
        query = " ".join(query_parts)
        logger.debug(f"🔍 Created enhancement query: {query}")
        
        return query
    
    async def enhance_single_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Enhance a single event with Perplexity AI
        """
        try:
            event_id = str(event.get("_id"))
            title = event.get("title", "Unknown Event")
            
            logger.info(f"🔄 Enhancing event: {title}")
            
            # Create targeted search query
            search_query = self.create_enhancement_query(event)
            
            # Use our enhanced extractor to get additional fields
            extraction_result = await self.extractor.search_and_extract_events(search_query)
            extracted_events = extraction_result.get('events', [])
            
            if not extracted_events:
                logger.warning(f"⚠️ No enhancement data found for: {title}")
                return None
            
            # Find the best match based on title similarity
            best_match = None
            best_score = 0
            
            for extracted_event in extracted_events:
                extracted_title = extracted_event.get("title", "").lower()
                original_title = title.lower()
                
                # Simple similarity scoring based on common words
                original_words = set(original_title.split())
                extracted_words = set(extracted_title.split())
                
                if original_words and extracted_words:
                    similarity = len(original_words & extracted_words) / len(original_words | extracted_words)
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = extracted_event
            
            # Use the best match if similarity is reasonable, otherwise use first result
            enhancement_data = best_match if best_score > 0.3 else extracted_events[0]
            
            # Extract only the enhanced fields we want to add
            enhanced_fields = {}
            
            # Social media links
            if enhancement_data.get("social_media"):
                enhanced_fields["social_media"] = enhancement_data["social_media"]
            
            # Event URL
            if enhancement_data.get("event_url"):
                enhanced_fields["event_url"] = enhancement_data["event_url"]
            
            # Quality metrics
            if enhancement_data.get("quality_metrics"):
                enhanced_fields["quality_metrics"] = enhancement_data["quality_metrics"]
            
            # Target audience
            if enhancement_data.get("target_audience"):
                enhanced_fields["target_audience"] = enhancement_data["target_audience"]
            
            # Venue type
            if enhancement_data.get("venue_type"):
                enhanced_fields["venue_type"] = enhancement_data["venue_type"]
            
            # Age restrictions
            if enhancement_data.get("age_restrictions"):
                enhanced_fields["age_restrictions"] = enhancement_data["age_restrictions"]
            
            # Dress code
            if enhancement_data.get("dress_code"):
                enhanced_fields["dress_code"] = enhancement_data["dress_code"]
            
            # Transportation notes
            if enhancement_data.get("transportation_notes"):
                enhanced_fields["transportation_notes"] = enhancement_data["transportation_notes"]
            
            # Contact info
            if enhancement_data.get("contact_info"):
                enhanced_fields["contact_info"] = enhancement_data["contact_info"]
            
            # Ticket links
            if enhancement_data.get("ticket_links"):
                enhanced_fields["ticket_links"] = enhancement_data["ticket_links"]
            
            # Additional categorization
            if enhancement_data.get("primary_category"):
                enhanced_fields["primary_category"] = enhancement_data["primary_category"]
            
            if enhancement_data.get("secondary_categories"):
                enhanced_fields["secondary_categories"] = enhancement_data["secondary_categories"]
            
            if enhancement_data.get("event_type"):
                enhanced_fields["event_type"] = enhancement_data["event_type"]
            
            if enhancement_data.get("indoor_outdoor"):
                enhanced_fields["indoor_outdoor"] = enhancement_data["indoor_outdoor"]
            
            # Metro accessibility
            if enhancement_data.get("metro_accessible") is not None:
                enhanced_fields["metro_accessible"] = enhancement_data["metro_accessible"]
            
            # Special needs friendly
            if enhancement_data.get("special_needs_friendly") is not None:
                enhanced_fields["special_needs_friendly"] = enhancement_data["special_needs_friendly"]
            
            # Language requirements
            if enhancement_data.get("language_requirements"):
                enhanced_fields["language_requirements"] = enhancement_data["language_requirements"]
            
            # Alcohol served
            if enhancement_data.get("alcohol_served") is not None:
                enhanced_fields["alcohol_served"] = enhancement_data["alcohol_served"]
            
            # Special occasion
            if enhancement_data.get("special_occasion"):
                enhanced_fields["special_occasion"] = enhancement_data["special_occasion"]
            
            # Recurring event
            if enhancement_data.get("recurring") is not None:
                enhanced_fields["recurring"] = enhancement_data["recurring"]
            
            if enhanced_fields:
                # Add enhancement metadata
                enhanced_fields["enhancement_metadata"] = {
                    "enhanced_at": datetime.now(),
                    "enhancement_source": "perplexity_retrospective",
                    "enhancement_query": search_query,
                    "similarity_score": best_score,
                    "fields_added": list(enhanced_fields.keys())
                }
                
                logger.info(f"✅ Enhanced '{title}' with {len(enhanced_fields)} new fields")
                return enhanced_fields
            else:
                logger.warning(f"⚠️ No useful enhancement data extracted for: {title}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error enhancing event '{title}': {e}")
            return None
    
    async def update_event_in_database(self, event_id: ObjectId, enhanced_fields: Dict[str, Any]) -> bool:
        """
        Update an event in the database with enhanced fields
        """
        try:
            # Prepare update query
            update_query = {
                "$set": {
                    **enhanced_fields,
                    "updated_at": datetime.now()
                }
            }
            
            # Update the event
            result = self.events_collection.update_one(
                {"_id": event_id},
                update_query
            )
            
            if result.modified_count > 0:
                logger.info(f"💾 Successfully updated event in database")
                return True
            else:
                logger.warning(f"⚠️ No changes made to event in database")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating event in database: {e}")
            return False
    
    async def enhance_events_batch(self, events: List[Dict[str, Any]], batch_size: int = 5) -> None:
        """
        Enhance events in batches to avoid rate limiting
        """
        total_events = len(events)
        
        for i in range(0, total_events, batch_size):
            batch = events[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_events + batch_size - 1) // batch_size
            
            logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} events)")
            
            # Process events in parallel within the batch
            batch_tasks = []
            for event in batch:
                task = self.enhance_single_event(event)
                batch_tasks.append((event, task))
            
            # Wait for all events in the batch to be enhanced
            for event, task in batch_tasks:
                try:
                    enhanced_fields = await task
                    
                    if enhanced_fields:
                        # Update the event in database
                        success = await self.update_event_in_database(
                            event["_id"], 
                            enhanced_fields
                        )
                        
                        if success:
                            self.stats["successfully_enhanced"] += 1
                        else:
                            self.stats["failed_enhancements"] += 1
                    else:
                        self.stats["skipped_events"] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error processing event: {e}")
                    self.stats["failed_enhancements"] += 1
            
            # Rate limiting - wait between batches
            if i + batch_size < total_events:
                logger.info(f"⏳ Waiting 30 seconds before next batch...")
                await asyncio.sleep(30)
    
    def print_final_stats(self):
        """
        Print final enhancement statistics
        """
        duration = datetime.now() - self.stats["start_time"]
        
        logger.info("=" * 50)
        logger.info("📊 ENHANCEMENT COMPLETED!")
        logger.info("=" * 50)
        logger.info(f"⏱️  Duration: {duration}")
        logger.info(f"📈 Total events in collection: {self.stats['total_events']}")
        logger.info(f"🎯 Events needing enhancement: {self.stats['events_needing_enhancement']}")
        logger.info(f"✅ Successfully enhanced: {self.stats['successfully_enhanced']}")
        logger.info(f"❌ Failed enhancements: {self.stats['failed_enhancements']}")
        logger.info(f"⏭️  Skipped events: {self.stats['skipped_events']}")
        
        if self.stats["events_needing_enhancement"] > 0:
            success_rate = (self.stats["successfully_enhanced"] / self.stats["events_needing_enhancement"]) * 100
            logger.info(f"📊 Success rate: {success_rate:.1f}%")
        
        logger.info("=" * 50)
    
    async def run_enhancement(self, limit: Optional[int] = None, batch_size: int = 5):
        """
        Main method to run the enhancement process
        """
        try:
            logger.info("🚀 Starting existing events enhancement...")
            
            # Get events that need enhancement
            events = self.get_events_needing_enhancement(limit=limit)
            
            if not events:
                logger.info("✅ No events need enhancement. All events are already enhanced!")
                return
            
            # Enhance events in batches
            await self.enhance_events_batch(events, batch_size=batch_size)
            
            # Print final statistics
            self.print_final_stats()
            
        except Exception as e:
            logger.error(f"❌ Fatal error during enhancement: {e}")
            raise
        finally:
            # Close database connection
            if hasattr(self, 'client'):
                self.client.close()
                logger.info("🔌 MongoDB connection closed")

async def main():
    """
    Main function to run the enhancement script
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance existing events with social media and advanced fields")
    parser.add_argument("--limit", type=int, help="Limit number of events to enhance (for testing)")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of events to process in each batch")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be enhanced without making changes")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("🧪 DRY RUN MODE - No changes will be made to the database")
        # TODO: Implement dry run logic if needed
        return
    
    # Create and run enhancer
    enhancer = ExistingEventsEnhancer()
    await enhancer.run_enhancement(limit=args.limit, batch_size=args.batch_size)

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        "enhance_existing_events.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="INFO",
        rotation="10 MB"
    )
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level="INFO"
    )
    
    # Run the enhancement
    asyncio.run(main())