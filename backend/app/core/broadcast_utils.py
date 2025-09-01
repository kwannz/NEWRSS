"""
Broadcast utility functions for WebSocket communication.

Separated from main.py to avoid circular imports.
"""

import socketio
from app.core.logging import websocket_logger
from app.core.settings import settings


# Initialize socket.io server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ORIGINS,
    logger=False,
    engineio_logger=False
)


async def broadcast_news(news_item: dict):
    """Broadcast regular news to connected WebSocket clients."""
    try:
        await sio.emit('news', news_item)
        websocket_logger.info(
            "Regular news broadcasted",
            title=news_item.get('title', 'Unknown'),
            recipients="all_connected"
        )
    except Exception as e:
        websocket_logger.error(
            "Failed to broadcast regular news",
            error=str(e),
            news_title=news_item.get('title', 'Unknown'),
            exc_info=True
        )


async def broadcast_urgent(news_item: dict):
    """Broadcast urgent news to connected WebSocket clients."""
    try:
        await sio.emit('urgent_news', news_item)
        websocket_logger.info(
            "Urgent news broadcasted",
            title=news_item.get('title', 'Unknown'),
            recipients="all_connected",
            importance_score=news_item.get('importance_score', 0)
        )
    except Exception as e:
        websocket_logger.error(
            "Failed to broadcast urgent news",
            error=str(e),
            news_title=news_item.get('title', 'Unknown'),
            exc_info=True
        )


# Get the socket.io server instance for use in main.py
def get_socketio_server():
    """Get the socket.io server instance."""
    return sio