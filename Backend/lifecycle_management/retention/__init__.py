"""
Retention Management Module

Handles automated retention policies and data lifecycle management
for scraped event data based on source priority.
"""

from .source_based_cleanup import SourceBasedRetentionManager
from .data_handler import ScrapingDataHandler

__all__ = ['SourceBasedRetentionManager', 'ScrapingDataHandler'] 