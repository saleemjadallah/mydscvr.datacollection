#!/usr/bin/env python3
"""
AI Image Generation Service with Direct S3 Upload
Generates AI images using DALL-E 3 and immediately uploads to S3
"""

import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from loguru import logger
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import hashlib
import boto3
from botocore.exceptions import ClientError
import io
import ssl
import certifi

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'AI_API.env'))

class AIImageServiceS3:
    """
    AI Image Generation Service using DALL-E 3 with direct S3 upload
    Ensures images are permanently stored immediately after generation
    """
    
    def __init__(self):
        # OpenAI configuration
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required but not set")
        
        self.base_url = "https://api.openai.com/v1/images/generations"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # S3 configuration
        self.s3_bucket = os.getenv('S3_BUCKET_NAME', 'mydscvr-event-images')
        self.s3_region = os.getenv('S3_REGION', 'me-central-1')
        self.s3_client = boto3.client(
            's3',
            region_name=self.s3_region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Configure logging
        logger.add("logs/ai_image_service_s3.log", rotation="10 MB", retention="7 days")
        
        # Category-specific prompt templates
        self.category_prompts = {
            "nightlife": "vibrant nightclub atmosphere, neon lights, energetic crowd, Dubai skyline at night",
            "dining": "elegant restaurant setting, fine dining ambiance, sophisticated atmosphere", 
            "family_activities": "family-friendly venue, bright welcoming atmosphere, children and parents enjoying activities",
            "cultural": "cultural venue, traditional meets modern Dubai architecture, heritage elements",
            "outdoor": "outdoor event setting with Dubai skyline background, palm trees, modern architecture",
            "entertainment": "live performance venue, stage lighting, audience engagement, professional entertainment",
            "sports": "sports facility, athletic activities, modern Dubai sports venues",
            "business": "professional conference setting, modern business environment, Dubai corporate atmosphere",
            "music": "concert venue, stage with lighting, musical performance atmosphere",
            "arts": "art gallery or creative space, contemporary Dubai arts scene",
            "shopping": "luxury shopping environment, modern Dubai mall atmosphere",
            "educational": "learning environment, workshop setting, educational activities",
            "fitness": "modern fitness facility, wellness atmosphere, healthy lifestyle",
            "technology": "tech event space, modern conference setting, innovation atmosphere",
            "health_wellness": "serene wellness center, meditation space, peaceful atmosphere, yoga studio",
            "workshops": "hands-on workshop space, creative learning environment, interactive session setting",
            "festivals": "festive outdoor setting, celebration atmosphere, community gathering"
        }
        
    def _generate_s3_key(self, event_id: str, event_name: str) -> str:
        """Generate a unique S3 key for the image"""
        # Clean event name for filename
        clean_name = "".join(c for c in event_name if c.isalnum() or c in (' ', '-', '_'))[:50]
        clean_name = clean_name.replace(' ', '_')
        
        # Create unique hash
        unique_hash = hashlib.md5(f"{event_id}{event_name}".encode()).hexdigest()[:8]
        
        # Generate S3 key
        return f"ai-images/{event_id}_{clean_name}_{unique_hash}.jpg"
    
    def _create_prompt(self, event: Dict[str, Any]) -> str:
        """Create optimized prompt for DALL-E 3"""
        event_name = event.get('name', event.get('title', 'Event'))
        category = event.get('category', event.get('primary_category', 'general'))
        venue = event.get('venue', {})
        
        # Build base prompt
        prompt_parts = [f"Professional event photography: {event_name}"]
        
        # Add category-specific elements
        if category in self.category_prompts:
            prompt_parts.append(self.category_prompts[category])
        
        # Add venue context
        if isinstance(venue, dict) and venue.get('name'):
            prompt_parts.append(f"Located at {venue['name']}")
            
        # Add Dubai context
        prompt_parts.append("Dubai location, modern architecture, high quality, professional photography")
        
        # Style modifiers
        prompt_parts.append("8k resolution, professional lighting, vibrant colors, no text, no watermarks")
        
        prompt = ". ".join(prompt_parts)
        
        # Ensure prompt is within DALL-E 3 limits
        if len(prompt) > 4000:
            prompt = prompt[:3997] + "..."
            
        return prompt
    
    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download image: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            return None
    
    def _upload_to_s3(self, image_data: bytes, s3_key: str) -> Optional[str]:
        """Upload image to S3 and return the public URL"""
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=image_data,
                ContentType='image/jpeg',
                CacheControl='public, max-age=31536000',  # Cache for 1 year
                Metadata={
                    'generated': 'dalle3',
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            
            # Return the public URL
            s3_url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{s3_key}"
            logger.info(f"✅ Uploaded to S3: {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            return None
    
    async def generate_and_store_image(self, event: Dict[str, Any]) -> Optional[str]:
        """Generate AI image and immediately store in S3"""
        
        event_name = event.get('name', event.get('title', 'Unknown Event'))
        event_id = str(event.get('_id', event.get('id', '')))
        
        # Check if event already has an S3 AI image
        if 'images' in event and isinstance(event['images'], dict):
            existing_image = event['images'].get('ai_generated', '')
            if existing_image and 'mydscvr-event-images.s3' in str(existing_image):
                logger.info(f"✅ Event {event_id} already has S3 image: {existing_image[:50]}...")
                return existing_image
        
        logger.info(f"🎨 Generating AI image for: {event_name}")
        
        try:
            # Create prompt
            prompt = self._create_prompt(event)
            
            # Call DALL-E 3 API
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                payload = {
                    "model": "dall-e-3",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1024x1024",
                    "quality": "standard",
                    "response_format": "url"
                }
                
                async with session.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        temp_url = data['data'][0]['url']
                        logger.info(f"✅ Generated image for: {event_name}")
                        
                        # Immediately download the image
                        image_data = await self._download_image(temp_url)
                        if not image_data:
                            logger.error(f"Failed to download generated image for {event_name}")
                            return None
                        
                        # Generate S3 key and upload
                        s3_key = self._generate_s3_key(event_id, event_name)
                        s3_url = self._upload_to_s3(image_data, s3_key)
                        
                        if s3_url:
                            logger.info(f"✅ Successfully stored image in S3 for: {event_name}")
                            return s3_url
                        else:
                            logger.error(f"Failed to upload to S3 for {event_name}")
                            # Fallback: return temporary URL (will expire)
                            return temp_url
                            
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ DALL-E API error for {event_name}: {response.status} - {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout generating image for: {event_name}")
            return None
        except Exception as e:
            logger.error(f"❌ Error generating image for {event_name}: {str(e)}")
            return None
    
    async def update_event_with_image(self, db, event_id: str, image_url: str) -> bool:
        """Update event in database with S3 image URL"""
        
        try:
            # Determine if it's an S3 URL or temporary URL
            is_s3 = 'mydscvr-event-images.s3' in image_url
            
            result = await db.events.update_one(
                {"_id": event_id},
                {
                    "$set": {
                        "images.ai_generated": image_url,
                        "images.storage_type": "s3" if is_s3 else "temporary",
                        "images.generated_at": datetime.utcnow(),
                        "images.generation_method": "dalle3_with_s3",
                        "images.status": "completed"
                    },
                    "$unset": {
                        "images.needs_regeneration": ""
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Updated event {event_id} with AI image")
                return True
            else:
                logger.warning(f"⚠️ No event found with ID {event_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating event {event_id} with image: {str(e)}")
            return False
    
    async def process_events_batch(self, db, events: List[Dict[str, Any]], batch_size: int = 3) -> Dict[str, Any]:
        """Process a batch of events for image generation with S3 storage"""
        
        logger.info(f"🎨 Processing batch of {len(events)} events for AI image generation")
        
        results = {
            "total_events": len(events),
            "successful": 0,
            "failed": 0,
            "already_has_image": 0,
            "processing_time": 0
        }
        
        start_time = datetime.now()
        
        # Process events in smaller batches to respect API rate limits
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            logger.info(f"📦 Processing batch {i//batch_size + 1}: events {i+1}-{min(i+batch_size, len(events))}")
            
            # Process batch concurrently
            tasks = []
            for event in batch:
                task = self._process_single_event(db, event)
                tasks.append(task)
            
            # Wait for batch completion
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update results
            for result in batch_results:
                if isinstance(result, Exception):
                    results["failed"] += 1
                    logger.error(f"Batch processing error: {str(result)}")
                elif result == "already_has_image":
                    results["already_has_image"] += 1
                elif result == "success":
                    results["successful"] += 1
                else:
                    results["failed"] += 1
            
            # Rate limiting delay between batches
            if i + batch_size < len(events):
                logger.info("⏸️ Waiting 5 seconds between batches...")
                await asyncio.sleep(5)
        
        results["processing_time"] = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"🎉 Batch processing complete: {results}")
        return results
    
    async def _process_single_event(self, db, event: Dict[str, Any]) -> str:
        """Process a single event for image generation"""
        
        event_id = event.get('_id')
        if not event_id:
            return "failed"
        
        try:
            # Generate and store image
            image_url = await self.generate_and_store_image(event)
            
            if image_url:
                # Update database
                success = await self.update_event_with_image(db, event_id, image_url)
                return "success" if success else "failed"
            else:
                return "failed"
                
        except Exception as e:
            logger.error(f"Error processing event {event_id}: {str(e)}")
            return "failed"


# Main execution for testing
async def main():
    """Test the AI image service with S3"""
    
    # Initialize service
    service = AIImageServiceS3()
    
    # Connect to MongoDB
    mongo_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
    client = AsyncIOMotorClient(mongo_url)
    db = client['DXB']
    
    # Get a few events that need images
    events = await db.events.find({
        "status": "active",
        "images.needs_regeneration": True
    }).limit(3).to_list(None)
    
    if events:
        logger.info(f"Found {len(events)} active events needing images")
        results = await service.process_events_batch(db, events)
        logger.info(f"Processing results: {results}")
    else:
        logger.info("No events found needing image generation")
    
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())