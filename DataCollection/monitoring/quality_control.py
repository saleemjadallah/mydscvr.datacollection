"""
Data Quality Monitoring System
Comprehensive monitoring for event data quality and completeness
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import urlparse

from config.database_schema import get_mongodb_connection
from config.logging_config import get_logger

logger = get_logger(__name__)


class QualityIssue(Enum):
    MISSING_TITLE = "missing_title"
    MISSING_DATE = "missing_date"
    MISSING_VENUE = "missing_venue"
    INVALID_DATE = "invalid_date"
    INVALID_PRICE = "invalid_price"
    MISSING_DESCRIPTION = "missing_description"
    POOR_DESCRIPTION = "poor_description"
    INVALID_IMAGE_URL = "invalid_image_url"
    MISSING_CATEGORY = "missing_category"
    INVALID_COORDINATES = "invalid_coordinates"
    DUPLICATE_CONTENT = "duplicate_content"
    OUTDATED_EVENT = "outdated_event"


@dataclass
class QualityMetrics:
    quality_score: float
    completeness_score: float
    accuracy_score: float
    freshness_score: float
    issues: List[QualityIssue]
    details: Dict[str, any]


class DataQualityMonitor:
    def __init__(self):
        self.mongodb = None
        self.quality_thresholds = {
            'minimum_score': 60,
            'description_min_length': 50,
            'description_max_length': 2000,
            'title_min_length': 10,
            'max_days_old': 90,
            'price_max': 10000
        }
    
    async def __aenter__(self):
        self.mongodb = await get_mongodb_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.mongodb:
            self.mongodb.close()

    async def check_event_quality(self, event: Dict) -> QualityMetrics:
        """Comprehensive quality assessment for a single event"""
        issues = []
        completeness_score = 0
        accuracy_score = 0
        freshness_score = 0
        details = {}

        # Check completeness (40% of total score)
        completeness_checks = [
            ('title', self._check_title),
            ('description', self._check_description),
            ('start_date', self._check_start_date),
            ('venue', self._check_venue),
            ('pricing', self._check_pricing),
            ('categories', self._check_categories),
            ('image_urls', self._check_images)
        ]
        
        completed_checks = 0
        for field, check_func in completeness_checks:
            is_valid, issue = check_func(event.get(field))
            if is_valid:
                completed_checks += 1
            elif issue:
                issues.append(issue)
        
        completeness_score = (completed_checks / len(completeness_checks)) * 40

        # Check accuracy (35% of total score)
        accuracy_issues, accuracy_details = await self._check_accuracy(event)
        issues.extend(accuracy_issues)
        details.update(accuracy_details)
        accuracy_score = max(0, 35 - len(accuracy_issues) * 5)

        # Check freshness (25% of total score)
        freshness_issues, freshness_details = self._check_freshness(event)
        issues.extend(freshness_issues)
        details.update(freshness_details)
        freshness_score = max(0, 25 - len(freshness_issues) * 10)

        quality_score = completeness_score + accuracy_score + freshness_score

        return QualityMetrics(
            quality_score=quality_score,
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            freshness_score=freshness_score,
            issues=issues,
            details=details
        )

    def _check_title(self, title: Optional[str]) -> Tuple[bool, Optional[QualityIssue]]:
        """Check title quality"""
        if not title:
            return False, QualityIssue.MISSING_TITLE
        if len(title.strip()) < self.quality_thresholds['title_min_length']:
            return False, QualityIssue.MISSING_TITLE
        return True, None

    def _check_description(self, description: Optional[str]) -> Tuple[bool, Optional[QualityIssue]]:
        """Check description quality"""
        if not description:
            return False, QualityIssue.MISSING_DESCRIPTION
        
        desc_len = len(description.strip())
        if desc_len < self.quality_thresholds['description_min_length']:
            return False, QualityIssue.POOR_DESCRIPTION
        if desc_len > self.quality_thresholds['description_max_length']:
            return False, QualityIssue.POOR_DESCRIPTION
        
        return True, None

    def _check_start_date(self, start_date) -> Tuple[bool, Optional[QualityIssue]]:
        """Check start date validity"""
        if not start_date:
            return False, QualityIssue.MISSING_DATE
        
        try:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            
            # Check if date is in the past (more than 1 day)
            if start_date < datetime.now() - timedelta(days=1):
                return False, QualityIssue.OUTDATED_EVENT
            
            # Check if date is too far in the future (more than 1 year)
            if start_date > datetime.now() + timedelta(days=365):
                return False, QualityIssue.INVALID_DATE
                
            return True, None
        except:
            return False, QualityIssue.INVALID_DATE

    def _check_venue(self, venue) -> Tuple[bool, Optional[QualityIssue]]:
        """Check venue information"""
        if not venue:
            return False, QualityIssue.MISSING_VENUE
        
        if isinstance(venue, dict):
            if not venue.get('name') and not venue.get('address'):
                return False, QualityIssue.MISSING_VENUE
        elif isinstance(venue, str):
            if len(venue.strip()) < 3:
                return False, QualityIssue.MISSING_VENUE
        
        return True, None

    def _check_pricing(self, pricing) -> Tuple[bool, Optional[QualityIssue]]:
        """Check pricing information"""
        if not pricing:
            return True, None  # Pricing is optional
        
        if isinstance(pricing, dict):
            min_price = pricing.get('min_price', 0)
            max_price = pricing.get('max_price', 0)
            
            try:
                if float(min_price) < 0 or float(max_price) < 0:
                    return False, QualityIssue.INVALID_PRICE
                if float(max_price) > self.quality_thresholds['price_max']:
                    return False, QualityIssue.INVALID_PRICE
                if min_price > max_price and max_price > 0:
                    return False, QualityIssue.INVALID_PRICE
            except (ValueError, TypeError):
                return False, QualityIssue.INVALID_PRICE
        
        return True, None

    def _check_categories(self, categories) -> Tuple[bool, Optional[QualityIssue]]:
        """Check category information"""
        if not categories:
            return False, QualityIssue.MISSING_CATEGORY
        
        if isinstance(categories, list) and len(categories) == 0:
            return False, QualityIssue.MISSING_CATEGORY
        
        return True, None

    def _check_images(self, image_urls) -> Tuple[bool, Optional[QualityIssue]]:
        """Check image URL validity"""
        if not image_urls:
            return True, None  # Images are optional
        
        if isinstance(image_urls, list):
            for url in image_urls:
                if not self._is_valid_image_url(url):
                    return False, QualityIssue.INVALID_IMAGE_URL
        
        return True, None

    def _is_valid_image_url(self, url: str) -> bool:
        """Validate image URL format"""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check for common image extensions
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            return any(url.lower().endswith(ext) for ext in valid_extensions)
        except:
            return False

    async def _check_accuracy(self, event: Dict) -> Tuple[List[QualityIssue], Dict]:
        """Check data accuracy and consistency"""
        issues = []
        details = {}
        
        # Check for duplicate content
        if await self._is_potential_duplicate(event):
            issues.append(QualityIssue.DUPLICATE_CONTENT)
            details['duplicate_check'] = 'Potential duplicate found'
        
        # Check coordinate validity
        venue = event.get('venue', {})
        if isinstance(venue, dict) and 'coordinates' in venue:
            coords = venue['coordinates']
            if not self._are_valid_dubai_coordinates(coords):
                issues.append(QualityIssue.INVALID_COORDINATES)
                details['coordinates_check'] = 'Invalid Dubai coordinates'
        
        return issues, details

    def _check_freshness(self, event: Dict) -> Tuple[List[QualityIssue], Dict]:
        """Check data freshness"""
        issues = []
        details = {}
        
        scraped_at = event.get('scraped_at') or event.get('imported_at')
        if scraped_at:
            try:
                if isinstance(scraped_at, str):
                    scraped_at = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
                
                days_old = (datetime.now() - scraped_at).days
                details['data_age_days'] = days_old
                
                if days_old > self.quality_thresholds['max_days_old']:
                    issues.append(QualityIssue.OUTDATED_EVENT)
            except:
                pass
        
        return issues, details

    async def _is_potential_duplicate(self, event: Dict) -> bool:
        """Check if event might be a duplicate"""
        if not self.mongodb:
            return False
        
        title = event.get('title', '')
        start_date = event.get('start_date')
        venue_name = ''
        
        venue = event.get('venue', {})
        if isinstance(venue, dict):
            venue_name = venue.get('name', '')
        elif isinstance(venue, str):
            venue_name = venue
        
        if not title or not start_date:
            return False
        
        # Search for similar events
        query = {
            'title': {'$regex': re.escape(title[:20]), '$options': 'i'},
            'start_date': start_date
        }
        
        if venue_name:
            query['$or'] = [
                {'venue.name': {'$regex': re.escape(venue_name[:10]), '$options': 'i'}},
                {'venue_name': {'$regex': re.escape(venue_name[:10]), '$options': 'i'}}
            ]
        
        try:
            existing = await self.mongodb.processed_events.find_one(query)
            return existing is not None
        except:
            return False

    def _are_valid_dubai_coordinates(self, coords) -> bool:
        """Check if coordinates are within Dubai area"""
        if not coords or len(coords) != 2:
            return False
        
        try:
            lng, lat = float(coords[0]), float(coords[1])
            # Dubai approximate bounds
            return (54.9 <= lng <= 55.6) and (24.8 <= lat <= 25.4)
        except:
            return False

    async def monitor_source_health(self, source: str, hours: int = 24) -> Dict:
        """Monitor scraping health for a specific source"""
        if not self.mongodb:
            return {}
        
        since = datetime.now() - timedelta(hours=hours)
        
        # Count events by source
        total_events = await self.mongodb.raw_events.count_documents({
            'source': source,
            'scraped_at': {'$gte': since}
        })
        
        processed_events = await self.mongodb.processed_events.count_documents({
            'source_name': source,
            'processed_at': {'$gte': since}
        })
        
        # Count errors
        error_events = await self.mongodb.raw_events.count_documents({
            'source': source,
            'status': 'error',
            'scraped_at': {'$gte': since}
        })
        
        success_rate = (processed_events / total_events * 100) if total_events > 0 else 0
        error_rate = (error_events / total_events * 100) if total_events > 0 else 0
        
        return {
            'source': source,
            'period_hours': hours,
            'total_scraped': total_events,
            'total_processed': processed_events,
            'total_errors': error_events,
            'success_rate': round(success_rate, 2),
            'error_rate': round(error_rate, 2),
            'health_status': 'healthy' if success_rate > 80 else 'degraded' if success_rate > 50 else 'unhealthy'
        }

    async def generate_quality_report(self, hours: int = 24) -> Dict:
        """Generate comprehensive quality report"""
        if not self.mongodb:
            return {}
        
        since = datetime.now() - timedelta(hours=hours)
        
        # Get recent processed events
        events_cursor = self.mongodb.processed_events.find({
            'processed_at': {'$gte': since}
        }).limit(1000)
        
        events = await events_cursor.to_list(length=1000)
        
        if not events:
            return {
                'period_hours': hours,
                'total_events': 0,
                'message': 'No events found in the specified period'
            }
        
        # Analyze quality for all events
        quality_scores = []
        issue_counts = {}
        source_quality = {}
        
        for event in events:
            metrics = await self.check_event_quality(event)
            quality_scores.append(metrics.quality_score)
            
            # Count issues
            for issue in metrics.issues:
                issue_counts[issue.value] = issue_counts.get(issue.value, 0) + 1
            
            # Track by source
            source = event.get('source_name', 'unknown')
            if source not in source_quality:
                source_quality[source] = []
            source_quality[source].append(metrics.quality_score)
        
        # Calculate summary statistics
        avg_quality = sum(quality_scores) / len(quality_scores)
        high_quality_events = len([s for s in quality_scores if s >= 80])
        low_quality_events = len([s for s in quality_scores if s < 60])
        
        # Source quality summary
        source_summary = {}
        for source, scores in source_quality.items():
            source_summary[source] = {
                'avg_quality': round(sum(scores) / len(scores), 2),
                'event_count': len(scores),
                'high_quality_percent': round(len([s for s in scores if s >= 80]) / len(scores) * 100, 2)
            }
        
        return {
            'period_hours': hours,
            'total_events': len(events),
            'average_quality_score': round(avg_quality, 2),
            'high_quality_events': high_quality_events,
            'high_quality_percentage': round(high_quality_events / len(events) * 100, 2),
            'low_quality_events': low_quality_events,
            'low_quality_percentage': round(low_quality_events / len(events) * 100, 2),
            'common_issues': dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'source_quality': source_summary,
            'quality_distribution': {
                'excellent_80_100': len([s for s in quality_scores if s >= 80]),
                'good_60_79': len([s for s in quality_scores if 60 <= s < 80]),
                'poor_below_60': len([s for s in quality_scores if s < 60])
            },
            'generated_at': datetime.now().isoformat()
        }

    async def get_quality_summary(self) -> Dict:
        """Get quick quality summary for monitoring"""
        if not self.mongodb:
            return {}
        
        try:
            # Last 24 hours stats
            since = datetime.now() - timedelta(hours=24)
            
            total_events = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since}
            })
            
            # Count events by quality (this would require pre-calculated quality scores)
            # For now, we'll use proxy metrics
            complete_events = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since},
                'title': {'$exists': True, '$ne': ''},
                'description': {'$exists': True, '$ne': ''},
                'start_date': {'$exists': True}
            })
            
            quality_percentage = (complete_events / total_events * 100) if total_events > 0 else 0
            
            return {
                'total_events_24h': total_events,
                'complete_events_24h': complete_events,
                'estimated_quality_percentage': round(quality_percentage, 2),
                'status': 'healthy' if quality_percentage > 85 else 'degraded' if quality_percentage > 70 else 'unhealthy',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error generating quality summary: {e}")
            return {'error': str(e)}


# Utility function for quick quality check
async def quick_quality_check(event: Dict) -> float:
    """Quick quality assessment without full analysis"""
    score = 0
    max_score = 100
    
    # Basic completeness checks (70 points)
    if event.get('title'): score += 15
    if event.get('description'): score += 15
    if event.get('start_date'): score += 15
    if event.get('venue'): score += 10
    if event.get('categories'): score += 10
    if event.get('source_name'): score += 5
    
    # Quality checks (30 points)
    title = event.get('title', '')
    description = event.get('description', '')
    
    if len(title) >= 10: score += 10
    if len(description) >= 50: score += 10
    if event.get('image_urls'): score += 5
    if event.get('pricing'): score += 5
    
    return min(score, max_score)