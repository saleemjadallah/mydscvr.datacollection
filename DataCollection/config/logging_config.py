import sys
import os
from pathlib import Path
from loguru import logger
from .settings import settings


def setup_logging():
    """Configure logging for the application."""
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Console logging
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # General application logging
    logger.add(
        "logs/data_collection.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="7 days",
        compression="zip"
    )
    
    # Error logging
    logger.add(
        "logs/errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 week",
        retention="4 weeks",
        compression="zip"
    )
    
    # Scraping specific logging
    logger.add(
        "logs/scraping.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[source]} | {message}",
        rotation="1 day",
        retention="30 days",
        filter=lambda record: "scraping" in record["extra"]
    )
    
    # Processing specific logging
    logger.add(
        "logs/processing.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation="1 day",
        retention="30 days",
        filter=lambda record: "processing" in record["extra"]
    )
    
    # Sync specific logging
    logger.add(
        "logs/sync.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation="1 day",
        retention="30 days",
        filter=lambda record: "sync" in record["extra"]
    )
    
    return logger


def get_scraping_logger(source: str):
    """Get a logger for scraping operations."""
    return logger.bind(scraping=True, source=source)


def get_processing_logger():
    """Get a logger for processing operations."""
    return logger.bind(processing=True)


def get_sync_logger():
    """Get a logger for sync operations."""
    return logger.bind(sync=True)


# Monitoring metrics tracking
class MetricsCollector:
    """Simple metrics collector for monitoring."""
    
    def __init__(self):
        self.metrics = {
            "events_scraped": 0,
            "events_processed": 0,
            "events_synced": 0,
            "scraping_errors": 0,
            "processing_errors": 0,
            "sync_errors": 0,
            "sources_scraped": set(),
            "last_scrape_times": {}
        }
    
    def increment_scraped(self, source: str, count: int = 1):
        """Increment scraped events counter."""
        self.metrics["events_scraped"] += count
        self.metrics["sources_scraped"].add(source)
        self.metrics["last_scrape_times"][source] = __import__('datetime').datetime.utcnow()
    
    def increment_processed(self, count: int = 1):
        """Increment processed events counter."""
        self.metrics["events_processed"] += count
    
    def increment_synced(self, count: int = 1):
        """Increment synced events counter."""
        self.metrics["events_synced"] += count
    
    def increment_error(self, error_type: str, count: int = 1):
        """Increment error counter."""
        error_key = f"{error_type}_errors"
        if error_key in self.metrics:
            self.metrics[error_key] += count
    
    def get_metrics(self) -> dict:
        """Get current metrics."""
        return {
            **self.metrics,
            "sources_scraped": list(self.metrics["sources_scraped"]),
            "last_scrape_times": {k: v.isoformat() for k, v in self.metrics["last_scrape_times"].items()}
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.__init__()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return metrics_collector 