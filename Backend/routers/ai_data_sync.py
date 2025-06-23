"""
AI Data Sync Router for DXB Events API
Syncs data from the AI APIs data collection service
"""

import os
import sys
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from database import get_mongodb
from schemas import SuccessResponse

# Add the Data-Collection path to sys.path to import our AI APIs
data_collection_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'Data-Collection')
if data_collection_path not in sys.path:
    sys.path.insert(0, data_collection_path)

try:
    # Import AI APIs with specific naming to avoid conflicts
    from integrations.ai_apis.pipeline_orchestrator import PipelineOrchestrator
    from integrations.ai_apis.config import AIAPIsConfig as AIConfig
    AI_APIS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI APIs not available: {e}")
    AI_APIS_AVAILABLE = False

router = APIRouter(prefix="/api/data-sync", tags=["data-sync"])


@router.post("/sync-events", response_model=SuccessResponse)
async def sync_events_from_ai_apis(
    background_tasks: BackgroundTasks,
    full_sync: bool = False,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Sync events from AI APIs to the backend database
    """
    if not AI_APIS_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="AI APIs integration not available. Please check the Data-Collection service."
        )
    
    # Add sync task to background
    background_tasks.add_task(
        _sync_events_background, 
        db, 
        full_sync
    )
    
    return SuccessResponse(
        message="Event sync started in background",
        data={"sync_type": "full" if full_sync else "incremental"}
    )


@router.get("/sync-status")
async def get_sync_status(db: AsyncIOMotorDatabase = Depends(get_mongodb)):
    """
    Get the status of the last sync operation
    """
    sync_status = await db.sync_logs.find_one(
        {}, 
        sort=[("timestamp", -1)]
    )
    
    if not sync_status:
        return {
            "status": "never_synced",
            "message": "No sync operations found",
            "last_sync": None
        }
    
    return {
        "status": sync_status.get("status", "unknown"),
        "last_sync": sync_status.get("timestamp"),
        "events_synced": sync_status.get("events_synced", 0),
        "sources_processed": sync_status.get("sources_processed", []),
        "errors": sync_status.get("errors", [])
    }


@router.post("/manual-sync", response_model=SuccessResponse)
async def manual_sync_specific_source(
    source_name: str,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Manually sync a specific Dubai event source
    """
    if not AI_APIS_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="AI APIs integration not available"
        )
    
    background_tasks.add_task(
        _sync_specific_source_background, 
        db, 
        source_name
    )
    
    return SuccessResponse(
        message=f"Manual sync started for source: {source_name}",
        data={"source": source_name}
    )


@router.get("/available-sources")
async def get_available_sources():
    """
    Get list of available Dubai event sources from AI APIs
    """
    if not AI_APIS_AVAILABLE:
        return {"sources": [], "error": "AI APIs not available"}
    
    try:
        config = AIConfig()
        sources = list(config.dubai_sources.keys())
        return {
            "sources": sources,
            "total": len(sources),
            "ai_apis_status": "available"
        }
    except Exception as e:
        return {
            "sources": [],
            "error": str(e),
            "ai_apis_status": "error"
        }


async def _sync_events_background(db: AsyncIOMotorDatabase, full_sync: bool = False):
    """
    Background task to sync events from AI APIs
    """
    sync_log = {
        "timestamp": datetime.utcnow(),
        "sync_type": "full" if full_sync else "incremental",
        "status": "started",
        "events_synced": 0,
        "sources_processed": [],
        "errors": []
    }
    
    try:
        # Initialize AI APIs pipeline
        config = AIConfig()
        orchestrator = PipelineOrchestrator(config)
        
        # Log sync start
        sync_log_id = await db.sync_logs.insert_one(sync_log)
        
        # Run the AI pipeline
        if full_sync:
            pipeline_result = await orchestrator.run_full_pipeline()
        else:
            pipeline_result = await orchestrator.run_incremental_update()
        
        # Process the results and store in MongoDB
        events_synced = 0
        sources_processed = []
        
        if pipeline_result.get("success", False):
            # Get events from the pipeline result
            enhanced_events = pipeline_result.get("enhanced_events", [])
            
            for event in enhanced_events:
                # Convert AI API event format to MongoDB format
                mongo_event = await _convert_ai_event_to_mongo(event)
                
                # Upsert event (insert or update if exists)
                await db.events.update_one(
                    {"source_id": mongo_event["source_id"]},
                    {"$set": mongo_event},
                    upsert=True
                )
                events_synced += 1
            
            sources_processed = pipeline_result.get("sources_processed", [])
            sync_log["status"] = "completed"
        else:
            sync_log["status"] = "failed"
            sync_log["errors"].append(pipeline_result.get("error", "Unknown error"))
        
        # Update sync log
        sync_log.update({
            "events_synced": events_synced,
            "sources_processed": sources_processed,
            "completed_at": datetime.utcnow()
        })
        
        await db.sync_logs.update_one(
            {"_id": sync_log_id.inserted_id},
            {"$set": sync_log}
        )
        
        print(f"✅ Sync completed: {events_synced} events from {len(sources_processed)} sources")
        
    except Exception as e:
        # Log error
        sync_log.update({
            "status": "error",
            "error": str(e),
            "completed_at": datetime.utcnow()
        })
        
        await db.sync_logs.insert_one(sync_log)
        print(f"❌ Sync failed: {e}")


async def _sync_specific_source_background(db: AsyncIOMotorDatabase, source_name: str):
    """
    Background task to sync events from a specific source
    """
    try:
        config = AIConfig()
        
        # Run scraping for specific source
        from integrations.ai_apis.firecrawl_client import FirecrawlClient
        firecrawl = FirecrawlClient(config)
        
        events = await firecrawl.scrape_source(source_name)
        
        events_synced = 0
        for event in events:
            mongo_event = await _convert_ai_event_to_mongo(event)
            await db.events.update_one(
                {"source_id": mongo_event["source_id"]},
                {"$set": mongo_event},
                upsert=True
            )
            events_synced += 1
        
        # Log the specific source sync
        await db.sync_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "sync_type": "manual",
            "source": source_name,
            "status": "completed",
            "events_synced": events_synced
        })
        
        print(f"✅ Manual sync completed for {source_name}: {events_synced} events")
        
    except Exception as e:
        await db.sync_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "sync_type": "manual",
            "source": source_name,
            "status": "error",
            "error": str(e)
        })
        print(f"❌ Manual sync failed for {source_name}: {e}")


async def _convert_ai_event_to_mongo(ai_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert AI API event format to MongoDB format compatible with the backend
    """
    # Extract family score from AI analysis
    family_score = 75  # Default
    if isinstance(ai_event.get("ai_analysis"), dict):
        family_analysis = ai_event["ai_analysis"].get("family_analysis", {})
        family_score = family_analysis.get("family_score", 75)
    
    # Convert to MongoDB event format
    mongo_event = {
        "source_id": ai_event.get("id", f"ai_{hash(ai_event.get('url', ''))}"),
        "title": ai_event.get("title", "").strip(),
        "description": ai_event.get("description", "").strip(),
        "content": ai_event.get("content", "").strip(),
        "url": ai_event.get("url", ""),
        "source_url": ai_event.get("source_url", ai_event.get("url", "")),
        
        # Event details
        "category": ai_event.get("category", "general"),
        "category_tags": [ai_event.get("category", "general")],
        "tags": ai_event.get("tags", []),
        
        # Dates (use placeholders if not available)
        "start_date": datetime.utcnow() + timedelta(days=7),  # Default to next week
        "end_date": datetime.utcnow() + timedelta(days=7, hours=2),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        
        # Location (default to Dubai)
        "area": "Dubai",
        "city": "Dubai",
        "location": {
            "type": "Point",
            "coordinates": [55.2744, 25.2048]  # Dubai coordinates
        },
        
        # Pricing (default to free)
        "price_min": 0,
        "price_max": 100,
        "currency": "AED",
        "is_free": True,
        
        # Family suitability
        "is_family_friendly": family_score > 60,
        "family_score": family_score,
        "age_min": 0,
        "age_max": 99,
        
        # Status and metrics
        "status": "active",
        "source": ai_event.get("source", "ai_scraped"),
        "source_name": ai_event.get("source_name", "AI Scraped"),
        "scraped_at": ai_event.get("scraped_at", datetime.utcnow().isoformat()),
        "view_count": 0,
        "save_count": 0,
        
        # AI enhancements
        "ai_enhanced": True,
        "ai_analysis": ai_event.get("ai_analysis", {}),
        "quality_score": ai_event.get("ai_analysis", {}).get("quality_assessment", {}).get("overall_score", 70),
        
        # Raw data for reference
        "raw_data": ai_event
    }
    
    return mongo_event 