#!/usr/bin/env python3
"""
Health check script for NEWRSS backend service.
Used by Docker health checks and monitoring systems.
"""

import asyncio
import sys
from typing import Dict, Any

import aiohttp
import asyncpg
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine

# Health check configuration
HEALTH_CHECK_TIMEOUT = 10
API_BASE_URL = "http://localhost:8000"


async def check_api_health() -> Dict[str, Any]:
    """Check if the API is responding."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {"status": "healthy", "response_time": data.get("response_time")}
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        # Get database URL from environment
        import os
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://newrss:newrss@postgres:5432/newrss")
        
        # Convert to asyncpg format
        asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Test connection
        conn = await asyncpg.connect(asyncpg_url, command_timeout=5)
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            return {"status": "healthy"}
        else:
            return {"status": "unhealthy", "error": "Unexpected query result"}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import os
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        
        redis_client = redis.from_url(redis_url, socket_timeout=5)
        await redis_client.ping()
        await redis_client.close()
        
        return {"status": "healthy"}
        
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    try:
        import shutil
        
        # Check available disk space
        total, used, free = shutil.disk_usage("/app")
        free_percentage = (free / total) * 100
        
        if free_percentage < 10:
            return {
                "status": "warning", 
                "free_percentage": free_percentage,
                "message": "Low disk space"
            }
        elif free_percentage < 5:
            return {
                "status": "unhealthy", 
                "free_percentage": free_percentage,
                "error": "Critical disk space"
            }
        else:
            return {"status": "healthy", "free_percentage": free_percentage}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def run_health_checks() -> Dict[str, Any]:
    """Run all health checks."""
    health_status = {
        "timestamp": asyncio.get_event_loop().time(),
        "overall_status": "healthy",
        "checks": {}
    }
    
    # Run health checks concurrently
    checks = await asyncio.gather(
        check_api_health(),
        check_database_health(),
        check_redis_health(),
        check_disk_space(),
        return_exceptions=True
    )
    
    check_names = ["api", "database", "redis", "disk"]
    
    for name, result in zip(check_names, checks):
        if isinstance(result, Exception):
            health_status["checks"][name] = {
                "status": "unhealthy",
                "error": str(result)
            }
        else:
            health_status["checks"][name] = result
    
    # Determine overall status
    unhealthy_checks = [
        name for name, check in health_status["checks"].items()
        if check.get("status") == "unhealthy"
    ]
    
    warning_checks = [
        name for name, check in health_status["checks"].items()
        if check.get("status") == "warning"
    ]
    
    if unhealthy_checks:
        health_status["overall_status"] = "unhealthy"
        health_status["unhealthy_checks"] = unhealthy_checks
    elif warning_checks:
        health_status["overall_status"] = "warning"
        health_status["warning_checks"] = warning_checks
    
    return health_status


async def main():
    """Main health check function."""
    try:
        # Set timeout for entire health check
        health_result = await asyncio.wait_for(
            run_health_checks(),
            timeout=HEALTH_CHECK_TIMEOUT
        )
        
        # Print results for monitoring
        print(f"Health Check Result: {health_result['overall_status']}")
        
        if health_result["overall_status"] == "unhealthy":
            print("Unhealthy checks:", health_result.get("unhealthy_checks", []))
            for name, check in health_result["checks"].items():
                if check.get("status") == "unhealthy":
                    print(f"  {name}: {check.get('error', 'Unknown error')}")
            sys.exit(1)
        elif health_result["overall_status"] == "warning":
            print("Warning checks:", health_result.get("warning_checks", []))
            for name, check in health_result["checks"].items():
                if check.get("status") == "warning":
                    print(f"  {name}: {check.get('message', 'Warning')}")
            # Exit with 0 for warnings (still considered healthy)
        
        print("All health checks passed")
        sys.exit(0)
        
    except asyncio.TimeoutError:
        print("Health check timed out")
        sys.exit(1)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())