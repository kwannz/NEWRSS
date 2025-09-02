"""
Production monitoring middleware for NEWRSS backend.
Provides request tracking, performance metrics, and health monitoring.
"""

import time
import uuid
from typing import Callable, Optional
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import structlog

from app.core.redis_client import get_redis_client
from app.core.database import get_db


logger = structlog.get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive monitoring middleware for production deployment.
    
    Features:
    - Request/response logging
    - Performance metrics collection
    - Error rate tracking
    - Health monitoring
    - Business metrics
    """
    
    def __init__(self, app, enable_detailed_logging: bool = True):
        super().__init__(app)
        self.enable_detailed_logging = enable_detailed_logging
        self.excluded_paths = {"/health", "/metrics", "/favicon.ico"}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware processing."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Skip monitoring for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Log incoming request
        await self._log_request(request, request_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            
            # Log successful response
            await self._log_response(request, response, duration, request_id)
            
            # Record metrics
            await self._record_metrics(request, response, duration)
            
            # Add monitoring headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Calculate duration for error cases
            duration = time.time() - start_time
            
            # Log error
            await self._log_error(request, e, duration, request_id)
            
            # Record error metrics
            await self._record_error_metrics(request, e, duration)
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={"X-Request-ID": request_id}
            )
    
    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request details."""
        if not self.enable_detailed_logging:
            return
            
        logger.info(
            "incoming_request",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent"),
            client_ip=request.client.host,
            content_length=request.headers.get("content-length"),
            timestamp=datetime.utcnow().isoformat()
        )
    
    async def _log_response(self, request: Request, response: Response, duration: float, request_id: str):
        """Log successful response details."""
        if not self.enable_detailed_logging and response.status_code < 400:
            return
            
        log_level = "info" if response.status_code < 400 else "warning"
        
        getattr(logger, log_level)(
            "request_completed",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            duration_seconds=round(duration, 3),
            response_size=response.headers.get("content-length"),
            timestamp=datetime.utcnow().isoformat()
        )
    
    async def _log_error(self, request: Request, error: Exception, duration: float, request_id: str):
        """Log request errors."""
        logger.error(
            "request_error",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            error_type=type(error).__name__,
            error_message=str(error),
            duration_seconds=round(duration, 3),
            timestamp=datetime.utcnow().isoformat(),
            exc_info=True
        )
    
    async def _record_metrics(self, request: Request, response: Response, duration: float):
        """Record performance and business metrics."""
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            # Current timestamp for metrics
            timestamp = int(time.time())
            
            # Request metrics
            await redis.incr(f"metrics:requests:total:{timestamp // 60}")  # Per minute
            await redis.incr(f"metrics:requests:method:{request.method}:{timestamp // 60}")
            await redis.incr(f"metrics:requests:status:{response.status_code}:{timestamp // 60}")
            
            # Performance metrics
            await redis.lpush(f"metrics:response_times:{timestamp // 60}", duration)
            await redis.ltrim(f"metrics:response_times:{timestamp // 60}", 0, 999)  # Keep last 1000
            
            # Endpoint-specific metrics
            endpoint = self._normalize_endpoint(request.url.path)
            await redis.incr(f"metrics:endpoints:{endpoint}:{timestamp // 60}")
            await redis.lpush(f"metrics:endpoint_times:{endpoint}:{timestamp // 60}", duration)
            await redis.ltrim(f"metrics:endpoint_times:{endpoint}:{timestamp // 60}", 0, 99)
            
            # Business metrics
            await self._record_business_metrics(request, response, redis, timestamp)
            
            # Set expiry for metrics (7 days)
            expire_time = 604800
            for key_pattern in [
                f"metrics:requests:total:{timestamp // 60}",
                f"metrics:requests:method:{request.method}:{timestamp // 60}",
                f"metrics:requests:status:{response.status_code}:{timestamp // 60}",
                f"metrics:response_times:{timestamp // 60}",
                f"metrics:endpoints:{endpoint}:{timestamp // 60}",
                f"metrics:endpoint_times:{endpoint}:{timestamp // 60}"
            ]:
                await redis.expire(key_pattern, expire_time)
            
        except Exception as e:
            logger.warning("Failed to record metrics", error=str(e))
    
    async def _record_business_metrics(self, request: Request, response: Response, redis, timestamp: int):
        """Record business-specific metrics."""
        endpoint = request.url.path
        
        # News-related metrics
        if "/api/news" in endpoint and response.status_code == 200:
            await redis.incr(f"metrics:business:news_requests:{timestamp // 60}")
        
        # WebSocket connection metrics
        if "/socket.io" in endpoint:
            await redis.incr(f"metrics:business:websocket_connections:{timestamp // 60}")
        
        # Telegram webhook metrics
        if "/telegram" in endpoint:
            await redis.incr(f"metrics:business:telegram_webhooks:{timestamp // 60}")
        
        # API endpoint usage
        if endpoint.startswith("/api/"):
            api_endpoint = endpoint.replace("/api/", "").split("/")[0]
            await redis.incr(f"metrics:business:api_usage:{api_endpoint}:{timestamp // 60}")
    
    async def _record_error_metrics(self, request: Request, error: Exception, duration: float):
        """Record error-specific metrics."""
        try:
            redis = await get_redis_client()
            if not redis:
                return
            
            timestamp = int(time.time())
            error_type = type(error).__name__
            
            # Error count metrics
            await redis.incr(f"metrics:errors:total:{timestamp // 60}")
            await redis.incr(f"metrics:errors:type:{error_type}:{timestamp // 60}")
            await redis.incr(f"metrics:errors:endpoint:{self._normalize_endpoint(request.url.path)}:{timestamp // 60}")
            
            # Error rate tracking
            await redis.lpush(f"metrics:error_rates:{timestamp // 60}", 1)
            await redis.ltrim(f"metrics:error_rates:{timestamp // 60}", 0, 999)
            
            # Set expiry
            expire_time = 604800
            for key_pattern in [
                f"metrics:errors:total:{timestamp // 60}",
                f"metrics:errors:type:{error_type}:{timestamp // 60}",
                f"metrics:errors:endpoint:{self._normalize_endpoint(request.url.path)}:{timestamp // 60}",
                f"metrics:error_rates:{timestamp // 60}"
            ]:
                await redis.expire(key_pattern, expire_time)
                
        except Exception as e:
            logger.warning("Failed to record error metrics", error=str(e))
    
    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics grouping."""
        # Replace dynamic segments with placeholders
        parts = path.strip('/').split('/')
        normalized_parts = []
        
        for part in parts:
            # Replace UUIDs and numeric IDs with placeholders
            if part.isdigit():
                normalized_parts.append('{id}')
            elif len(part) == 36 and part.count('-') == 4:  # UUID format
                normalized_parts.append('{uuid}')
            else:
                normalized_parts.append(part)
        
        return '/'.join(normalized_parts) or 'root'


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Health check middleware for load balancer and monitoring systems.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.health_checks = {
            "database": self._check_database,
            "redis": self._check_redis,
            "disk_space": self._check_disk_space,
            "memory": self._check_memory
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process health check requests."""
        if request.url.path == "/health":
            return await self._handle_health_check(request)
        elif request.url.path == "/health/detailed":
            return await self._handle_detailed_health_check(request)
        else:
            return await call_next(request)
    
    async def _handle_health_check(self, request: Request) -> JSONResponse:
        """Handle simple health check."""
        try:
            # Quick database check
            db_healthy = await self._check_database()
            redis_healthy = await self._check_redis()
            
            if db_healthy and redis_healthy:
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "healthy",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response_time": time.time()
                    }
                )
            else:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "unhealthy",
                        "timestamp": datetime.utcnow().isoformat(),
                        "database": db_healthy,
                        "redis": redis_healthy
                    }
                )
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    async def _handle_detailed_health_check(self, request: Request) -> JSONResponse:
        """Handle detailed health check with all components."""
        health_results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        overall_healthy = True
        
        for check_name, check_func in self.health_checks.items():
            try:
                result = await check_func()
                health_results["checks"][check_name] = {
                    "status": "healthy" if result else "unhealthy",
                    "healthy": result
                }
                if not result:
                    overall_healthy = False
            except Exception as e:
                health_results["checks"][check_name] = {
                    "status": "error",
                    "error": str(e)
                }
                overall_healthy = False
        
        health_results["status"] = "healthy" if overall_healthy else "unhealthy"
        
        return JSONResponse(
            status_code=200 if overall_healthy else 503,
            content=health_results
        )
    
    async def _check_database(self) -> bool:
        """Check database connectivity."""
        try:
            async with get_db() as db:
                await db.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    async def _check_redis(self) -> bool:
        """Check Redis connectivity."""
        try:
            redis = await get_redis_client()
            if redis:
                await redis.ping()
                return True
            return False
        except Exception:
            return False
    
    async def _check_disk_space(self) -> bool:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percentage = (free / total) * 100
            return free_percentage > 10  # Alert if less than 10% free
        except Exception:
            return False
    
    async def _check_memory(self) -> bool:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.percent < 90  # Alert if more than 90% used
        except ImportError:
            # psutil not available, skip check
            return True
        except Exception:
            return False