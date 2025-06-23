from celery import Celery
from celery.schedules import crontab
from config import settings
import os

# Create Celery app
celery_app = Celery("dxb_events_lifecycle")

# Configure broker and backend
celery_app.conf.broker_url = settings.redis_url
celery_app.conf.result_backend = settings.redis_url

# Import task modules
celery_app.autodiscover_tasks([
    'lifecycle_management.schedulers',
], force=True)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='Asia/Dubai',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'lifecycle_management.schedulers.cleanup_tasks.*': {'queue': 'cleanup'},
        'lifecycle_management.schedulers.monitoring_tasks.*': {'queue': 'monitoring'},
        'lifecycle_management.schedulers.hidden_gems_tasks.*': {'queue': 'hidden_gems'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task execution
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Beat schedule for automated tasks
    beat_schedule={
        # Daily cleanup at 3 AM UAE time
        'daily-source-based-cleanup': {
            'task': 'lifecycle_management.schedulers.cleanup_tasks.daily_source_based_cleanup',
            'schedule': crontab(hour=3, minute=0),  # 3 AM daily
            'options': {'queue': 'cleanup'}
        },
        
        # Weekly retention report on Monday at 4 AM UAE time
        'weekly-retention-report': {
            'task': 'lifecycle_management.schedulers.monitoring_tasks.weekly_retention_report',
            'schedule': crontab(hour=4, minute=0, day_of_week=1),  # Monday 4 AM
            'options': {'queue': 'monitoring'}
        },
        
        # Daily storage health check at 2 AM UAE time
        'daily-storage-health-check': {
            'task': 'lifecycle_management.schedulers.monitoring_tasks.daily_storage_health_check',
            'schedule': crontab(hour=2, minute=0),  # 2 AM daily
            'options': {'queue': 'monitoring'}
        },
        
        # Setup retention policies for new events (every 4 hours)
        'setup-retention-policies': {
            'task': 'lifecycle_management.schedulers.cleanup_tasks.setup_retention_policies',
            'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
            'options': {'queue': 'cleanup'}
        },
        
        # Emergency cleanup check (every 6 hours)
        'emergency-cleanup-check': {
            'task': 'lifecycle_management.schedulers.cleanup_tasks.emergency_cleanup_check',
            'schedule': crontab(minute=30, hour='*/6'),  # Every 6 hours at :30
            'options': {'queue': 'cleanup'}
        },
        
        # Daily hidden gem creation at 1 AM UAE time
        'create-daily-hidden-gem': {
            'task': 'lifecycle_management.schedulers.hidden_gems_tasks.create_daily_hidden_gem',
            'schedule': crontab(hour=1, minute=0),  # 1 AM daily
            'options': {'queue': 'hidden_gems'}
        },
        
        # Weekly cleanup of expired hidden gems on Sunday at 1:30 AM UAE time
        'cleanup-expired-gems': {
            'task': 'lifecycle_management.schedulers.hidden_gems_tasks.cleanup_expired_gems',
            'schedule': crontab(hour=1, minute=30, day_of_week=0),  # Sunday 1:30 AM
            'options': {'queue': 'hidden_gems'}
        }
    }
)

# Error handling
@celery_app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

if __name__ == '__main__':
    celery_app.start() 