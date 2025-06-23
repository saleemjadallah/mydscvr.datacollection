#!/usr/bin/env python3
"""
Perplexity Data Collection - Monitoring and Logging Configuration
Simplified monitoring system for the new Perplexity-only data collection pipeline
"""

import time
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from loguru import logger

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from config.perplexity_settings import get_settings, get_perplexity_api_key
except ImportError:
    # Fallback for backward compatibility
    print("Warning: Using legacy settings. Please migrate to config.perplexity_settings")
    from config.settings import get_settings


class PerplexityMonitoringSystem:
    """
    Simplified monitoring system for Perplexity-based data collection
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.health_checks = {}
        self.setup_logging()
    
    def setup_logging(self):
        """Configure loguru for the monitoring system"""
        # Remove default handler
        logger.remove()
        
        # Add console handler
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        
        # Add file handler
        log_file = Path("logs/perplexity_monitoring.log")
        log_file.parent.mkdir(exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip"
        )
        
        logger.info("📊 Perplexity monitoring system initialized")
    
    def check_perplexity_health(self) -> Dict[str, Any]:
        """Check Perplexity API connectivity with a minimal request"""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "service": "perplexity_api",
            "status": "unknown",
            "response_time_ms": None,
            "error": None,
            "details": {}
        }
        
        try:
            start_time = time.time()
            
            # Get API key safely
            try:
                api_key = get_perplexity_api_key()
            except Exception as e:
                health_data["status"] = "error"
                health_data["error"] = f"API key error: {str(e)}"
                return health_data
            
            # Simple health check with minimal request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "sonar",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response_time = (time.time() - start_time) * 1000
                health_data["response_time_ms"] = round(response_time, 2)
                
                if response.status_code == 200:
                    health_data["status"] = "healthy"
                    health_data["details"] = {
                        "status_code": response.status_code,
                        "response_size": len(response.content)
                    }
                else:
                    health_data["status"] = "error"
                    health_data["error"] = f"HTTP {response.status_code}: {response.text[:200]}"
                    health_data["details"] = {"status_code": response.status_code}
        
        except httpx.TimeoutException:
            health_data["status"] = "timeout"
            health_data["error"] = "Request timed out"
        except httpx.RequestError as e:
            health_data["status"] = "connection_error"
            health_data["error"] = f"Connection error: {str(e)}"
        except Exception as e:
            health_data["status"] = "error"
            health_data["error"] = f"Unexpected error: {str(e)}"
        
        # Store health check result
        self.health_checks["perplexity_api"] = health_data
        
        return health_data
    
    def check_mongodb_health(self) -> Dict[str, Any]:
        """Check MongoDB connectivity"""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "service": "mongodb",
            "status": "unknown",
            "response_time_ms": None,
            "error": None,
            "details": {}
        }
        
        try:
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
            
            start_time = time.time()
            
            # Get MongoDB config
            if hasattr(self.settings, 'mongodb_config'):
                mongo_config = self.settings.mongodb_config
                uri = mongo_config["uri"]
                db_name = mongo_config["database"]
            else:
                # Fallback for legacy settings
                uri = self.settings.MONGODB_CONNECTION_STRING
                db_name = self.settings.DATABASE_NAME
            
            # Test connection
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            
            # Test database access
            db = client[db_name]
            collections = db.list_collection_names()
            
            response_time = (time.time() - start_time) * 1000
            health_data["response_time_ms"] = round(response_time, 2)
            health_data["status"] = "healthy"
            health_data["details"] = {
                "database": db_name,
                "collections_count": len(collections),
                "collections": collections[:5]  # Show first 5 collections
            }
            
            client.close()
        
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            health_data["status"] = "connection_error"
            health_data["error"] = f"MongoDB connection failed: {str(e)}"
        except Exception as e:
            health_data["status"] = "error"
            health_data["error"] = f"MongoDB error: {str(e)}"
        
        # Store health check result
        self.health_checks["mongodb"] = health_data
        
        return health_data
    
    def run_all_health_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status"""
        logger.info("🔍 Running comprehensive health checks...")
        
        # Run health checks
        perplexity_health = self.check_perplexity_health()
        mongodb_health = self.check_mongodb_health()
        
        # Overall system status
        overall_status = "healthy"
        if perplexity_health["status"] != "healthy" or mongodb_health["status"] != "healthy":
            overall_status = "degraded"
        
        comprehensive_status = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "services": {
                "perplexity_api": perplexity_health,
                "mongodb": mongodb_health
            },
            "summary": {
                "total_services": 2,
                "healthy_services": sum(1 for s in [perplexity_health, mongodb_health] if s["status"] == "healthy"),
                "avg_response_time_ms": round(
                    sum(s.get("response_time_ms", 0) for s in [perplexity_health, mongodb_health] if s.get("response_time_ms")) / 2, 2
                ) if any(s.get("response_time_ms") for s in [perplexity_health, mongodb_health]) else None
            }
        }
        
        # Log results
        logger.info(f"📊 Health Check Results:")
        logger.info(f"   Overall Status: {overall_status.upper()}")
        logger.info(f"   Perplexity API: {perplexity_health['status'].upper()}")
        logger.info(f"   MongoDB: {mongodb_health['status'].upper()}")
        
        return comprehensive_status
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Perplexity Data Collection",
            "version": "2.0.0",
            "components": [
                "Perplexity AI API",
                "MongoDB Database",
                "Event Extraction Pipeline"
            ],
            "deprecated_components": [
                "Firecrawl (removed)",
                "Celery (removed)",
                "Redis (removed)",
                "Custom scrapers (removed)"
            ]
        }


def quick_health_check() -> bool:
    """Quick health check function for scripts"""
    try:
        monitor = PerplexityMonitoringSystem()
        results = monitor.run_all_health_checks()
        return results["overall_status"] == "healthy"
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False


def main():
    """Main function for running monitoring as a script"""
    print("🔍 Perplexity Data Collection - Health Monitor")
    print("=" * 50)
    
    monitor = PerplexityMonitoringSystem()
    
    # System info
    info = monitor.get_system_info()
    print(f"System: {info['system']} v{info['version']}")
    print(f"Timestamp: {info['timestamp']}")
    print()
    
    # Health checks
    results = monitor.run_all_health_checks()
    
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Services: {results['summary']['healthy_services']}/{results['summary']['total_services']} healthy")
    
    if results['summary']['avg_response_time_ms']:
        print(f"Average Response Time: {results['summary']['avg_response_time_ms']}ms")
    
    print("\nService Details:")
    for service, details in results['services'].items():
        status_emoji = "✅" if details['status'] == 'healthy' else "❌"
        print(f"  {status_emoji} {service}: {details['status']}")
        if details.get('error'):
            print(f"    Error: {details['error']}")
        if details.get('response_time_ms'):
            print(f"    Response Time: {details['response_time_ms']}ms")


if __name__ == "__main__":
    main() 