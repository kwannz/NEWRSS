from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from datetime import datetime
import asyncio
from app.core.logging import get_service_logger
from app.services.broadcast_service import BroadcastService

router = APIRouter(prefix="/api/broadcast", tags=["broadcast"])
logger = get_service_logger("broadcast_api")

@router.get("/status")
async def get_broadcast_status():
    """Get current broadcast system status and statistics"""
    try:
        broadcast_service = BroadcastService()
        stats = await broadcast_service.get_broadcast_statistics()
        
        return JSONResponse(content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "statistics": stats
        })
        
    except Exception as e:
        logger.error(
            "Error getting broadcast status",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve broadcast status"
        )

@router.post("/test/websocket")
async def test_websocket_broadcast():
    """Test WebSocket broadcast functionality"""
    try:
        # Import the broadcast functions from main
        from app.main import broadcast_news, broadcast_urgent
        
        # Test message
        test_message = {
            "id": 999999,
            "title": "🧪 WebSocket Test Message",
            "content": "This is a test message to verify WebSocket broadcasting functionality.",
            "url": "https://example.com/test",
            "source": "System Test",
            "category": "test",
            "published_at": datetime.now().isoformat(),
            "importance_score": 3,
            "is_urgent": False,
            "market_impact": 2,
            "sentiment_score": 0.0,
            "created_at": datetime.now().isoformat()
        }
        
        # Send test broadcast
        await broadcast_news(test_message)
        
        logger.info("WebSocket test broadcast sent successfully")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Test WebSocket broadcast sent successfully",
            "timestamp": datetime.now().isoformat(),
            "test_payload": test_message
        })
        
    except Exception as e:
        logger.error(
            "Error in WebSocket test broadcast",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"WebSocket test failed: {str(e)}"
        )

@router.post("/test/urgent")
async def test_urgent_broadcast():
    """Test urgent news broadcast via WebSocket"""
    try:
        from app.main import broadcast_urgent
        
        test_urgent_message = {
            "id": 999998,
            "title": "🚨 URGENT: WebSocket Test Alert",
            "content": "This is an urgent test message to verify emergency broadcasting functionality.",
            "url": "https://example.com/urgent-test",
            "source": "System Test",
            "category": "test",
            "published_at": datetime.now().isoformat(),
            "importance_score": 5,
            "is_urgent": True,
            "market_impact": 5,
            "sentiment_score": -0.8,
            "created_at": datetime.now().isoformat()
        }
        
        await broadcast_urgent(test_urgent_message)
        
        logger.info("Urgent WebSocket test broadcast sent successfully")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Test urgent broadcast sent successfully",
            "timestamp": datetime.now().isoformat(),
            "test_payload": test_urgent_message
        })
        
    except Exception as e:
        logger.error(
            "Error in urgent broadcast test",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Urgent broadcast test failed: {str(e)}"
        )

@router.post("/test/telegram")
async def test_telegram_broadcast():
    """Test Telegram notification functionality"""
    try:
        broadcast_service = BroadcastService()
        
        test_telegram_message = {
            "title": "📱 Telegram Test Notification",
            "content": "This is a test message to verify Telegram notification functionality. Testing user filtering and message delivery.",
            "url": "https://example.com/telegram-test",
            "source": "System Test",
            "category": "test",
            "published_at": datetime.now().isoformat(),
            "importance_score": 4,
            "is_urgent": False,
            "market_impact": 3,
            "sentiment_score": 0.2
        }
        
        # Test regular Telegram notification
        await broadcast_service.telegram_notifier.send_regular_news_notification(test_telegram_message)
        
        logger.info("Telegram test notification sent successfully")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Test Telegram notification sent successfully",
            "timestamp": datetime.now().isoformat(),
            "test_payload": test_telegram_message
        })
        
    except Exception as e:
        logger.error(
            "Error in Telegram test",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Telegram test failed: {str(e)}"
        )

@router.post("/test/urgent-telegram")
async def test_urgent_telegram():
    """Test urgent Telegram notifications"""
    try:
        broadcast_service = BroadcastService()
        
        test_urgent_telegram = {
            "title": "🚨 URGENT: Telegram Test Alert",
            "content": "This is an urgent test notification to verify emergency Telegram broadcasting. All subscribed users should receive this immediately.",
            "url": "https://example.com/urgent-telegram-test",
            "source": "System Test",
            "category": "test",
            "published_at": datetime.now().isoformat(),
            "importance_score": 5,
            "is_urgent": True,
            "market_impact": 5,
            "sentiment_score": -0.9
        }
        
        await broadcast_service.telegram_notifier.notify_urgent_news(test_urgent_telegram)
        
        logger.info("Urgent Telegram test sent successfully")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Test urgent Telegram notification sent successfully",
            "timestamp": datetime.now().isoformat(),
            "test_payload": test_urgent_telegram
        })
        
    except Exception as e:
        logger.error(
            "Error in urgent Telegram test",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Urgent Telegram test failed: {str(e)}"
        )

@router.post("/test/complete-pipeline")
async def test_complete_pipeline():
    """Test complete news processing and broadcasting pipeline"""
    try:
        broadcast_service = BroadcastService()
        
        # Simulate a complete news item
        test_news_items = [
            {
                "title": "🔧 Complete Pipeline Test: Market Analysis",
                "content": "This comprehensive test simulates a complete news processing pipeline including AI analysis, database storage, WebSocket broadcasting, and Telegram notifications. The system will process this item through all stages to verify end-to-end functionality. Keywords: bitcoin, regulation, partnership.",
                "url": f"https://example.com/pipeline-test-{int(datetime.now().timestamp())}",
                "source": "Pipeline Test",
                "category": "test",
                "published_at": datetime.now().isoformat(),
                "importance_score": 4,
                "is_urgent": False,
                "content_hash": f"test-hash-{int(datetime.now().timestamp())}"
            },
            {
                "title": "🚨 URGENT Pipeline Test: Security Alert",
                "content": "This is an urgent pipeline test simulating a critical security alert. Keywords: hack, exploit, urgent, SEC. This should trigger immediate notifications to all subscribed users and appear in urgent WebSocket channels.",
                "url": f"https://example.com/urgent-pipeline-test-{int(datetime.now().timestamp())}",
                "source": "Pipeline Test",
                "category": "test",
                "published_at": datetime.now().isoformat(),
                "importance_score": 5,
                "is_urgent": True,
                "content_hash": f"urgent-test-hash-{int(datetime.now().timestamp())}"
            }
        ]
        
        # Process through complete pipeline
        logger.info("Starting complete pipeline test")
        pipeline_stats = await broadcast_service.process_and_broadcast_news(test_news_items)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Complete pipeline test executed successfully",
            "timestamp": datetime.now().isoformat(),
            "pipeline_statistics": pipeline_stats,
            "test_items_count": len(test_news_items)
        })
        
    except Exception as e:
        logger.error(
            "Error in complete pipeline test",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Complete pipeline test failed: {str(e)}"
        )

@router.get("/user/{telegram_id}/stats")
async def get_user_delivery_stats(telegram_id: str):
    """Get delivery statistics for a specific user"""
    try:
        from app.services.user_filter_service import UserFilterService
        
        user_filter = UserFilterService()
        stats = await user_filter.get_user_delivery_stats(telegram_id)
        
        return JSONResponse(content={
            "status": "success",
            "telegram_id": telegram_id,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(
            "Error getting user delivery stats",
            telegram_id=telegram_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user stats: {str(e)}"
        )

@router.post("/admin/reset-daily-limits")
async def reset_daily_limits():
    """Reset daily notification limits (admin endpoint)"""
    try:
        from app.services.user_filter_service import UserFilterService
        
        user_filter = UserFilterService()
        reset_count = await user_filter.reset_daily_limits()
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Reset {reset_count} daily notification counters",
            "reset_count": reset_count,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(
            "Error resetting daily limits",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset daily limits: {str(e)}"
        )

@router.get("/health")
async def broadcast_health_check():
    """Health check endpoint for broadcast system"""
    try:
        # Check WebSocket configuration
        websocket_configured = False
        try:
            from app.main import broadcast_service
            websocket_configured = broadcast_service.websocket_broadcast_func is not None
        except:
            pass
        
        # Check Telegram bot configuration  
        telegram_configured = False
        try:
            from app.core.settings import settings
            telegram_configured = bool(settings.TELEGRAM_BOT_TOKEN)
        except:
            pass
        
        # Check database connectivity
        database_healthy = False
        try:
            from app.core.database import SessionLocal
            async with SessionLocal() as db:
                await db.execute("SELECT 1")
                database_healthy = True
        except:
            pass
        
        health_status = {
            "websocket_configured": websocket_configured,
            "telegram_configured": telegram_configured,
            "database_healthy": database_healthy,
            "overall_health": all([websocket_configured, telegram_configured, database_healthy]),
            "timestamp": datetime.now().isoformat()
        }
        
        status_code = 200 if health_status["overall_health"] else 503
        
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
        
    except Exception as e:
        logger.error(
            "Health check failed",
            error=str(e),
            exc_info=True
        )
        return JSONResponse(
            status_code=503,
            content={
                "overall_health": False,
                "error": "Health check failed",
                "timestamp": datetime.now().isoformat()
            }
        )