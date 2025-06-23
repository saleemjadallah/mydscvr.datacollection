"""
Alert System for Data Collection Pipeline
Monitors critical failures and sends notifications
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import json

from config.database_schema import get_mongodb_connection
from config.logging_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(Enum):
    SCRAPING_FAILURE = "scraping_failure"
    PROCESSING_BACKLOG = "processing_backlog"
    SYNC_FAILURE = "sync_failure"
    QUALITY_DEGRADATION = "quality_degradation"
    SYSTEM_RESOURCE = "system_resource"
    API_COST_SPIKE = "api_cost_spike"
    DATA_ANOMALY = "data_anomaly"


@dataclass
class Alert:
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime
    metadata: Dict = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertSystem:
    def __init__(self):
        self.mongodb = None
        self.settings = get_settings()
        self.alert_handlers = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [self._log_alert],
            AlertLevel.ERROR: [self._log_alert, self._store_alert],
            AlertLevel.CRITICAL: [self._log_alert, self._store_alert, self._send_email_alert]
        }
        
        # Alert thresholds
        self.thresholds = {
            'scraping_failure_hours': 2,
            'processing_backlog_size': 100,
            'sync_failure_rate': 50,  # percentage
            'quality_score_threshold': 60,
            'cpu_usage_threshold': 85,
            'memory_usage_threshold': 90,
            'disk_usage_threshold': 95,
            'daily_cost_threshold': 10.0,
            'error_rate_threshold': 20  # percentage
        }
        
        # Rate limiting for alerts
        self.alert_cooldowns = {}
        self.cooldown_periods = {
            AlertType.SCRAPING_FAILURE: timedelta(hours=1),
            AlertType.PROCESSING_BACKLOG: timedelta(minutes=30),
            AlertType.SYNC_FAILURE: timedelta(minutes=15),
            AlertType.QUALITY_DEGRADATION: timedelta(hours=2),
            AlertType.SYSTEM_RESOURCE: timedelta(minutes=10),
            AlertType.API_COST_SPIKE: timedelta(hours=4),
            AlertType.DATA_ANOMALY: timedelta(hours=1)
        }
    
    async def __aenter__(self):
        self.mongodb = await get_mongodb_connection()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.mongodb:
            self.mongodb.close()

    async def check_scraping_failures(self) -> List[Alert]:
        """Check for scraping failures across sources"""
        if not self.mongodb:
            return []
        
        alerts = []
        failure_threshold = datetime.now() - timedelta(hours=self.thresholds['scraping_failure_hours'])
        
        try:
            # Check each source for recent successful scraping
            pipeline = [
                {'$match': {'scraped_at': {'$gte': failure_threshold}}},
                {'$group': {
                    '_id': '$source',
                    'last_success': {
                        '$max': {
                            '$cond': [
                                {'$ne': ['$status', 'error']},
                                '$scraped_at',
                                None
                            ]
                        }
                    },
                    'total_attempts': {'$sum': 1},
                    'failed_attempts': {
                        '$sum': {'$cond': [{'$eq': ['$status', 'error']}, 1, 0]}
                    }
                }}
            ]
            
            cursor = self.mongodb.raw_events.aggregate(pipeline)
            async for source_data in cursor:
                source = source_data['_id']
                last_success = source_data.get('last_success')
                failed_attempts = source_data.get('failed_attempts', 0)
                total_attempts = source_data.get('total_attempts', 0)
                
                # Check if no successful scraping in threshold period
                if not last_success or last_success < failure_threshold:
                    alert = Alert(
                        alert_type=AlertType.SCRAPING_FAILURE,
                        level=AlertLevel.CRITICAL,
                        title=f"Scraping Failure: {source}",
                        message=f"No successful scraping from {source} in the last {self.thresholds['scraping_failure_hours']} hours",
                        source=source,
                        timestamp=datetime.now(),
                        metadata={
                            'source': source,
                            'last_success': last_success.isoformat() if last_success else None,
                            'failed_attempts': failed_attempts,
                            'total_attempts': total_attempts
                        }
                    )
                    
                    if await self._should_send_alert(alert):
                        alerts.append(alert)
                
                # Check high failure rate
                elif total_attempts > 0:
                    failure_rate = (failed_attempts / total_attempts) * 100
                    if failure_rate > self.thresholds['error_rate_threshold']:
                        alert = Alert(
                            alert_type=AlertType.SCRAPING_FAILURE,
                            level=AlertLevel.ERROR,
                            title=f"High Scraping Error Rate: {source}",
                            message=f"Scraping error rate for {source} is {failure_rate:.1f}% (threshold: {self.thresholds['error_rate_threshold']}%)",
                            source=source,
                            timestamp=datetime.now(),
                            metadata={
                                'source': source,
                                'failure_rate': failure_rate,
                                'failed_attempts': failed_attempts,
                                'total_attempts': total_attempts
                            }
                        )
                        
                        if await self._should_send_alert(alert):
                            alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error checking scraping failures: {e}")
        
        return alerts

    async def check_processing_backlog(self) -> List[Alert]:
        """Check for processing queue backlog"""
        if not self.mongodb:
            return []
        
        alerts = []
        
        try:
            # Count pending events
            pending_count = await self.mongodb.raw_events.count_documents({
                'status': 'pending_processing'
            })
            
            if pending_count > self.thresholds['processing_backlog_size']:
                alert = Alert(
                    alert_type=AlertType.PROCESSING_BACKLOG,
                    level=AlertLevel.ERROR if pending_count < self.thresholds['processing_backlog_size'] * 2 else AlertLevel.CRITICAL,
                    title="Processing Queue Backlog",
                    message=f"Processing queue has {pending_count} pending events (threshold: {self.thresholds['processing_backlog_size']})",
                    source="processing_system",
                    timestamp=datetime.now(),
                    metadata={
                        'pending_count': pending_count,
                        'threshold': self.thresholds['processing_backlog_size']
                    }
                )
                
                if await self._should_send_alert(alert):
                    alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error checking processing backlog: {e}")
        
        return alerts

    async def check_sync_failures(self) -> List[Alert]:
        """Check for backend sync failures"""
        if not self.mongodb:
            return []
        
        alerts = []
        since = datetime.now() - timedelta(hours=1)
        
        try:
            # Count sync attempts and failures
            total_syncs = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since}
            })
            
            failed_syncs = await self.mongodb.processed_events.count_documents({
                'processed_at': {'$gte': since},
                'mongodb_sync_status': 'failed'
            })
            
            if total_syncs > 0:
                failure_rate = (failed_syncs / total_syncs) * 100
                
                if failure_rate > self.thresholds['sync_failure_rate']:
                    alert = Alert(
                        alert_type=AlertType.SYNC_FAILURE,
                        level=AlertLevel.CRITICAL if failure_rate > 80 else AlertLevel.ERROR,
                        title="High Sync Failure Rate",
                        message=f"MongoDB sync failure rate is {failure_rate:.1f}% in the last hour (threshold: {self.thresholds['sync_failure_rate']}%)",
                        source="sync_system",
                        timestamp=datetime.now(),
                        metadata={
                            'failure_rate': failure_rate,
                            'failed_syncs': failed_syncs,
                            'total_syncs': total_syncs
                        }
                    )
                    
                    if await self._should_send_alert(alert):
                        alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error checking sync failures: {e}")
        
        return alerts

    async def check_quality_degradation(self) -> List[Alert]:
        """Check for data quality issues"""
        if not self.mongodb:
            return []
        
        alerts = []
        since = datetime.now() - timedelta(hours=4)
        
        try:
            # Calculate average quality score for recent events
            pipeline = [
                {'$match': {
                    'processed_at': {'$gte': since},
                    'quality_score': {'$exists': True}
                }},
                {'$group': {
                    '_id': None,
                    'avg_quality': {'$avg': '$quality_score'},
                    'low_quality_count': {
                        '$sum': {
                            '$cond': [
                                {'$lt': ['$quality_score', self.thresholds['quality_score_threshold']]},
                                1, 0
                            ]
                        }
                    },
                    'total_count': {'$sum': 1}
                }}
            ]
            
            result = await self.mongodb.processed_events.aggregate(pipeline).to_list(1)
            
            if result:
                data = result[0]
                avg_quality = data.get('avg_quality', 100)
                low_quality_count = data.get('low_quality_count', 0)
                total_count = data.get('total_count', 0)
                
                if avg_quality < self.thresholds['quality_score_threshold']:
                    alert = Alert(
                        alert_type=AlertType.QUALITY_DEGRADATION,
                        level=AlertLevel.WARNING if avg_quality > 50 else AlertLevel.ERROR,
                        title="Data Quality Degradation",
                        message=f"Average data quality score dropped to {avg_quality:.1f} (threshold: {self.thresholds['quality_score_threshold']})",
                        source="quality_system",
                        timestamp=datetime.now(),
                        metadata={
                            'avg_quality': avg_quality,
                            'low_quality_count': low_quality_count,
                            'total_count': total_count,
                            'low_quality_percentage': (low_quality_count / total_count * 100) if total_count > 0 else 0
                        }
                    )
                    
                    if await self._should_send_alert(alert):
                        alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error checking quality degradation: {e}")
        
        return alerts

    async def check_system_resources(self) -> List[Alert]:
        """Check system resource usage"""
        alerts = []
        
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.thresholds['cpu_usage_threshold']:
                alert = Alert(
                    alert_type=AlertType.SYSTEM_RESOURCE,
                    level=AlertLevel.CRITICAL if cpu_percent > 95 else AlertLevel.ERROR,
                    title="High CPU Usage",
                    message=f"CPU usage is {cpu_percent}% (threshold: {self.thresholds['cpu_usage_threshold']}%)",
                    source="system",
                    timestamp=datetime.now(),
                    metadata={'cpu_usage': cpu_percent}
                )
                
                if await self._should_send_alert(alert):
                    alerts.append(alert)
            
            # Memory usage
            memory = psutil.virtual_memory()
            if memory.percent > self.thresholds['memory_usage_threshold']:
                alert = Alert(
                    alert_type=AlertType.SYSTEM_RESOURCE,
                    level=AlertLevel.CRITICAL if memory.percent > 95 else AlertLevel.ERROR,
                    title="High Memory Usage",
                    message=f"Memory usage is {memory.percent}% (threshold: {self.thresholds['memory_usage_threshold']}%)",
                    source="system",
                    timestamp=datetime.now(),
                    metadata={'memory_usage': memory.percent, 'available_gb': memory.available / (1024**3)}
                )
                
                if await self._should_send_alert(alert):
                    alerts.append(alert)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            if disk.percent > self.thresholds['disk_usage_threshold']:
                alert = Alert(
                    alert_type=AlertType.SYSTEM_RESOURCE,
                    level=AlertLevel.CRITICAL,
                    title="High Disk Usage",
                    message=f"Disk usage is {disk.percent}% (threshold: {self.thresholds['disk_usage_threshold']}%)",
                    source="system",
                    timestamp=datetime.now(),
                    metadata={'disk_usage': disk.percent, 'free_gb': disk.free / (1024**3)}
                )
                
                if await self._should_send_alert(alert):
                    alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
        
        return alerts

    async def check_api_cost_spike(self) -> List[Alert]:
        """Check for unexpected AI API cost spikes"""
        if not self.mongodb:
            return []
        
        alerts = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            # Calculate today's AI costs
            pipeline = [
                {'$match': {
                    'processed_at': {'$gte': today},
                    'ai_processing_cost': {'$exists': True}
                }},
                {'$group': {
                    '_id': None,
                    'total_cost': {'$sum': '$ai_processing_cost'},
                    'avg_cost': {'$avg': '$ai_processing_cost'},
                    'max_cost': {'$max': '$ai_processing_cost'},
                    'event_count': {'$sum': 1}
                }}
            ]
            
            result = await self.mongodb.processed_events.aggregate(pipeline).to_list(1)
            
            if result:
                data = result[0]
                total_cost = data.get('total_cost', 0)
                
                if total_cost > self.thresholds['daily_cost_threshold']:
                    alert = Alert(
                        alert_type=AlertType.API_COST_SPIKE,
                        level=AlertLevel.WARNING if total_cost < self.thresholds['daily_cost_threshold'] * 2 else AlertLevel.ERROR,
                        title="High AI Processing Costs",
                        message=f"Today's AI processing costs: ${total_cost:.2f} (threshold: ${self.thresholds['daily_cost_threshold']})",
                        source="ai_processing",
                        timestamp=datetime.now(),
                        metadata={
                            'total_cost': total_cost,
                            'avg_cost_per_event': data.get('avg_cost', 0),
                            'max_cost_per_event': data.get('max_cost', 0),
                            'events_processed': data.get('event_count', 0),
                            'estimated_monthly_cost': total_cost * 30
                        }
                    )
                    
                    if await self._should_send_alert(alert):
                        alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error checking API costs: {e}")
        
        return alerts

    async def _should_send_alert(self, alert: Alert) -> bool:
        """Check if alert should be sent (rate limiting)"""
        alert_key = f"{alert.alert_type.value}:{alert.source}"
        cooldown_period = self.cooldown_periods.get(alert.alert_type, timedelta(hours=1))
        
        if alert_key in self.alert_cooldowns:
            last_sent = self.alert_cooldowns[alert_key]
            if datetime.now() - last_sent < cooldown_period:
                return False
        
        self.alert_cooldowns[alert_key] = datetime.now()
        return True

    async def _log_alert(self, alert: Alert):
        """Log alert to console/file"""
        level_map = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }
        
        log_func = level_map.get(alert.level, logger.info)
        log_func(f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}")

    async def _store_alert(self, alert: Alert):
        """Store alert in database"""
        if not self.mongodb:
            return
        
        try:
            alert_doc = {
                'alert_type': alert.alert_type.value,
                'level': alert.level.value,
                'title': alert.title,
                'message': alert.message,
                'source': alert.source,
                'timestamp': alert.timestamp,
                'metadata': alert.metadata or {},
                'resolved': alert.resolved,
                'resolved_at': alert.resolved_at
            }
            
            await self.mongodb.alerts.insert_one(alert_doc)
        except Exception as e:
            logger.error(f"Error storing alert: {e}")

    async def _send_email_alert(self, alert: Alert):
        """Send email notification for critical alerts"""
        if not self.settings.smtp_host or not self.settings.smtp_username:
            logger.warning("Email settings not configured, skipping email alert")
            return
        
        try:
            msg = MimeMultipart()
            msg['From'] = self.settings.smtp_username
            msg['To'] = self.settings.alert_email or self.settings.smtp_username
            msg['Subject'] = f"[DXB Events Alert] {alert.title}"
            
            # Create email body
            body = f"""
Alert Details:
Type: {alert.alert_type.value}
Level: {alert.level.value}
Source: {alert.source}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Message:
{alert.message}

Metadata:
{json.dumps(alert.metadata or {}, indent=2)}

This is an automated alert from the DXB Events Data Collection System.
"""
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port)
            server.starttls()
            server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email alert sent for: {alert.title}")
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")

    async def run_all_checks(self) -> List[Alert]:
        """Run all alert checks and handle alerts"""
        all_alerts = []
        
        check_functions = [
            self.check_scraping_failures,
            self.check_processing_backlog,
            self.check_sync_failures,
            self.check_quality_degradation,
            self.check_system_resources,
            self.check_api_cost_spike
        ]
        
        for check_func in check_functions:
            try:
                alerts = await check_func()
                all_alerts.extend(alerts)
            except Exception as e:
                logger.error(f"Error in alert check {check_func.__name__}: {e}")
        
        # Handle all alerts
        for alert in all_alerts:
            await self._handle_alert(alert)
        
        return all_alerts

    async def _handle_alert(self, alert: Alert):
        """Handle an alert by running appropriate handlers"""
        handlers = self.alert_handlers.get(alert.level, [])
        
        for handler in handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler.__name__}: {e}")

    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved"""
        if not self.mongodb:
            return False
        
        try:
            result = await self.mongodb.alerts.update_one(
                {'_id': alert_id},
                {
                    '$set': {
                        'resolved': True,
                        'resolved_at': datetime.now()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return False

    async def get_active_alerts(self, hours: int = 24) -> List[Dict]:
        """Get active (unresolved) alerts from the last N hours"""
        if not self.mongodb:
            return []
        
        since = datetime.now() - timedelta(hours=hours)
        
        try:
            cursor = self.mongodb.alerts.find({
                'timestamp': {'$gte': since},
                'resolved': False
            }).sort('timestamp', -1)
            
            alerts = await cursor.to_list(length=None)
            return alerts
        except Exception as e:
            logger.error(f"Error fetching active alerts: {e}")
            return []


# Utility function for manual alert creation
async def create_manual_alert(alert_type: AlertType, level: AlertLevel, title: str, message: str, source: str = "manual"):
    """Create a manual alert"""
    async with AlertSystem() as alert_system:
        alert = Alert(
            alert_type=alert_type,
            level=level,
            title=title,
            message=message,
            source=source,
            timestamp=datetime.now()
        )
        await alert_system._handle_alert(alert)
        return alert