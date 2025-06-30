#!/usr/bin/env python3
"""
Fix Missing AI Images for June 28th Events
Generates AI images for events from June 28th that don't have them
Uses the HybridAIImageService to create images and store them permanently
"""

import asyncio
import os
import sys
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from ai_image_service_hybrid import HybridAIImageService

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'AI_API.env'))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'Mongo.env'))

# Configure logging
logger.add("logs/june28_image_fix.log", rotation="10 MB", retention="7 days")

class June28ImageFixer:
    """Fix missing AI images for June 28th events"""
    
    def __init__(self):
        self.mongodb_uri = os.getenv('Mongo_URI')
        if not self.mongodb_uri:
            raise ValueError("Mongo_URI environment variable is required")
        
        self.client = None
        self.db = None
        self.ai_service = None
        
    async def connect_to_database(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongodb_uri, tlsInsecure=True)
            self.db = self.client['DXB']
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            raise
    
    async def initialize_ai_service(self):
        """Initialize the hybrid AI image service"""
        try:
            self.ai_service = HybridAIImageService()
            logger.info("✅ HybridAIImageService initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI service: {str(e)}")
            raise
    
    async def find_events_missing_images(self):
        """Find events from June 28th that don't have AI images"""
        try:
            # Query for events created on June 28th without AI images
            query = {
                "created_at": {
                    "$gte": datetime(2025, 6, 28, 0, 0, 0),
                    "$lt": datetime(2025, 6, 29, 0, 0, 0)
                },
                "$or": [
                    {"images": {"$exists": False}},
                    {"images.ai_generated": {"$exists": False}},
                    {"images.ai_generated": None},
                    {"images.status": {"$ne": "completed_hybrid"}}
                ]
            }
            
            events = await self.db.events.find(query).to_list(length=None)
            logger.info(f"🔍 Found {len(events)} events from June 28th missing AI images")
            
            return events
            
        except Exception as e:
            logger.error(f"❌ Error finding events: {str(e)}")
            return []
    
    async def generate_images_for_events(self, events):
        """Generate AI images for the provided events"""
        if not events:
            logger.info("ℹ️ No events to process")
            return
        
        total_events = len(events)
        success_count = 0
        failed_count = 0
        skipped_count = 0
        copyright_skipped_count = 0
        
        logger.info(f"🎨 Starting AI image generation for {total_events} events from June 28th")
        logger.info("=" * 80)
        
        # Process events sequentially without batching
        for event_num, event in enumerate(events, 1):
            event_title = event.get('title', 'Unknown Event')
            event_id = str(event.get('_id', ''))
            
            try:
                logger.info(f"🎨 [{event_num}/{total_events}] Generating image for: {event_title}")
                
                # Check if event already has an image (double-check)
                existing_image = event.get('images', {}).get('ai_generated')
                if existing_image and existing_image != "":
                    logger.info(f"⏭️ Event already has image, skipping: {event_title}")
                    skipped_count += 1
                    continue
                
                # Check for copyrighted content and skip if needed
                copyright_keywords = ['little mermaid', 'disney', 'marvel', 'star wars', 'mickey mouse', 'frozen']
                if any(keyword in event_title.lower() for keyword in copyright_keywords):
                    logger.warning(f"⚠️ Skipping copyrighted content: {event_title}")
                    skipped_count += 1
                    continue
                
                # Check for copyright issues first
                copyright_check = self.ai_service._detect_copyrighted_content(
                    event.get('title', ''), 
                    event.get('description', '')
                )
                
                if copyright_check['has_copyright_issues'] and copyright_check['risk_level'] == 'high':
                    # Skip high-risk copyright content
                    copyright_skipped_count += 1
                    logger.warning(f"🚫 [{event_num}/{total_events}] Skipping due to copyright risk: {event_title}")
                    logger.warning(f"   Detected: {copyright_check['detected_patterns']}")
                    
                    # Mark as copyright skipped in database
                    try:
                        await self.ai_service.mark_event_as_copyright_skipped(
                            self.db, event['_id'], 
                            f"High copyright risk - patterns: {copyright_check['detected_patterns']}"
                        )
                    except Exception as update_error:
                        logger.error(f"❌ Failed to mark event as copyright skipped: {update_error}")
                    
                    continue
                
                # Generate AI image
                image_url = await self.ai_service.generate_image(event)
                
                if image_url:
                    # Create prompt for storage (will be safe prompt if copyright issues detected)
                    if copyright_check['has_copyright_issues']:
                        prompt_used = self.ai_service._create_copyright_safe_prompt(event)
                    else:
                        prompt_used = self.ai_service._create_hybrid_prompt(event)
                    
                    # Update event with generated image
                    success = await self.ai_service.update_event_with_image(
                        self.db, event['_id'], image_url, prompt_used
                    )
                    
                    if success:
                        success_count += 1
                        if copyright_check['has_copyright_issues']:
                            logger.info(f"✅ [{event_num}/{total_events}] Generated safe image for: {event_title}")
                        else:
                            logger.info(f"✅ [{event_num}/{total_events}] Generated image for: {event_title}")
                        logger.info(f"🔗 Image URL: {image_url[:100]}...")
                    else:
                        failed_count += 1
                        logger.error(f"❌ [{event_num}/{total_events}] Failed to update database for: {event_title}")
                else:
                    failed_count += 1
                    logger.error(f"❌ [{event_num}/{total_events}] Failed to generate image for: {event_title}")
                    
                    # Mark as failed in database
                    try:
                        await self.db.events.update_one(
                            {"_id": event['_id']},
                            {
                                "$set": {
                                    "images.status": "failed",
                                    "images.failed_at": datetime.now().isoformat(),
                                    "images.error": "AI generation failed - June 28th fix attempt"
                                }
                            }
                        )
                    except Exception as update_error:
                        logger.error(f"❌ Failed to mark event as failed: {update_error}")
                
                # Progress update every 10 events
                if event_num % 10 == 0:
                    logger.info(f"📊 Progress: {event_num}/{total_events} events processed")
                    logger.info(f"   ✅ Success: {success_count}")
                    logger.info(f"   ❌ Failed: {failed_count}")
                    logger.info(f"   ⏭️ Skipped: {skipped_count}")
                    logger.info(f"   🚫 Copyright Skipped: {copyright_skipped_count}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ [{event_num}/{total_events}] Error processing {event_title}: {str(e)}")
                
                # Mark as failed in database
                try:
                    await self.db.events.update_one(
                        {"_id": event['_id']},
                        {
                            "$set": {
                                "images.status": "failed",
                                "images.failed_at": datetime.now().isoformat(),
                                "images.error": f"Exception during generation: {str(e)}"
                            }
                        }
                    )
                except Exception as update_error:
                    logger.error(f"❌ Failed to mark event as failed: {update_error}")
        
        # Final summary
        logger.info("=" * 80)
        logger.info(f"🎉 June 28th AI Image Generation Fix Complete!")
        logger.info(f"📊 Final Results:")
        logger.info(f"   📋 Total events processed: {total_events}")
        logger.info(f"   ✅ Successfully generated: {success_count} images")
        logger.info(f"   ❌ Failed: {failed_count} images")
        logger.info(f"   ⏭️ Skipped (already had images): {skipped_count} images")
        logger.info(f"   🚫 Skipped (copyright issues): {copyright_skipped_count} images")
        
        if success_count + failed_count > 0:
            success_rate = (success_count / (success_count + failed_count)) * 100
            logger.info(f"   📈 Success rate: {success_rate:.1f}%")
        
        logger.info("=" * 80)
        
        return {
            'total': total_events,
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count,
            'copyright_skipped': copyright_skipped_count
        }
    
    async def close_connections(self):
        """Close database connections"""
        if self.client:
            self.client.close()
            logger.info("🔌 Database connection closed")

async def main():
    """Main execution function"""
    logger.info("🚀 Starting June 28th AI Image Generation Fix")
    logger.info(f"⏰ Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    fixer = June28ImageFixer()
    
    try:
        # Initialize connections and services
        await fixer.connect_to_database()
        await fixer.initialize_ai_service()
        
        # Find events missing images
        events_missing_images = await fixer.find_events_missing_images()
        
        if not events_missing_images:
            logger.info("✅ All events from June 28th already have AI images!")
            return
        
        # Generate images for missing events
        results = await fixer.generate_images_for_events(events_missing_images)
        
        # Log final status
        if results['success'] > 0:
            logger.success(f"✅ Successfully fixed {results['success']} missing images from June 28th!")
        
        if results['failed'] > 0:
            logger.warning(f"⚠️ {results['failed']} images failed to generate")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main execution: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise
    
    finally:
        await fixer.close_connections()
        logger.info(f"🏁 June 28th AI Image Fix completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Run the fix
    asyncio.run(main()) 