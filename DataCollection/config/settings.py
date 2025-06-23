#!/usr/bin/env python3
"""
DEPRECATED: Legacy Settings Configuration

This file is DEPRECATED and kept only for backward compatibility.
Please use config/perplexity_settings.py for the new Perplexity-based system.

The new system no longer uses Firecrawl, Celery, Redis, or other complex dependencies.
All data collection is now handled by Perplexity AI directly.
"""

import warnings
from typing import Optional
from pydantic_settings import BaseSettings

# Issue deprecation warning
warnings.warn(
    "config/settings.py is deprecated. Use config/perplexity_settings.py instead.",
    DeprecationWarning,
    stacklevel=2
)

class LegacySettings(BaseSettings):
    """
    DEPRECATED: Legacy settings for backward compatibility only.
    Use PerplexityDataCollectionSettings instead.
    """
    
    # Legacy API Keys (most are no longer used)
    PERPLEXITY_API_KEY: str = ""
    OPENAI_API_KEY: Optional[str] = None
    
    # MongoDB Configuration (still used)
    MONGODB_CONNECTION_STRING: str = "mongodb+srv://support:olaabdel88@dxb.tq60png.mongodb.net/?retryWrites=true&w=majority&appName=DXB&tls=true&tlsAllowInvalidCertificates=true"
    DATABASE_NAME: str = "DXB"
    
    # Collection Names (updated for new system)
    EVENTS_COLLECTION: str = "events"
    SESSIONS_COLLECTION: str = "extraction_sessions"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = [".env", "AI_API.env", "Mongo.env"]
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields for backward compatibility

# Legacy global instance
settings = LegacySettings()

def get_settings() -> LegacySettings:
    """
    DEPRECATED: Get legacy settings.
    Use config.perplexity_settings.get_settings() instead.
    """
    warnings.warn(
        "get_settings() from config.settings is deprecated. Use config.perplexity_settings.get_settings() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return settings

def validate_required_settings():
    """
    DEPRECATED: Legacy validation.
    Use the new PerplexityDataCollectionSettings validation instead.
    """
    warnings.warn(
        "validate_required_settings() is deprecated. The new system validates automatically.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if not settings.PERPLEXITY_API_KEY:
        raise ValueError("PERPLEXITY_API_KEY is required")
    
    return True

# Migration helper
def migrate_to_new_settings():
    """
    Helper function to show migration path to new settings system.
    """
    print("MIGRATION NOTICE:")
    print("================")
    print("The old settings system has been replaced!")
    print()
    print("OLD: from config.settings import get_settings")
    print("NEW: from config.perplexity_settings import get_settings")
    print()
    print("The new system:")
    print("- Removes all Firecrawl dependencies")
    print("- Uses only Perplexity AI for data collection")
    print("- Has cleaner configuration")
    print("- Includes better validation")
    print()
    print("Please update your imports!")

if __name__ == "__main__":
    migrate_to_new_settings() 