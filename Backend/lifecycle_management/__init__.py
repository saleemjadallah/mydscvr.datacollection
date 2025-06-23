"""
DXB Events Data Lifecycle Management

This module provides automated lifecycle management for scraped event data,
including source-based retention policies, automated cleanup, and storage monitoring.

Key Components:
- SourceBasedRetentionManager: Manages retention policies based on source priority
- ScrapingDataHandler: Handles storage of scraped events with automatic retention
- StorageHealthMonitor: Monitors storage efficiency and generates reports
- Automated Celery tasks for cleanup and monitoring

Source Priority Levels:
- High (7-day retention): dubai_calendar, timeout_dubai, timeout_kids_uae, platinumlist
- Medium (3-day retention): eventbrite_dubai, meetup_dubai, whats_on_dubai, etc.
- Low (1-day retention): 7g_media, social_rising, instagram_influencers
"""

from .retention.source_based_cleanup import SourceBasedRetentionManager
from .retention.data_handler import ScrapingDataHandler
from .monitoring.storage_health import StorageHealthMonitor
from .celery_config import celery_app

__all__ = [
    'SourceBasedRetentionManager',
    'ScrapingDataHandler', 
    'StorageHealthMonitor',
    'celery_app'
]

__version__ = "1.0.0" 