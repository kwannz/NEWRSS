"""
Automated maintenance tasks for NEWRSS production environment.
Handles database cleanup, log rotation, performance optimization, and health monitoring.
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

from celery import Celery
from sqlalchemy import text
import structlog

from app.core.database import get_db
from app.core.redis_client import get_redis_client
from app.models.news import NewsItem
from app.tasks.news_crawler import celery_app


logger = structlog.get_logger(__name__)


@celery_app.task(bind=True)
def cleanup_old_news_items(self, days_to_keep: int = 30):
    """
    Clean up old news items from the database.
    Keeps only items from the last N days.
    """
    try:
        asyncio.run(_cleanup_old_news_items_async(days_to_keep))
        logger.info("News cleanup completed", days_to_keep=days_to_keep)
        return {"status": "success", "days_to_keep": days_to_keep}
    except Exception as e:
        logger.error("News cleanup failed", error=str(e))
        raise self.retry(exc=e, countdown=300, max_retries=3)


async def _cleanup_old_news_items_async(days_to_keep: int):
    """Async implementation of news cleanup."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    async with get_db() as db:
        # Count items to be deleted
        count_result = await db.execute(
            text("SELECT COUNT(*) FROM news_items WHERE created_at < :cutoff_date"),
            {"cutoff_date": cutoff_date}
        )
        items_to_delete = count_result.scalar()
        
        # Delete old items in batches
        batch_size = 1000
        total_deleted = 0
        
        while True:
            result = await db.execute(
                text("""
                    DELETE FROM news_items 
                    WHERE id IN (
                        SELECT id FROM news_items 
                        WHERE created_at < :cutoff_date 
                        LIMIT :batch_size
                    )
                """),
                {"cutoff_date": cutoff_date, "batch_size": batch_size}
            )
            
            deleted_count = result.rowcount
            total_deleted += deleted_count
            
            if deleted_count == 0:
                break
            
            await db.commit()
            
            # Small delay to avoid overwhelming the database
            await asyncio.sleep(0.1)
        
        logger.info(
            "Database cleanup completed",
            items_to_delete=items_to_delete,
            total_deleted=total_deleted,
            cutoff_date=cutoff_date.isoformat()
        )


@celery_app.task(bind=True)
def cleanup_redis_cache(self, max_memory_mb: int = 256):
    """
    Clean up Redis cache when memory usage exceeds threshold.
    """
    try:
        asyncio.run(_cleanup_redis_cache_async(max_memory_mb))
        logger.info("Redis cleanup completed", max_memory_mb=max_memory_mb)
        return {"status": "success", "max_memory_mb": max_memory_mb}
    except Exception as e:
        logger.error("Redis cleanup failed", error=str(e))
        raise self.retry(exc=e, countdown=300, max_retries=3)


async def _cleanup_redis_cache_async(max_memory_mb: int):
    """Async implementation of Redis cleanup."""
    redis = await get_redis_client()
    if not redis:
        return
    
    # Get Redis memory info
    info = await redis.info('memory')
    used_memory_mb = info.get('used_memory', 0) / (1024 * 1024)
    
    if used_memory_mb > max_memory_mb:
        logger.warning(
            "Redis memory usage high, cleaning up",
            used_memory_mb=used_memory_mb,
            max_memory_mb=max_memory_mb
        )
        
        # Clean up old metrics (older than 24 hours)
        current_time = int(datetime.utcnow().timestamp())
        cutoff_time = current_time - 86400  # 24 hours ago
        
        # Get all metric keys
        metric_patterns = [
            "metrics:requests:*",
            "metrics:response_times:*",
            "metrics:endpoints:*",
            "metrics:errors:*",
            "metrics:business:*"
        ]
        
        keys_deleted = 0
        for pattern in metric_patterns:
            keys = await redis.keys(pattern)
            for key in keys:
                # Extract timestamp from key
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    timestamp_str = key_str.split(':')[-1]
                    key_timestamp = int(timestamp_str) * 60  # Convert minutes to seconds
                    
                    if key_timestamp < cutoff_time:
                        await redis.delete(key)
                        keys_deleted += 1
                except (ValueError, IndexError):
                    # Skip keys that don't match expected format
                    continue
        
        # Force garbage collection
        await redis.execute_command('MEMORY', 'PURGE')
        
        # Get updated memory info
        new_info = await redis.info('memory')
        new_used_memory_mb = new_info.get('used_memory', 0) / (1024 * 1024)
        
        logger.info(
            "Redis cleanup completed",
            keys_deleted=keys_deleted,
            memory_before_mb=used_memory_mb,
            memory_after_mb=new_used_memory_mb,
            memory_freed_mb=used_memory_mb - new_used_memory_mb
        )


@celery_app.task(bind=True)
def rotate_application_logs(self, max_log_size_mb: int = 100, max_log_files: int = 10):
    """
    Rotate application logs when they exceed size threshold.
    """
    try:
        rotated_files = _rotate_logs(max_log_size_mb, max_log_files)
        logger.info("Log rotation completed", rotated_files=rotated_files)
        return {"status": "success", "rotated_files": rotated_files}
    except Exception as e:
        logger.error("Log rotation failed", error=str(e))
        raise self.retry(exc=e, countdown=300, max_retries=3)


def _rotate_logs(max_log_size_mb: int, max_log_files: int) -> List[str]:
    """Rotate log files that exceed size threshold."""
    rotated_files = []
    log_directory = "/var/log/newrss"
    
    if not os.path.exists(log_directory):
        return rotated_files
    
    for filename in os.listdir(log_directory):
        if not filename.endswith('.log'):
            continue
            
        log_path = os.path.join(log_directory, filename)
        
        try:
            # Check file size
            file_size_mb = os.path.getsize(log_path) / (1024 * 1024)
            
            if file_size_mb > max_log_size_mb:
                # Rotate the log file
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                rotated_filename = f"{filename}.{timestamp}"
                rotated_path = os.path.join(log_directory, rotated_filename)
                
                os.rename(log_path, rotated_path)
                rotated_files.append(rotated_filename)
                
                # Clean up old rotated files
                _cleanup_old_log_files(log_directory, filename, max_log_files)
                
        except OSError as e:
            logger.warning("Failed to rotate log file", file=log_path, error=str(e))
    
    return rotated_files


def _cleanup_old_log_files(log_directory: str, base_filename: str, max_files: int):
    """Clean up old rotated log files, keeping only the most recent ones."""
    pattern = f"{base_filename}."
    log_files = []
    
    for filename in os.listdir(log_directory):
        if filename.startswith(pattern) and filename != base_filename:
            file_path = os.path.join(log_directory, filename)
            mtime = os.path.getmtime(file_path)
            log_files.append((filename, mtime, file_path))
    
    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x[1], reverse=True)
    
    # Remove files beyond the limit
    for filename, mtime, file_path in log_files[max_files:]:
        try:
            os.remove(file_path)
            logger.info("Removed old log file", file=filename)
        except OSError as e:
            logger.warning("Failed to remove old log file", file=filename, error=str(e))


@celery_app.task(bind=True)
def collect_performance_metrics(self):
    """
    Collect and aggregate performance metrics for monitoring dashboards.
    """
    try:
        metrics = asyncio.run(_collect_performance_metrics_async())
        logger.info("Performance metrics collected", metrics_count=len(metrics))
        return {"status": "success", "metrics": metrics}
    except Exception as e:
        logger.error("Performance metrics collection failed", error=str(e))
        raise self.retry(exc=e, countdown=300, max_retries=3)


async def _collect_performance_metrics_async() -> Dict[str, Any]:
    """Async implementation of performance metrics collection."""
    metrics = {}
    redis = await get_redis_client()
    
    if not redis:
        return metrics
    
    current_minute = int(datetime.utcnow().timestamp()) // 60
    
    # Collect request metrics for the last hour
    request_counts = []
    response_times = []
    
    for i in range(60):  # Last 60 minutes
        minute = current_minute - i
        
        # Request count
        count_key = f"metrics:requests:total:{minute}"
        count = await redis.get(count_key)
        request_counts.append(int(count) if count else 0)
        
        # Average response time
        times_key = f"metrics:response_times:{minute}"
        times = await redis.lrange(times_key, 0, -1)
        if times:
            avg_time = sum(float(t) for t in times) / len(times)
            response_times.append(avg_time)
        else:
            response_times.append(0.0)
    
    metrics.update({
        "requests_per_hour": sum(request_counts),
        "avg_requests_per_minute": sum(request_counts) / 60,
        "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
        "max_response_time": max(response_times) if response_times else 0
    })
    
    # Collect error metrics
    error_count_key = f"metrics:errors:total:{current_minute}"
    error_count = await redis.get(error_count_key)
    metrics["errors_current_minute"] = int(error_count) if error_count else 0
    
    # Database metrics
    try:
        async with get_db() as db:
            # Count total news items
            result = await db.execute(text("SELECT COUNT(*) FROM news_items"))
            metrics["total_news_items"] = result.scalar()
            
            # Count news items from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            result = await db.execute(
                text("SELECT COUNT(*) FROM news_items WHERE created_at > :yesterday"),
                {"yesterday": yesterday}
            )
            metrics["news_items_24h"] = result.scalar()
            
    except Exception as e:
        logger.warning("Failed to collect database metrics", error=str(e))
    
    # System metrics
    try:
        import psutil
        
        metrics.update({
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        })
    except ImportError:
        logger.warning("psutil not available for system metrics")
    except Exception as e:
        logger.warning("Failed to collect system metrics", error=str(e))
    
    return metrics


@celery_app.task(bind=True)
def health_check_alert(self):
    """
    Perform comprehensive health checks and send alerts if issues detected.
    """
    try:
        health_status = asyncio.run(_perform_health_checks_async())
        
        # Check if any health checks failed
        failed_checks = [
            check for check, status in health_status.items()
            if not status.get("healthy", False)
        ]
        
        if failed_checks:
            logger.error(
                "Health check failures detected",
                failed_checks=failed_checks,
                health_status=health_status
            )
            # In production, send alerts here (email, Slack, PagerDuty, etc.)
            _send_health_alert(failed_checks, health_status)
        else:
            logger.info("All health checks passed", health_status=health_status)
        
        return {"status": "success", "health_status": health_status, "failed_checks": failed_checks}
        
    except Exception as e:
        logger.error("Health check task failed", error=str(e))
        raise self.retry(exc=e, countdown=300, max_retries=3)


async def _perform_health_checks_async() -> Dict[str, Dict[str, Any]]:
    """Perform comprehensive system health checks."""
    health_status = {}
    
    # Database health check
    try:
        async with get_db() as db:
            await db.execute(text("SELECT 1"))
            health_status["database"] = {"healthy": True, "response_time": 0.1}
    except Exception as e:
        health_status["database"] = {"healthy": False, "error": str(e)}
    
    # Redis health check
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            health_status["redis"] = {"healthy": True}
        else:
            health_status["redis"] = {"healthy": False, "error": "Redis client not available"}
    except Exception as e:
        health_status["redis"] = {"healthy": False, "error": str(e)}
    
    # Disk space check
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        health_status["disk_space"] = {
            "healthy": free_percent > 10,
            "free_percent": round(free_percent, 2),
            "free_gb": round(free / (1024**3), 2)
        }
    except Exception as e:
        health_status["disk_space"] = {"healthy": False, "error": str(e)}
    
    # Memory check
    try:
        import psutil
        memory = psutil.virtual_memory()
        health_status["memory"] = {
            "healthy": memory.percent < 90,
            "used_percent": round(memory.percent, 2),
            "available_gb": round(memory.available / (1024**3), 2)
        }
    except ImportError:
        health_status["memory"] = {"healthy": True, "note": "psutil not available"}
    except Exception as e:
        health_status["memory"] = {"healthy": False, "error": str(e)}
    
    return health_status


def _send_health_alert(failed_checks: List[str], health_status: Dict[str, Any]):
    """Send health check failure alerts."""
    # In a real implementation, integrate with your alerting system
    # Examples: Slack webhook, email, PagerDuty, etc.
    
    alert_message = f"NEWRSS Health Check Failures: {', '.join(failed_checks)}"
    
    logger.critical(
        "Health check alert triggered",
        failed_checks=failed_checks,
        health_status=health_status,
        alert_message=alert_message
    )
    
    # TODO: Implement actual alerting integration
    # slack_webhook(alert_message)
    # send_email_alert(alert_message)
    # pagerduty_alert(alert_message)


# Schedule maintenance tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic maintenance tasks."""
    
    # Daily cleanup at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_old_news_items.s(days_to_keep=30),
        name='daily-news-cleanup'
    )
    
    # Redis cleanup every 6 hours
    sender.add_periodic_task(
        crontab(minute=0, hour='*/6'),
        cleanup_redis_cache.s(max_memory_mb=256),
        name='redis-cleanup'
    )
    
    # Log rotation every 4 hours
    sender.add_periodic_task(
        crontab(minute=30, hour='*/4'),
        rotate_application_logs.s(max_log_size_mb=100, max_log_files=10),
        name='log-rotation'
    )
    
    # Performance metrics collection every 15 minutes
    sender.add_periodic_task(
        crontab(minute='*/15'),
        collect_performance_metrics.s(),
        name='performance-metrics'
    )
    
    # Health checks every 5 minutes
    sender.add_periodic_task(
        crontab(minute='*/5'),
        health_check_alert.s(),
        name='health-check-alert'
    )


# Import crontab for scheduling
from celery.schedules import crontab