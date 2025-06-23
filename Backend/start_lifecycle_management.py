#!/usr/bin/env python3
"""
DXB Events Lifecycle Management Startup Script

This script helps initialize and start the lifecycle management system
with proper setup, health checks, and monitoring.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from lifecycle_management import SourceBasedRetentionManager, StorageHealthMonitor
from lifecycle_management.celery_config import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def check_mongodb_connection():
    """Test MongoDB Atlas connection"""
    try:
        client = AsyncIOMotorClient(
            settings.mongodb_url,
            tls=True,
            tlsAllowInvalidCertificates=True  # For development/testing
        )
        db = client[settings.mongodb_database]
        
        # Test connection
        await client.admin.command('ping')
        
        # Check collections
        collections = await db.list_collection_names()
        
        logger.info(f"✅ MongoDB Atlas connected - Database: {settings.mongodb_database}")
        logger.info(f"📋 Available collections: {collections}")
        
        return client, db
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        return None, None

async def check_redis_connection():
    """Test Redis connection for Celery"""
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        logger.info("✅ Redis connected (Celery broker)")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False

async def setup_database_indexes(db):
    """Setup lifecycle management indexes"""
    try:
        # Events collection indexes for lifecycle management
        await db.events.create_index([("source", 1)])
        await db.events.create_index([("source_priority", 1)])
        await db.events.create_index([("delete_after", 1)])
        await db.events.create_index([("status", 1)])
        await db.events.create_index([("scraped_at", 1)])
        await db.events.create_index([("deleted_at", 1)])
        
        # Compound indexes for efficient cleanup queries
        await db.events.create_index([("end_date", 1), ("source", 1)])
        await db.events.create_index([("delete_after", 1), ("status", 1)])
        await db.events.create_index([("source_priority", 1), ("delete_after", 1), ("status", 1)])
        
        # Weekly stats collection indexes
        await db.weekly_stats.create_index([("week_start", 1)], unique=True)
        await db.weekly_stats.create_index([("recorded_at", 1)])
        
        logger.info("✅ Lifecycle management database indexes created")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database index creation failed: {e}")
        return False

async def initialize_retention_policies(db):
    """Initialize retention policies for existing events"""
    try:
        retention_manager = SourceBasedRetentionManager(db)
        
        # Setup automatic deletion for events without policies
        await retention_manager.setup_automatic_deletion()
        
        # Get statistics
        stats = await retention_manager.get_retention_stats()
        
        logger.info("✅ Retention policies initialized")
        logger.info(f"📊 Retention stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Retention policy initialization failed: {e}")
        return False

async def run_initial_health_check(db):
    """Run initial health check"""
    try:
        health_monitor = StorageHealthMonitor(db)
        
        # Check storage health
        health_status = await health_monitor.check_storage_health()
        
        # Get cost estimate
        cost_estimate = await health_monitor.calculate_storage_cost_estimate()
        
        logger.info(f"✅ Initial health check completed")
        logger.info(f"📊 Storage health: {health_status['status']}")
        logger.info(f"💰 Estimated monthly cost: ${cost_estimate['estimated_monthly_cost_usd']:.4f}")
        
        if health_status['alerts']:
            logger.warning(f"⚠️ Health alerts: {health_status['alerts']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Initial health check failed: {e}")
        return False

def test_celery_connection():
    """Test Celery task queue connection"""
    try:
        # Test basic Celery connection
        result = celery_app.control.inspect().active()
        logger.info("✅ Celery connection successful")
        
        # Try to send a test task
        task = celery_app.send_task('lifecycle_management.schedulers.cleanup_tasks.setup_retention_policies')
        logger.info(f"✅ Test task queued with ID: {task.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Celery connection failed: {e}")
        logger.warning("💡 Make sure Redis is running and Celery worker is started")
        return False

async def show_system_status(db):
    """Show comprehensive system status"""
    try:
        retention_manager = SourceBasedRetentionManager(db)
        health_monitor = StorageHealthMonitor(db)
        
        # Get retention stats
        retention_stats = await retention_manager.get_retention_stats()
        
        # Get detailed source stats
        source_stats = await health_monitor.get_detailed_source_stats()
        
        # Get cost estimate
        cost_estimate = await health_monitor.calculate_storage_cost_estimate()
        
        print("\n" + "="*80)
        print("🚀 DXB EVENTS LIFECYCLE MANAGEMENT - SYSTEM STATUS")
        print("="*80)
        
        print(f"\n📊 STORAGE OVERVIEW:")
        print(f"   Total Events: {cost_estimate['total_events']}")
        print(f"   Storage Size: {cost_estimate['estimated_storage_gb']:.4f} GB")
        print(f"   Monthly Cost: ${cost_estimate['estimated_monthly_cost_usd']:.4f}")
        
        print(f"\n🎯 SOURCE BREAKDOWN:")
        for source, stats in source_stats.items():
            print(f"   {source:<20} | Priority: {stats['priority']:<6} | Events: {stats['active_events']:<4}")
        
        print(f"\n⚙️ RETENTION POLICIES:")
        for priority, policy in retention_manager.retention_policies.items():
            sources_count = len(policy['sources'])
            print(f"   {priority.title():<8} Priority | {policy['retention_days']} days | {sources_count} sources")
        
        print(f"\n🔄 AUTOMATED TASKS:")
        print(f"   Daily Cleanup:      3:00 AM UAE")
        print(f"   Health Checks:      2:00 AM UAE") 
        print(f"   Weekly Reports:     Monday 4:00 AM UAE")
        print(f"   Retention Setup:    Every 4 hours")
        print(f"   Emergency Checks:   Every 6 hours")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"❌ System status display failed: {e}")

async def main():
    """Main initialization function"""
    print("🚀 Initializing DXB Events Lifecycle Management System...")
    print("=" * 60)
    
    # Step 1: Check MongoDB connection
    print("\n1️⃣ Checking MongoDB Atlas connection...")
    mongodb_client, db = await check_mongodb_connection()
    if db is None:
        print("❌ Cannot proceed without MongoDB connection")
        sys.exit(1)
    
    # Step 2: Check Redis connection
    print("\n2️⃣ Checking Redis connection...")
    redis_ok = await check_redis_connection()
    if not redis_ok:
        print("⚠️ Redis not available - Celery tasks will not work")
    
    # Step 3: Setup database indexes
    print("\n3️⃣ Setting up database indexes...")
    indexes_ok = await setup_database_indexes(db)
    if not indexes_ok:
        print("⚠️ Database index setup had issues")
    
    # Step 4: Initialize retention policies
    print("\n4️⃣ Initializing retention policies...")
    retention_ok = await initialize_retention_policies(db)
    if not retention_ok:
        print("⚠️ Retention policy initialization had issues")
    
    # Step 5: Run initial health check
    print("\n5️⃣ Running initial health check...")
    health_ok = await run_initial_health_check(db)
    if not health_ok:
        print("⚠️ Initial health check had issues")
    
    # Step 6: Test Celery connection
    print("\n6️⃣ Testing Celery task queue...")
    if redis_ok:
        celery_ok = test_celery_connection()
        if not celery_ok:
            print("⚠️ Celery connection issues - check if worker is running")
    
    # Step 7: Show system status
    print("\n7️⃣ Displaying system status...")
    await show_system_status(db)
    
    # Summary
    print(f"\n✅ INITIALIZATION COMPLETE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 NEXT STEPS:")
    print("   1. Start Celery worker: celery -A lifecycle_management.celery_config:celery_app worker --loglevel=info")
    print("   2. Start Celery beat: celery -A lifecycle_management.celery_config:celery_app beat --loglevel=info")  
    print("   3. Start FastAPI server: uvicorn main:app --reload")
    print("   4. Monitor via API: http://localhost:8000/lifecycle/health")
    
    # Close MongoDB connection
    mongodb_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Initialization interrupted by user")
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        sys.exit(1) 