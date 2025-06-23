"""
Performance Monitoring System
Tracks system performance, API costs, and processing metrics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import time
import psutil
import os

from config.database_schema import get_mongodb_connection
from config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_processes: int


@dataclass
class ScrapingMetrics:
    source: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    total_events_scraped: int
    success_rate: float
    last_updated: datetime


@dataclass
class ProcessingMetrics:
    total_events_processed: int
    avg_processing_time: float
    ai_processing_calls: int
    ai_processing_cost: float
    errors_count: int
    queue_backlog: int
    throughput_per_hour: float
    last_updated: datetime


@dataclass
class SyncMetrics:
    mongodb_syncs: int
    mongodb_failures: int
    backend_notifications: int
    backend_failures: int
    sync_success_rate: float
    avg_sync_time: float
    last_updated: datetime


class PerformanceMonitor:
    def __init__(self):
        self.mongodb = None
        self.metrics_collection = 'performance_metrics'
        self.start_time = datetime.now()
        
    async def __aenter__(self):
        self.mongodb = await get_mongodb_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.mongodb:
            self.mongodb.close()

    async def track_system_metrics(self) -> PerformanceMetrics:
        """Track system-level performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Active processes
            active_processes = len(psutil.pids())
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_percent,
                memory_usage=memory_percent,
                disk_usage=disk_percent,
                network_io=network_io,
                active_processes=active_processes
            )
            
            # Store in MongoDB
            if self.mongodb:
                await self.mongodb[self.metrics_collection].insert_one({
                    'type': 'system_metrics',
                    'timestamp': metrics.timestamp,
                    'data': asdict(metrics)
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error tracking system metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_usage=0, memory_usage=0, disk_usage=0,
                network_io={}, active_processes=0
            )

    async def track_scraping_metrics(self, hours: int = 24) -> Dict[str, ScrapingMetrics]:
        """Track scraping performance by source"""
        if not self.mongodb:
            return {}
        
        since = datetime.now() - timedelta(hours=hours)
        sources_metrics = {}
        
        try:
            # Get scraping activity by source
            pipeline = [
                {'$match': {'scraped_at': {'$gte': since}}},
                {'$group': {
                    '_id': '$source',
                    'total_requests': {'$sum': 1},
                    'successful_requests': {
                        '$sum': {'$cond': [{'$ne': ['$status', 'error']}, 1, 0]}
                    },
                    'failed_requests': {
                        '$sum': {'$cond': [{'$eq': ['$status', 'error']}, 1, 0]}
                    },
                    'total_events': {'$sum': {'$size': {'$ifNull': ['$events', []]}}},
                    'avg_response_time': {'$avg': '$response_time'},
                    'last_updated': {'$max': '$scraped_at'}
                }}
            ]
            
            cursor = self.mongodb.raw_events.aggregate(pipeline)
            async for source_data in cursor:
                source = source_data['_id']
                total_requests = source_data['total_requests']
                successful_requests = source_data['successful_requests']
                
                success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
                
                sources_metrics[source] = ScrapingMetrics(
                    source=source,
                    total_requests=total_requests,
                    successful_requests=successful_requests,
                    failed_requests=source_data['failed_requests'],
                    avg_response_time=source_data.get('avg_response_time', 0) or 0,
                    total_events_scraped=source_data.get('total_events', 0),
                    success_rate=round(success_rate, 2),
                    last_updated=source_data.get('last_updated', datetime.now())
                )
            
            # Store aggregated metrics
            await self.mongodb[self.metrics_collection].insert_one({
                'type': 'scraping_metrics',
                'timestamp': datetime.now(),
                'period_hours': hours,
                'data': {source: asdict(metrics) for source, metrics in sources_metrics.items()}
            })
            
        except Exception as e:
            logger.error(f"Error tracking scraping metrics: {e}")
        
        return sources_metrics

    async def track_processing_metrics(self, hours: int = 24) -> ProcessingMetrics:
        """Track AI processing and event processing performance"""
        if not self.mongodb:
            return ProcessingMetrics(0, 0, 0, 0, 0, 0, 0, datetime.now())
        
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            # Count processed events
            total_processed = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since}
            })
            
            # Calculate average processing time
            pipeline = [
                {'$match': {'processed_at': {'$gte': since}, 'processing_time': {'$exists': True}}},
                {'$group': {
                    '_id': None,
                    'avg_processing_time': {'$avg': '$processing_time'},
                    'ai_calls': {'$sum': '$ai_processing_calls'},
                    'total_cost': {'$sum': '$ai_processing_cost'}
                }}
            ]
            
            result = await self.mongodb.processed_events.aggregate(pipeline).to_list(1)
            
            avg_processing_time = 0
            ai_calls = 0
            total_cost = 0
            
            if result:
                avg_processing_time = result[0].get('avg_processing_time', 0) or 0
                ai_calls = result[0].get('ai_calls', 0) or 0
                total_cost = result[0].get('total_cost', 0) or 0
            
            # Count errors
            errors_count = await self.mongodb.raw_events.count_documents({
                'scraped_at': {'$gte': since},
                'status': 'error'
            })
            
            # Calculate queue backlog
            queue_backlog = await self.mongodb.raw_events.count_documents({
                'status': 'pending_processing'
            })
            
            # Calculate throughput
            throughput_per_hour = (total_processed / hours) if hours > 0 else 0
            
            metrics = ProcessingMetrics(
                total_events_processed=total_processed,
                avg_processing_time=round(avg_processing_time, 2),
                ai_processing_calls=ai_calls,
                ai_processing_cost=round(total_cost, 4),
                errors_count=errors_count,
                queue_backlog=queue_backlog,
                throughput_per_hour=round(throughput_per_hour, 2),
                last_updated=datetime.now()
            )
            
            # Store metrics
            await self.mongodb[self.metrics_collection].insert_one({
                'type': 'processing_metrics',
                'timestamp': datetime.now(),
                'period_hours': hours,
                'data': asdict(metrics)
            })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error tracking processing metrics: {e}")
            return ProcessingMetrics(0, 0, 0, 0, 0, 0, 0, datetime.now())

    async def track_sync_metrics(self, hours: int = 24) -> SyncMetrics:
        """Track backend synchronization performance"""
        if not self.mongodb:
            return SyncMetrics(0, 0, 0, 0, 0, 0, datetime.now())
        
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            # MongoDB sync metrics
            mongodb_syncs = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since},
                'mongodb_sync_status': 'completed'
            })
            
            mongodb_failures = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since},
                'mongodb_sync_status': 'failed'
            })
            
            # Backend notification metrics
            backend_notifications = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since},
                'backend_notification_status': 'sent'
            })
            
            backend_failures = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since},
                'backend_notification_status': 'failed'
            })
            
            # Calculate sync success rate
            total_syncs = mongodb_syncs + mongodb_failures
            sync_success_rate = (mongodb_syncs / total_syncs * 100) if total_syncs > 0 else 100
            
            # Calculate average sync time
            pipeline = [
                {'$match': {
                    'processed_at': {'$gte': since},
                    'sync_time': {'$exists': True}
                }},
                {'$group': {
                    '_id': None,
                    'avg_sync_time': {'$avg': '$sync_time'}
                }}
            ]
            
            result = await self.mongodb.processed_events.aggregate(pipeline).to_list(1)
            avg_sync_time = result[0].get('avg_sync_time', 0) if result else 0
            
            metrics = SyncMetrics(
                mongodb_syncs=mongodb_syncs,
                mongodb_failures=mongodb_failures,
                backend_notifications=backend_notifications,
                backend_failures=backend_failures,
                sync_success_rate=round(sync_success_rate, 2),
                avg_sync_time=round(avg_sync_time or 0, 2),
                last_updated=datetime.now()
            )
            
            # Store metrics
            await self.mongodb[self.metrics_collection].insert_one({
                'type': 'sync_metrics',
                'timestamp': datetime.now(),
                'period_hours': hours,
                'data': asdict(metrics)
            })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error tracking sync metrics: {e}")
            return SyncMetrics(0, 0, 0, 0, 0, 0, datetime.now())

    async def track_ai_processing_costs(self, hours: int = 24) -> Dict:
        """Track AI processing costs and usage"""
        if not self.mongodb:
            return {}
        
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            pipeline = [
                {'$match': {'processed_at': {'$gte': since}}},
                {'$group': {
                    '_id': None,
                    'total_ai_calls': {'$sum': '$ai_processing_calls'},
                    'total_cost': {'$sum': '$ai_processing_cost'},
                    'avg_cost_per_event': {'$avg': '$ai_processing_cost'},
                    'events_with_ai': {'$sum': 1}
                }}
            ]
            
            result = await self.mongodb.processed_events.aggregate(pipeline).to_list(1)
            
            if not result:
                return {
                    'total_ai_calls': 0,
                    'total_cost': 0,
                    'avg_cost_per_event': 0,
                    'events_processed': 0,
                    'estimated_monthly_cost': 0
                }
            
            data = result[0]
            total_cost = data.get('total_cost', 0) or 0
            
            # Estimate monthly cost
            daily_cost = total_cost * (24 / hours) if hours > 0 else 0
            estimated_monthly_cost = daily_cost * 30
            
            cost_metrics = {
                'period_hours': hours,
                'total_ai_calls': data.get('total_ai_calls', 0),
                'total_cost': round(total_cost, 4),
                'avg_cost_per_event': round(data.get('avg_cost_per_event', 0) or 0, 6),
                'events_processed': data.get('events_with_ai', 0),
                'estimated_daily_cost': round(daily_cost, 4),
                'estimated_monthly_cost': round(estimated_monthly_cost, 2),
                'cost_efficiency': 'good' if daily_cost < 3.33 else 'moderate' if daily_cost < 6.67 else 'high',
                'timestamp': datetime.now().isoformat()
            }
            
            # Store cost metrics
            await self.mongodb[self.metrics_collection].insert_one({
                'type': 'ai_cost_metrics',
                'timestamp': datetime.now(),
                'period_hours': hours,
                'data': cost_metrics
            })
            
            return cost_metrics
            
        except Exception as e:
            logger.error(f"Error tracking AI costs: {e}")
            return {}

    async def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        try:
            # Get recent metrics
            system_metrics = await self.track_system_metrics()
            scraping_metrics = await self.track_scraping_metrics(24)
            processing_metrics = await self.track_processing_metrics(24)
            sync_metrics = await self.track_sync_metrics(24)
            cost_metrics = await self.track_ai_processing_costs(24)
            
            # Calculate overall health score
            health_factors = []
            
            # System health (25%)
            system_score = 100 - max(0, system_metrics.cpu_usage - 70) - max(0, system_metrics.memory_usage - 80)
            health_factors.append(('system', system_score * 0.25))
            
            # Scraping health (25%)
            scraping_scores = [metrics.success_rate for metrics in scraping_metrics.values()]
            avg_scraping_score = sum(scraping_scores) / len(scraping_scores) if scraping_scores else 100
            health_factors.append(('scraping', avg_scraping_score * 0.25))
            
            # Processing health (25%)
            processing_score = 100 - min(50, processing_metrics.queue_backlog * 2)  # Penalize backlog
            health_factors.append(('processing', processing_score * 0.25))
            
            # Sync health (25%)
            health_factors.append(('sync', sync_metrics.sync_success_rate * 0.25))
            
            overall_health = sum(score for _, score in health_factors)
            
            return {
                'overall_health_score': round(overall_health, 2),
                'health_status': (
                    'excellent' if overall_health >= 90 else
                    'good' if overall_health >= 75 else
                    'degraded' if overall_health >= 50 else
                    'critical'
                ),
                'system_metrics': asdict(system_metrics),
                'scraping_summary': {
                    'total_sources': len(scraping_metrics),
                    'avg_success_rate': round(sum(m.success_rate for m in scraping_metrics.values()) / len(scraping_metrics), 2) if scraping_metrics else 0,
                    'total_events_scraped': sum(m.total_events_scraped for m in scraping_metrics.values())
                },
                'processing_summary': asdict(processing_metrics),
                'sync_summary': asdict(sync_metrics),
                'cost_summary': cost_metrics,
                'uptime_hours': round((datetime.now() - self.start_time).total_seconds() / 3600, 2),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    async def get_historical_metrics(self, metric_type: str, hours: int = 168) -> List[Dict]:
        """Get historical metrics for trending analysis"""
        if not self.mongodb:
            return []
        
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            cursor = self.mongodb[self.metrics_collection].find({
                'type': metric_type,
                'timestamp': {'$gte': since}
            }).sort('timestamp', 1)
            
            metrics = await cursor.to_list(length=None)
            return metrics
            
        except Exception as e:
            logger.error(f"Error fetching historical metrics: {e}")
            return []

    async def cleanup_old_metrics(self, days: int = 30):
        """Clean up old performance metrics"""
        if not self.mongodb:
            return
        
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            result = await self.mongodb[self.metrics_collection].delete_many({
                'timestamp': {'$lt': cutoff}
            })
            logger.info(f"Cleaned up {result.deleted_count} old performance metrics")
        except Exception as e:
            logger.error(f"Error cleaning up metrics: {e}")


class PerformanceTracker:
    """Context manager for tracking operation performance"""
    
    def __init__(self, operation_name: str, mongodb=None):
        self.operation_name = operation_name
        self.mongodb = mongodb
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        logger.info(f"Operation '{self.operation_name}' completed in {duration:.2f} seconds")
        
        # Store performance data
        if self.mongodb:
            asyncio.create_task(self._store_performance_data(duration, exc_type is None))
    
    async def _store_performance_data(self, duration: float, success: bool):
        """Store operation performance data"""
        try:
            await self.mongodb.operation_performance.insert_one({
                'operation': self.operation_name,
                'duration': duration,
                'success': success,
                'timestamp': datetime.now()
            })
        except Exception as e:
            logger.error(f"Error storing performance data: {e}")


# Utility functions
async def track_api_call_performance(api_name: str, duration: float, success: bool, cost: float = 0):
    """Track individual API call performance"""
    try:
        mongodb = await get_mongodb_connection()
        await mongodb.api_call_metrics.insert_one({
            'api': api_name,
            'duration': duration,
            'success': success,
            'cost': cost,
            'timestamp': datetime.now()
        })
        mongodb.close()
    except Exception as e:
        logger.error(f"Error tracking API call performance: {e}")