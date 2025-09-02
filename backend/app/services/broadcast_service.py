import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.logging import get_service_logger
from app.services.telegram_notifier import TelegramNotifier
from app.services.ai_analyzer import AINewsAnalyzer
from app.services.user_filter_service import UserFilterService
from app.models.news import NewsItem
from app.core.database import SessionLocal
from app.repositories.user_repository import UserRepository
from sqlalchemy import select
import json

class BroadcastService:
    """
    Real-time news broadcasting service that coordinates WebSocket and Telegram notifications
    """
    
    def __init__(self):
        self.logger = get_service_logger("broadcast_service")
        self.telegram_notifier = TelegramNotifier()
        self.ai_analyzer = AINewsAnalyzer()
        self.user_filter = UserFilterService()
        self.websocket_broadcast_func = None  # Will be set by main app
        
    def set_websocket_broadcaster(self, broadcast_func, urgent_broadcast_func):
        """Set WebSocket broadcast functions from main app"""
        self.websocket_broadcast_func = broadcast_func
        self.urgent_websocket_broadcast_func = urgent_broadcast_func
        self.logger.info("WebSocket broadcast functions configured")
    
    async def process_and_broadcast_news(self, news_items: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Process news items and broadcast via both WebSocket and Telegram
        
        Returns statistics about processing
        """
        stats = {
            'total_processed': 0,
            'urgent_broadcast': 0,
            'regular_broadcast': 0,
            'telegram_notifications': 0,
            'websocket_broadcasts': 0,
            'ai_analyzed': 0,
            'database_saved': 0
        }
        
        if not news_items:
            self.logger.info("No news items to process")
            return stats
            
        try:
            self.logger.info(
                "Starting news processing and broadcasting",
                total_items=len(news_items),
                process_start=datetime.now().isoformat()
            )
            
            # Process each news item
            processed_items = []
            for item in news_items:
                try:
                    # Enhance with AI analysis if available
                    enhanced_item = await self._enhance_with_ai_analysis(item)
                    if enhanced_item.get('ai_enhanced'):
                        stats['ai_analyzed'] += 1
                    
                    # Save to database
                    saved_item = await self._save_to_database(enhanced_item)
                    if saved_item:
                        stats['database_saved'] += 1
                        processed_items.append(saved_item)
                    
                    stats['total_processed'] += 1
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to process individual news item",
                        item_title=item.get('title', 'Unknown'),
                        error=str(e),
                        exc_info=True
                    )
                    continue
            
            # Broadcast processed items
            broadcast_results = await self._broadcast_news_items(processed_items)
            
            # Update stats with broadcast results
            stats.update(broadcast_results)
            
            self.logger.info(
                "News processing and broadcasting completed",
                **stats,
                process_duration_ms=(datetime.now().timestamp() * 1000) - (datetime.now().timestamp() * 1000)
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Critical error in news processing pipeline",
                error=str(e),
                exc_info=True
            )
            return stats
    
    async def _enhance_with_ai_analysis(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance news item with AI analysis"""
        try:
            # Skip AI analysis if no OpenAI key or content too short
            if not news_item.get('content') or len(news_item.get('content', '')) < 50:
                return {**news_item, 'ai_enhanced': False}
            
            analysis = await self.ai_analyzer.analyze_news(news_item)
            
            # Merge AI analysis results
            enhanced_item = {
                **news_item,
                'summary': analysis.get('summary'),
                'sentiment_score': analysis.get('sentiment', 0.0),
                'market_impact': analysis.get('market_impact', news_item.get('importance_score', 1)),
                'key_tokens': json.dumps(analysis.get('key_info', {}).get('tokens', [])),
                'key_prices': json.dumps(analysis.get('key_info', {}).get('prices', [])),
                'ai_enhanced': True
            }
            
            self.logger.debug(
                "AI analysis completed for news item",
                title=news_item.get('title', 'Unknown'),
                sentiment=analysis.get('sentiment', 0.0),
                market_impact=analysis.get('market_impact', 1)
            )
            
            return enhanced_item
            
        except Exception as e:
            self.logger.warning(
                "AI analysis failed, proceeding without enhancement",
                title=news_item.get('title', 'Unknown'),
                error=str(e)
            )
            return {**news_item, 'ai_enhanced': False}
    
    async def _save_to_database(self, news_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Save news item to database"""
        try:
            async with SessionLocal() as db:
                # Check if news item already exists by URL
                stmt = select(NewsItem).where(NewsItem.url == news_item.get('url'))
                result = await db.execute(stmt)
                existing_item = result.scalar_one_or_none()
                
                if existing_item:
                    self.logger.debug(
                        "News item already exists in database, skipping",
                        url=news_item.get('url')
                    )
                    return None
                
                # Create new news item
                db_item = NewsItem(
                    title=news_item.get('title', ''),
                    content=news_item.get('content', ''),
                    summary=news_item.get('summary'),
                    url=news_item.get('url', ''),
                    source=news_item.get('source', ''),
                    category=news_item.get('category', 'general'),
                    published_at=news_item.get('published_at', datetime.now()),
                    importance_score=news_item.get('importance_score', 1),
                    is_urgent=news_item.get('is_urgent', False),
                    market_impact=news_item.get('market_impact', 1),
                    sentiment_score=news_item.get('sentiment_score'),
                    key_tokens=news_item.get('key_tokens'),
                    key_prices=news_item.get('key_prices'),
                    is_processed=True
                )
                
                db.add(db_item)
                await db.commit()
                await db.refresh(db_item)
                
                # Convert to dict for broadcasting
                item_dict = {
                    'id': db_item.id,
                    'title': db_item.title,
                    'content': db_item.content,
                    'summary': db_item.summary,
                    'url': db_item.url,
                    'source': db_item.source,
                    'category': db_item.category,
                    'published_at': db_item.published_at.isoformat(),
                    'importance_score': db_item.importance_score,
                    'is_urgent': db_item.is_urgent,
                    'market_impact': db_item.market_impact,
                    'sentiment_score': db_item.sentiment_score,
                    'key_tokens': json.loads(db_item.key_tokens) if db_item.key_tokens else [],
                    'key_prices': json.loads(db_item.key_prices) if db_item.key_prices else [],
                    'created_at': db_item.created_at.isoformat()
                }
                
                self.logger.debug(
                    "News item saved to database",
                    item_id=db_item.id,
                    title=db_item.title,
                    is_urgent=db_item.is_urgent,
                    importance_score=db_item.importance_score
                )
                
                return item_dict
                
        except Exception as e:
            self.logger.error(
                "Failed to save news item to database",
                title=news_item.get('title', 'Unknown'),
                error=str(e),
                exc_info=True
            )
            return None
    
    async def _broadcast_news_items(self, news_items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Broadcast news items via WebSocket and Telegram"""
        broadcast_stats = {
            'urgent_broadcast': 0,
            'regular_broadcast': 0,
            'telegram_notifications': 0,
            'websocket_broadcasts': 0
        }
        
        if not news_items:
            return broadcast_stats
        
        try:
            # Separate urgent and regular news
            urgent_items = [item for item in news_items if item.get('is_urgent', False)]
            regular_items = [item for item in news_items if not item.get('is_urgent', False)]
            
            # Process urgent news first
            if urgent_items:
                urgent_results = await self._broadcast_urgent_news(urgent_items)
                broadcast_stats['urgent_broadcast'] = len(urgent_items)
                broadcast_stats['telegram_notifications'] += urgent_results.get('telegram_sent', 0)
                broadcast_stats['websocket_broadcasts'] += urgent_results.get('websocket_sent', 0)
            
            # Process regular news (batch important ones)
            if regular_items:
                # Only broadcast regular news with importance >= 3
                important_regular = [item for item in regular_items if item.get('importance_score', 1) >= 3]
                
                if important_regular:
                    regular_results = await self._broadcast_regular_news(important_regular)
                    broadcast_stats['regular_broadcast'] = len(important_regular)
                    broadcast_stats['telegram_notifications'] += regular_results.get('telegram_sent', 0)
                    broadcast_stats['websocket_broadcasts'] += regular_results.get('websocket_sent', 0)
                
                # Send all items via WebSocket for frontend display
                if self.websocket_broadcast_func:
                    for item in regular_items:
                        await self.websocket_broadcast_func(item)
                    broadcast_stats['websocket_broadcasts'] += len(regular_items)
            
            return broadcast_stats
            
        except Exception as e:
            self.logger.error(
                "Error in news broadcasting",
                error=str(e),
                exc_info=True
            )
            return broadcast_stats
    
    async def _broadcast_urgent_news(self, urgent_items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Broadcast urgent news via both WebSocket and Telegram"""
        results = {'telegram_sent': 0, 'websocket_sent': 0}
        
        try:
            # Create concurrent tasks for WebSocket and Telegram broadcasting
            tasks = []
            
            for item in urgent_items:
                # WebSocket broadcast (immediate)
                if self.urgent_websocket_broadcast_func:
                    tasks.append(self._safe_websocket_broadcast_urgent(item))
                
                # Telegram notification (to subscribed users)
                tasks.append(self._safe_telegram_urgent_broadcast(item))
            
            # Execute all broadcasts concurrently
            broadcast_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful broadcasts
            websocket_success = sum(1 for i, result in enumerate(broadcast_results) 
                                  if i % 2 == 0 and not isinstance(result, Exception))
            telegram_success = sum(1 for i, result in enumerate(broadcast_results) 
                                 if i % 2 == 1 and not isinstance(result, Exception))
            
            results['websocket_sent'] = websocket_success
            results['telegram_sent'] = telegram_success
            
            self.logger.info(
                "Urgent news broadcast completed",
                urgent_count=len(urgent_items),
                websocket_sent=websocket_success,
                telegram_sent=telegram_success
            )
            
        except Exception as e:
            self.logger.error(
                "Error broadcasting urgent news",
                urgent_count=len(urgent_items),
                error=str(e),
                exc_info=True
            )
        
        return results
    
    async def _broadcast_regular_news(self, regular_items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Broadcast regular important news"""
        results = {'telegram_sent': 0, 'websocket_sent': 0}
        
        try:
            # For regular news, we batch WebSocket broadcasts and selective Telegram notifications
            telegram_tasks = []
            websocket_tasks = []
            
            for item in regular_items:
                # WebSocket broadcast for all regular items
                if self.websocket_broadcast_func:
                    websocket_tasks.append(self._safe_websocket_broadcast_regular(item))
                
                # Telegram notification only for high importance (score >= 4)
                if item.get('importance_score', 1) >= 4:
                    telegram_tasks.append(self._safe_telegram_regular_broadcast(item))
            
            # Execute broadcasts
            websocket_results = await asyncio.gather(*websocket_tasks, return_exceptions=True) if websocket_tasks else []
            telegram_results = await asyncio.gather(*telegram_tasks, return_exceptions=True) if telegram_tasks else []
            
            # Count successes
            results['websocket_sent'] = sum(1 for result in websocket_results if not isinstance(result, Exception))
            results['telegram_sent'] = sum(1 for result in telegram_results if not isinstance(result, Exception))
            
            self.logger.info(
                "Regular news broadcast completed",
                regular_count=len(regular_items),
                websocket_sent=results['websocket_sent'],
                telegram_sent=results['telegram_sent']
            )
            
        except Exception as e:
            self.logger.error(
                "Error broadcasting regular news",
                regular_count=len(regular_items),
                error=str(e),
                exc_info=True
            )
        
        return results
    
    async def _safe_websocket_broadcast_urgent(self, item: Dict[str, Any]) -> bool:
        """Safely broadcast urgent news via WebSocket"""
        try:
            if self.urgent_websocket_broadcast_func:
                await self.urgent_websocket_broadcast_func(item)
                return True
        except Exception as e:
            self.logger.error(
                "WebSocket urgent broadcast failed",
                item_title=item.get('title', 'Unknown'),
                error=str(e)
            )
        return False
    
    async def _safe_websocket_broadcast_regular(self, item: Dict[str, Any]) -> bool:
        """Safely broadcast regular news via WebSocket"""
        try:
            if self.websocket_broadcast_func:
                await self.websocket_broadcast_func(item)
                return True
        except Exception as e:
            self.logger.error(
                "WebSocket regular broadcast failed",
                item_title=item.get('title', 'Unknown'),
                error=str(e)
            )
        return False
    
    async def _safe_telegram_urgent_broadcast(self, item: Dict[str, Any]) -> bool:
        """Safely broadcast urgent news via Telegram with advanced user filtering"""
        try:
            # Get filtered users for urgent delivery
            filtered_users = await self.user_filter.get_filtered_users_for_news(item, "urgent")
            
            if not filtered_users:
                self.logger.info(
                    "No users qualify for urgent Telegram notification after filtering",
                    item_title=item.get('title', 'Unknown')
                )
                return False
            
            # Send to filtered users and record deliveries
            user_telegram_ids = [user['telegram_id'] for user in filtered_users]
            
            # Use the existing telegram notification but with filtered user list
            await self.telegram_notifier.bot.send_news_alert(user_telegram_ids, item)
            
            # Record delivery for each user
            for user in filtered_users:
                await self.user_filter.record_news_delivery(
                    user['telegram_id'], 
                    item, 
                    "urgent", 
                    True
                )
            
            self.logger.info(
                "Urgent Telegram broadcast completed with filtering",
                item_title=item.get('title', 'Unknown'),
                filtered_users=len(filtered_users)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Telegram urgent broadcast failed",
                item_title=item.get('title', 'Unknown'),
                error=str(e)
            )
        return False
    
    async def _safe_telegram_regular_broadcast(self, item: Dict[str, Any]) -> bool:
        """Safely broadcast regular news via Telegram with advanced user filtering"""
        try:
            # Get filtered users for regular delivery
            filtered_users = await self.user_filter.get_filtered_users_for_news(item, "regular")
            
            if not filtered_users:
                self.logger.debug(
                    "No users qualify for regular Telegram notification after filtering",
                    item_title=item.get('title', 'Unknown'),
                    importance=item.get('importance_score', 1)
                )
                return False
            
            # Send to filtered users
            user_telegram_ids = [user['telegram_id'] for user in filtered_users]
            await self.telegram_notifier.bot.send_news_alert(user_telegram_ids, item)
            
            # Record delivery for each user
            for user in filtered_users:
                await self.user_filter.record_news_delivery(
                    user['telegram_id'], 
                    item, 
                    "regular", 
                    True
                )
            
            self.logger.info(
                "Regular Telegram broadcast completed with filtering",
                item_title=item.get('title', 'Unknown'),
                filtered_users=len(filtered_users)
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "Telegram regular broadcast failed",
                item_title=item.get('title', 'Unknown'),
                error=str(e)
            )
            # Record failed delivery attempts
            try:
                all_users = await self.user_filter.get_filtered_users_for_news(item, "regular")
                for user in all_users:
                    await self.user_filter.record_news_delivery(
                        user['telegram_id'], 
                        item, 
                        "regular", 
                        False
                    )
            except:
                pass  # Don't fail the whole operation if delivery recording fails
            
        return False
    
    async def get_broadcast_statistics(self) -> Dict[str, Any]:
        """Get broadcasting system statistics"""
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                
                # Get user statistics
                total_users = await user_repo.get_subscribed_user_ids(urgent_only=False)
                urgent_subscribers = await user_repo.get_subscribed_user_ids(urgent_only=True)
                digest_subscribers = await user_repo.get_digest_subscribers()
                
                # Get news statistics (last 24 hours)
                from datetime import datetime, timedelta
                yesterday = datetime.now() - timedelta(days=1)
                
                stmt = select(NewsItem).where(NewsItem.created_at >= yesterday)
                result = await db.execute(stmt)
                recent_news = result.scalars().all()
                
                urgent_news = [item for item in recent_news if item.is_urgent]
                
                stats = {
                    'user_statistics': {
                        'total_subscribed_users': len(total_users),
                        'urgent_subscribers': len(urgent_subscribers),
                        'digest_subscribers': len(digest_subscribers)
                    },
                    'news_statistics_24h': {
                        'total_news_processed': len(recent_news),
                        'urgent_news_count': len(urgent_news),
                        'average_importance': sum(item.importance_score for item in recent_news) / len(recent_news) if recent_news else 0
                    },
                    'system_status': {
                        'websocket_configured': self.websocket_broadcast_func is not None,
                        'telegram_configured': True,
                        'ai_analyzer_configured': True,
                        'last_updated': datetime.now().isoformat()
                    }
                }
                
                return stats
                
        except Exception as e:
            self.logger.error(
                "Error getting broadcast statistics",
                error=str(e),
                exc_info=True
            )
            return {
                'error': 'Failed to retrieve statistics',
                'system_status': {
                    'websocket_configured': self.websocket_broadcast_func is not None,
                    'telegram_configured': True,
                    'ai_analyzer_configured': True,
                    'last_updated': datetime.now().isoformat()
                }
            }