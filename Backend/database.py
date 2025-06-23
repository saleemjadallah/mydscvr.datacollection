from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch
from config import settings
import logging

# MongoDB Atlas (Primary database for all data)
mongodb_client = AsyncIOMotorClient(
    settings.mongodb_url,
    tls=True,
    tlsAllowInvalidCertificates=True  # For development/testing
)
mongodb = mongodb_client[settings.mongodb_database]  # Use the specific DXB database

# Redis (For caching and sessions) - Optional
try:
    redis_client = redis.from_url(settings.redis_url)
except Exception as e:
    print(f"⚠️ Redis not available (caching disabled): {e}")
    redis_client = None

# Elasticsearch (For search capabilities) - Optional
elasticsearch_client = None


# Dependency to get MongoDB database
async def get_mongodb():
    return mongodb


# Dependency to get Redis client
async def get_redis():
    return redis_client


# Dependency to get Elasticsearch client
async def get_elasticsearch():
    if elasticsearch_client is None:
        # Try to reconnect
        await connect_elasticsearch()
    return elasticsearch_client


# Database initialization
async def init_databases():
    """Initialize all databases and create indexes"""
    try:
        # Test MongoDB Atlas connection (required)
        await mongodb_client.admin.command('ping')
        print(f"✅ MongoDB Atlas connected successfully to database: {settings.mongodb_database}")
        
        # Create MongoDB indexes
        await create_mongodb_indexes()
        
    except Exception as e:
        print(f"❌ MongoDB Atlas connection failed: {e}")
        raise  # MongoDB is required
    
    # Test Redis connection (optional)
    try:
        await redis_client.ping()
        print("✅ Redis connected successfully")
    except Exception as e:
        print(f"⚠️ Redis connection failed (optional for development): {e}")
    
    # Test Elasticsearch connection (optional)
    try:
        await elasticsearch_client.info()
        print("✅ Elasticsearch connected successfully")
        # Create Elasticsearch indexes (if available)
        await create_elasticsearch_indexes()
    except Exception as e:
        print(f"⚠️ Elasticsearch connection failed (optional for development): {e}")


async def create_mongodb_indexes():
    """Create indexes for MongoDB collections"""
    try:
        # Events collection indexes
        await mongodb.events.create_index([("title", "text"), ("description", "text")])
        await mongodb.events.create_index([("location", "2dsphere")])
        await mongodb.events.create_index([("start_date", 1)])
        await mongodb.events.create_index([("category_tags", 1)])
        await mongodb.events.create_index([("price_min", 1), ("price_max", 1)])
        await mongodb.events.create_index([("is_family_friendly", 1)])
        await mongodb.events.create_index([("area", 1)])
        await mongodb.events.create_index([("source_name", 1)])
        
        # Lifecycle Management indexes
        await mongodb.events.create_index([("source", 1)])
        await mongodb.events.create_index([("source_priority", 1)])
        await mongodb.events.create_index([("delete_after", 1)])
        await mongodb.events.create_index([("status", 1)])
        await mongodb.events.create_index([("scraped_at", 1)])
        await mongodb.events.create_index([("deleted_at", 1)])
        
        # Compound indexes for efficient cleanup queries
        await mongodb.events.create_index([("end_date", 1), ("source", 1)])
        await mongodb.events.create_index([("delete_after", 1), ("status", 1)])
        await mongodb.events.create_index([("source_priority", 1), ("delete_after", 1), ("status", 1)])
        
        # Venues collection indexes
        await mongodb.venues.create_index([("location", "2dsphere")])
        await mongodb.venues.create_index([("area", 1)])
        await mongodb.venues.create_index([("name", 1)])
        
        # Weekly stats collection indexes for monitoring
        await mongodb.weekly_stats.create_index([("week_start", 1)], unique=True)
        await mongodb.weekly_stats.create_index([("recorded_at", 1)])
        
        # User authentication collection indexes
        await mongodb.users.create_index([("email", 1)], unique=True)
        await mongodb.users.create_index([("created_at", 1)])
        await mongodb.users.create_index([("is_active", 1)])
        await mongodb.users.create_index([("onboarding_completed", 1)])
        
        # User sessions collection indexes
        await mongodb.user_sessions.create_index([("session_token", 1)], unique=True)
        await mongodb.user_sessions.create_index([("user_id", 1)])
        await mongodb.user_sessions.create_index([("expires_at", 1)], expireAfterSeconds=0)
        
        print("✅ MongoDB indexes created successfully (including lifecycle management and user auth)")
    except Exception as e:
        print(f"⚠️ MongoDB indexing warning: {e}")


async def create_elasticsearch_indexes():
    """Create Elasticsearch indexes for search"""
    events_mapping = {
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "standard"},
                "description": {"type": "text", "analyzer": "standard"},
                "category_tags": {"type": "keyword"},
                "area": {"type": "keyword"},
                "price_min": {"type": "integer"},
                "price_max": {"type": "integer"},
                "start_date": {"type": "date"},
                "end_date": {"type": "date"},
                "age_min": {"type": "integer"},
                "age_max": {"type": "integer"},
                "is_family_friendly": {"type": "boolean"},
                "location": {"type": "geo_point"},
                "venue_name": {"type": "text"},
                "family_score": {"type": "integer"}
            }
        }
    }
    
    # Create events index
    if not await elasticsearch_client.indices.exists(index="events"):
        await elasticsearch_client.indices.create(index="events", body=events_mapping)
        print("✅ Elasticsearch events index created")


async def close_databases():
    """Close all database connections"""
    try:
        mongodb_client.close()
        await redis_client.close()
        await elasticsearch_client.close()
        print("✅ All database connections closed")
    except Exception as e:
        print(f"⚠️ Error closing connections: {e}")


# Helper function to test MongoDB connection
async def test_mongodb_connection():
    """Test MongoDB Atlas connection and list collections"""
    try:
        # Test connection
        await mongodb_client.admin.command('ping')
        
        # List existing collections
        collections = await mongodb.list_collection_names()
        
        return {
            "status": "connected",
            "database": settings.mongodb_database,
            "collections": collections,
            "connection_string": settings.mongodb_url.replace("olaabdel88", "***")  # Hide password
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }


async def connect_elasticsearch():
    """Connect to Elasticsearch"""
    global elasticsearch_client
    try:
        # Try to connect to Elasticsearch
        elasticsearch_client = AsyncElasticsearch([settings.elasticsearch_url])
        
        # Test connection
        info = await elasticsearch_client.info()
        print(f"✅ Elasticsearch connected: {info['version']['number']}")
        return True
    except Exception as e:
        print(f"⚠️ Elasticsearch connection failed (optional for development): {e}")
        elasticsearch_client = None
        return False


 