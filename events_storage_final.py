#!/usr/bin/env python3
"""
Final unified MongoDB storage for all event sources (Perplexity, Firecrawl, etc.)
Stores events directly in processed format compatible with frontend
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson import ObjectId
from loguru import logger
from dotenv import load_dotenv

# Add backend path for deduplication
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Backend'))
from utils.deduplication import EventDeduplicator

# Load environment variables from multiple possible sources
# Priority: DataCollection.env > Mongo.env > .env
env_files = ['DataCollection.env', 'Mongo.env', '.env']
for env_file in env_files:
    env_path = os.path.join(os.path.dirname(__file__), env_file)
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
        logger.info(f"Loaded environment from {env_file}")

class EventsStorageFinal:
    """
    Final unified storage for all event sources
    """
    
    def __init__(self):
        # MongoDB connection - try multiple possible env variable names
        self.mongodb_uri = (
            os.getenv('Mongo_URI') or 
            os.getenv('MONGO_URI') or 
            os.getenv('MONGODB_URL') or 
            os.getenv('MONGODB_URI')
        )
        
        self.database_name = (
            os.getenv('MONGO_DB_NAME') or 
            os.getenv('MONGODB_DATABASE') or 
            'DXB'
        )
        
        if not self.mongodb_uri:
            raise ValueError("MongoDB URI not found. Set one of: Mongo_URI, MONGO_URI, MONGODB_URL, or MONGODB_URI in environment files.")
        
        try:
            self.client = AsyncIOMotorClient(
                self.mongodb_uri,
                serverSelectionTimeoutMS=5000,
                tlsInsecure=True
            )
            
            self.db = self.client[self.database_name]
            self.events_collection = self.db.events
            
            # Initialize deduplicator
            self.deduplicator = EventDeduplicator(self.events_collection)
            
            logger.info("MongoDB client initialized (connection will be tested on first operation)")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB client: {e}")
            raise
    
    async def test_connection(self):
        """Test MongoDB connection"""
        try:
            await self.client.admin.command('ping')
            logger.success("Connected to MongoDB successfully")
            # Create indexes after successful connection
            await self._create_indexes()
            return True
        except Exception as e:
            logger.error(f"MongoDB connection test failed: {e}")
            return False
    
    async def _create_indexes(self):
        """Create necessary indexes for performance"""
        try:
            # Compound index for deduplication
            await self.events_collection.create_index(
                [("name", ASCENDING), ("startDate", ASCENDING)],
                name="dedup_index"
            )
            
            # Index for date-based queries
            await self.events_collection.create_index(
                [("startDate", DESCENDING)],
                name="date_index"
            )
            
            # Index for status
            await self.events_collection.create_index(
                [("status", ASCENDING)],
                name="status_index"
            )
            
            # Text index for search
            await self.events_collection.create_index(
                [("name", "text"), ("description", "text")],
                name="search_index"
            )
            
            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")
    
    async def store_events(self, events: List[Dict[str, Any]], source: str = None, session_id: str = None) -> Dict[str, Any]:
        """
        Store events in MongoDB with deduplication
        
        Args:
            events: List of event dictionaries
            source: Source of the events (e.g., 'perplexity', 'firecrawl')
            
        Returns:
            Dictionary with storage statistics
        """
        stats = {
            'total': len(events),
            'stored': 0,
            'duplicates': 0,
            'errors': 0,
            'source': source
        }
        
        for event in events:
            try:
                # Check for duplicates
                is_duplicate = await self.deduplicator.is_duplicate_event(event)
                existing_event = None
                
                if is_duplicate:
                    stats['duplicates'] += 1
                    logger.debug(f"Duplicate event found: {event.get('name', 'Unknown')}")
                    continue
                
                # Add metadata
                event['source'] = source
                event['createdAt'] = datetime.utcnow()
                event['updatedAt'] = datetime.utcnow()
                event['status'] = 'active'
                
                # Ensure required fields
                if '_id' not in event:
                    event['_id'] = str(ObjectId())
                
                # Store in MongoDB
                await self.events_collection.insert_one(event)
                stats['stored'] += 1
                logger.info(f"Stored event: {event.get('name', 'Unknown')}")
                
            except DuplicateKeyError:
                stats['duplicates'] += 1
                logger.debug(f"Duplicate key for event: {event.get('name', 'Unknown')}")
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error storing event: {e}")
        
        logger.info(f"Storage stats for {source}: {stats}")
        
        # Return format compatible with enhanced_collection.py expectations
        return {
            'stored_count': stats['stored'],
            'total_processed': stats['total'],
            'duplicates_prevented': stats['duplicates'],
            'errors': stats['errors']
        }
    
    async def get_recent_events(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events from the database"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        cursor = self.events_collection.find(
            {
                'startDate': {'$gte': cutoff_date.isoformat()},
                'status': 'active'
            }
        ).sort('startDate', DESCENDING).limit(limit)
        
        events = await cursor.to_list(length=limit)
        return events
    
    async def update_event_images(self, event_id: str, image_data: Dict[str, Any]) -> bool:
        """Update event with AI-generated images"""
        try:
            result = await self.events_collection.update_one(
                {'_id': event_id},
                {
                    '$set': {
                        'aiImages': image_data,
                        'updatedAt': datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating event images: {e}")
            return False
    
    async def create_extraction_session(self, session_name: str, session_data: Dict[str, Any] = None) -> str:
        """Create an extraction session record"""
        session_id = str(ObjectId())
        
        if session_data is None:
            session_data = {}
        
        session_record = {
            "_id": ObjectId(),
            "session_id": session_id,
            "session_name": session_name,
            "started_at": datetime.utcnow(),
            "status": "in_progress",
            "events_extracted": 0,
            "events_stored": 0,
            "duplicates_found": 0,
            "errors": [],
            **session_data
        }
        
        # Store in sessions collection if exists, otherwise just return the ID
        if hasattr(self.db, 'extraction_sessions'):
            await self.db.extraction_sessions.insert_one(session_record)
        
        logger.info(f"Created extraction session: {session_id} ({session_name})")
        return session_id
    
    async def update_extraction_session(self, session_id: str, updates: Dict[str, Any]):
        """Update extraction session with results"""
        if hasattr(self.db, 'extraction_sessions'):
            await self.db.extraction_sessions.update_one(
                {"session_id": session_id},
                {"$set": updates}
            )
        logger.info(f"Updated extraction session {session_id}")
    
    async def get_total_events_count(self) -> int:
        """Get total number of events in the collection"""
        try:
            return await self.events_collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting events: {e}")
            return 0
    
    async def close(self):
        """Close MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")