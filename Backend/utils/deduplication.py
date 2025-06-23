"""
Event deduplication utilities for DXB Events API
Phase 4: Data Integration implementation
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from difflib import SequenceMatcher
import hashlib


class EventDeduplicator:
    """
    Smart event deduplication system using multiple matching strategies
    """
    
    def __init__(self, mongodb: AsyncIOMotorDatabase):
        self.mongodb = mongodb
        
        # Thresholds for duplicate detection
        self.title_similarity_threshold = 0.85
        self.venue_similarity_threshold = 0.8
        self.time_window_hours = 24  # Events within 24 hours are potential duplicates (increased from 6)
        self.description_similarity_threshold = 0.7
        
        # Common words to exclude from title comparison
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'within',
            'event', 'show', 'experience', 'festival', 'concert', 'exhibition'
        }
    
    async def is_duplicate_event(self, new_event: Dict[str, Any]) -> bool:
        """
        Check if the new event is a duplicate of an existing event
        """
        try:
            # Get potential duplicates using multiple strategies
            candidates = await self._get_duplicate_candidates(new_event)
            
            if not candidates:
                return False
            
            # Evaluate each candidate
            for candidate in candidates:
                similarity_score = self._calculate_similarity_score(new_event, candidate)
                
                # If similarity is high enough, consider it a duplicate
                if similarity_score >= 0.75:  # Lowered from 0.85 to 0.75 (75%)
                    await self._handle_duplicate_found(new_event, candidate, similarity_score)
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error in duplicate detection: {e}")
            return False  # If detection fails, allow the event to proceed
    
    async def _get_duplicate_candidates(self, new_event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get potential duplicate candidates using multiple search strategies
        """
        candidates = []
        
        # Strategy 1: Title-based search
        title_candidates = await self._search_by_title(new_event)
        candidates.extend(title_candidates)
        
        # Strategy 2: Venue and time-based search
        venue_time_candidates = await self._search_by_venue_and_time(new_event)
        candidates.extend(venue_time_candidates)
        
        # Strategy 3: Source ID matching (exact duplicates from same source)
        source_candidates = await self._search_by_source_id(new_event)
        candidates.extend(source_candidates)
        
        # Remove duplicates from candidates list
        unique_candidates = []
        seen_ids = set()
        
        for candidate in candidates:
            candidate_id = candidate.get("_id")
            if candidate_id not in seen_ids:
                unique_candidates.append(candidate)
                seen_ids.add(candidate_id)
        
        return unique_candidates
    
    async def _search_by_title(self, new_event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for events with similar titles
        """
        title = new_event.get("title", "").strip()
        if not title:
            return []
        
        # Extract key words from title
        key_words = self._extract_key_words(title)
        
        if not key_words:
            return []
        
        # Search using text search and keyword matching
        search_query = {
            "$or": [
                {"$text": {"$search": " ".join(key_words)}},
                {"keywords": {"$in": key_words}},
                {"title": {"$regex": re.escape(title[:20]), "$options": "i"}},
                # Additional fuzzy title search for better duplicate detection
                {"title": {"$regex": re.escape(title[:30]), "$options": "i"}},
                # Search for events with similar core title words
                {"title": {"$regex": "|".join([re.escape(word) for word in key_words[:3] if len(word) > 3]), "$options": "i"}}
            ]
        }
        
        candidates = await self.mongodb.events.find(search_query).limit(20).to_list(length=None)
        return candidates
    
    async def _search_by_venue_and_time(self, new_event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for events at the same venue around the same time
        """
        venue_name = new_event.get("venue_name", "").strip()
        start_date = new_event.get("start_date")
        
        if not venue_name or not start_date:
            return []
        
        # Create time window
        if isinstance(start_date, str):
            try:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return []
        
        time_before = start_date - timedelta(hours=self.time_window_hours)
        time_after = start_date + timedelta(hours=self.time_window_hours)
        
        # Search for events at similar venue and time
        search_query = {
            "$and": [
                {
                    "$or": [
                        {"venue_name": {"$regex": re.escape(venue_name[:15]), "$options": "i"}},
                        {"venue_address": {"$regex": re.escape(venue_name[:15]), "$options": "i"}}
                    ]
                },
                {
                    "start_date": {
                        "$gte": time_before,
                        "$lte": time_after
                    }
                }
            ]
        }
        
        candidates = await self.mongodb.events.find(search_query).limit(10).to_list(length=None)
        return candidates
    
    async def _search_by_source_id(self, new_event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for events with the same source ID (exact duplicates)
        """
        source_id = new_event.get("source_id")
        source_name = new_event.get("source_name")
        
        if not source_id:
            return []
        
        search_query = {
            "source_id": source_id,
            "source_name": source_name
        }
        
        candidates = await self.mongodb.events.find(search_query).limit(5).to_list(length=None)
        return candidates
    
    def _extract_key_words(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text for comparison
        """
        if not text:
            return []
        
        # Clean and normalize text
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = text.split()
        
        # Filter out stop words and short words
        key_words = [
            word for word in words
            if len(word) > 2 and word not in self.stop_words
        ]
        
        return key_words[:10]  # Limit to top 10 keywords
    
    def _calculate_similarity_score(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> float:
        """
        Calculate overall similarity score between two events
        """
        scores = {}
        
        # Title similarity (weight: 50% - increased from 40%)
        title_score = self._calculate_text_similarity(
            event1.get("title", ""),
            event2.get("title", "")
        )
        scores["title"] = title_score * 0.5
        
        # If titles are very similar, apply bonus multiplier
        if title_score > 0.9:
            scores["title"] = min(1.0, scores["title"] * 1.2)
        
        # Venue similarity (weight: 20% - reduced from 25%)
        venue_score = self._calculate_text_similarity(
            event1.get("venue_name", ""),
            event2.get("venue_name", "")
        )
        scores["venue"] = venue_score * 0.20
        
        # Time similarity (weight: 15% - reduced from 20%)
        time_score = self._calculate_time_similarity(
            event1.get("start_date"),
            event2.get("start_date")
        )
        scores["time"] = time_score * 0.15
        
        # Description similarity (weight: 10%)
        desc_score = self._calculate_text_similarity(
            event1.get("description", ""),
            event2.get("description", "")
        )
        scores["description"] = desc_score * 0.1
        
        # Source exact match (weight: 5%)
        source_score = 1.0 if (
            event1.get("source_id") == event2.get("source_id") and
            event1.get("source_name") == event2.get("source_name")
        ) else 0.0
        scores["source"] = source_score * 0.05
        
        # Calculate weighted total
        total_score = sum(scores.values())
        
        return min(1.0, total_score)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1 = re.sub(r'[^\w\s]', ' ', text1.lower()).strip()
        text2 = re.sub(r'[^\w\s]', ' ', text2.lower()).strip()
        
        if not text1 or not text2:
            return 0.0
        
        # Use sequence matcher for basic similarity
        basic_similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Use word-based similarity for additional check
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return basic_similarity
        
        # Calculate Jaccard similarity (intersection over union)
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        word_similarity = intersection / union if union > 0 else 0.0
        
        # Return weighted average
        return (basic_similarity * 0.6) + (word_similarity * 0.4)
    
    def _calculate_time_similarity(self, time1: Any, time2: Any) -> float:
        """
        Calculate similarity between two timestamps
        """
        if not time1 or not time2:
            return 0.0
        
        # Convert to datetime objects if needed
        if isinstance(time1, str):
            try:
                time1 = datetime.fromisoformat(time1.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return 0.0
        
        if isinstance(time2, str):
            try:
                time2 = datetime.fromisoformat(time2.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return 0.0
        
        if not isinstance(time1, datetime) or not isinstance(time2, datetime):
            return 0.0
        
        # Calculate time difference in hours
        time_diff = abs((time1 - time2).total_seconds()) / 3600
        
        # Create similarity score based on time difference
        if time_diff <= 1:  # Within 1 hour
            return 1.0
        elif time_diff <= 6:  # Within 6 hours
            return 1.0 - (time_diff - 1) / 5 * 0.5  # Linear decrease
        elif time_diff <= 24:  # Within 24 hours
            return 0.5 - (time_diff - 6) / 18 * 0.4  # Further decrease
        else:  # More than 24 hours
            return 0.1
    
    async def _handle_duplicate_found(
        self, 
        new_event: Dict[str, Any], 
        existing_event: Dict[str, Any], 
        similarity_score: float
    ):
        """
        Handle actions when a duplicate is found
        """
        try:
            # Log the duplicate detection
            duplicate_log = {
                "new_event": {
                    "source_id": new_event.get("source_id"),
                    "source_name": new_event.get("source_name"),
                    "title": new_event.get("title")
                },
                "existing_event": {
                    "_id": existing_event.get("_id"),
                    "title": existing_event.get("title"),
                    "source_name": existing_event.get("source_name")
                },
                "similarity_score": similarity_score,
                "detected_at": datetime.now(timezone.utc),
                "action": "rejected_duplicate"
            }
            
            # Store duplicate detection log
            await self.mongodb.duplicate_logs.insert_one(duplicate_log)
            
            # Update existing event with additional source information if beneficial
            await self._merge_event_data(new_event, existing_event)
            
        except Exception as e:
            print(f"Error handling duplicate: {e}")
    
    async def _merge_event_data(self, new_event: Dict[str, Any], existing_event: Dict[str, Any]):
        """
        Merge useful data from new event into existing event
        """
        try:
            update_fields = {}
            
            # Merge image URLs
            existing_images = existing_event.get("image_urls", [])
            new_images = new_event.get("image_urls", [])
            all_images = list(set(existing_images + new_images))
            if len(all_images) > len(existing_images):
                update_fields["image_urls"] = all_images
            
            # Update booking URL if missing
            if not existing_event.get("booking_url") and new_event.get("booking_url"):
                update_fields["booking_url"] = new_event.get("booking_url")
            
            # Merge tags
            existing_tags = existing_event.get("tags", [])
            new_tags = new_event.get("tags", [])
            all_tags = list(set(existing_tags + new_tags))
            if len(all_tags) > len(existing_tags):
                update_fields["tags"] = all_tags
            
            # Add source tracking
            if "source_tracking" not in existing_event:
                update_fields["source_tracking"] = []
            
            source_info = {
                "source_name": new_event.get("source_name"),
                "source_id": new_event.get("source_id"),
                "first_seen": datetime.now(timezone.utc),
                "data": new_event.get("source_data", {})
            }
            
            update_fields["$push"] = {"source_tracking": source_info}
            update_fields["last_updated"] = datetime.now(timezone.utc)
            
            # Perform update if there are changes
            if update_fields:
                await self.mongodb.events.update_one(
                    {"_id": existing_event["_id"]},
                    {"$set": {k: v for k, v in update_fields.items() if k != "$push"},
                     "$push": update_fields.get("$push", {})}
                )
            
        except Exception as e:
            print(f"Error merging event data: {e}")
    
    async def get_duplicate_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about duplicate detection
        """
        try:
            # Get duplicate detection logs
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = today - timedelta(days=7)
            
            # Today's duplicates
            today_duplicates = await self.mongodb.duplicate_logs.count_documents({
                "detected_at": {"$gte": today}
            })
            
            # Week's duplicates
            week_duplicates = await self.mongodb.duplicate_logs.count_documents({
                "detected_at": {"$gte": week_ago}
            })
            
            # Total duplicates
            total_duplicates = await self.mongodb.duplicate_logs.count_documents({})
            
            # Top duplicate sources
            pipeline = [
                {"$group": {
                    "_id": "$new_event.source_name",
                    "duplicate_count": {"$sum": 1}
                }},
                {"$sort": {"duplicate_count": -1}},
                {"$limit": 5}
            ]
            
            top_sources = await self.mongodb.duplicate_logs.aggregate(pipeline).to_list(length=None)
            
            return {
                "today_duplicates": today_duplicates,
                "week_duplicates": week_duplicates,
                "total_duplicates": total_duplicates,
                "top_duplicate_sources": top_sources,
                "deduplication_rate": f"{(total_duplicates / max(1, total_duplicates + await self.mongodb.events.count_documents({})) * 100):.1f}%"
            }
            
        except Exception as e:
            print(f"Error getting duplicate statistics: {e}")
            return {
                "today_duplicates": 0,
                "week_duplicates": 0,
                "total_duplicates": 0,
                "top_duplicate_sources": [],
                "deduplication_rate": "0.0%"
            }
    
    async def find_potential_duplicates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Find potential duplicates that may have been missed
        """
        try:
            # Find events with very similar titles
            pipeline = [
                {"$group": {
                    "_id": {"$substr": ["$title", 0, 20]},
                    "events": {"$push": "$$ROOT"},
                    "count": {"$sum": 1}
                }},
                {"$match": {"count": {"$gt": 1}}},
                {"$limit": limit}
            ]
            
            potential_groups = await self.mongodb.events.aggregate(pipeline).to_list(length=None)
            
            potential_duplicates = []
            for group in potential_groups:
                events = group.get("events", [])
                if len(events) > 1:
                    # Compare each pair in the group
                    for i in range(len(events)):
                        for j in range(i + 1, len(events)):
                            similarity = self._calculate_similarity_score(events[i], events[j])
                            if similarity > 0.7:  # Lower threshold for investigation
                                potential_duplicates.append({
                                    "event1": {
                                        "_id": events[i]["_id"],
                                        "title": events[i]["title"],
                                        "source_name": events[i].get("source_name")
                                    },
                                    "event2": {
                                        "_id": events[j]["_id"],
                                        "title": events[j]["title"],
                                        "source_name": events[j].get("source_name")
                                    },
                                    "similarity_score": similarity,
                                    "needs_review": True
                                })
            
            return potential_duplicates
            
        except Exception as e:
            print(f"Error finding potential duplicates: {e}")
            return [] 