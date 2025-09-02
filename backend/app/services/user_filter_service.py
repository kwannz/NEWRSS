from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from app.core.logging import get_service_logger
from app.core.database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.core.redis import get_redis
import json

class UserFilterService:
    """
    Advanced user filtering service for personalized news notifications
    """
    
    def __init__(self):
        self.logger = get_service_logger("user_filter")
        self.redis_key_prefix = "news_delivery:"
    
    async def get_filtered_users_for_news(
        self, 
        news_item: Dict[str, Any], 
        delivery_type: str = "regular"  # regular, urgent, digest
    ) -> List[Dict[str, Any]]:
        """
        Get users who should receive a specific news item based on sophisticated filtering
        
        Args:
            news_item: The news item to filter users for
            delivery_type: Type of delivery (regular, urgent, digest)
        
        Returns:
            List of user data with delivery preferences
        """
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                
                # Get base user set based on delivery type
                if delivery_type == "urgent":
                    user_ids = await user_repo.get_subscribed_user_ids(urgent_only=True)
                elif delivery_type == "digest":
                    digest_users = await user_repo.get_digest_subscribers()
                    user_ids = [user['telegram_id'] for user in digest_users]
                else:
                    user_ids = await user_repo.get_subscribed_user_ids(urgent_only=False)
                
                if not user_ids:
                    self.logger.info("No subscribed users found", delivery_type=delivery_type)
                    return []
                
                # Apply advanced filtering
                filtered_users = []
                for telegram_id in user_ids:
                    user_data = await self._get_user_delivery_profile(telegram_id)
                    if await self._should_user_receive_news(user_data, news_item, delivery_type):
                        filtered_users.append(user_data)
                
                self.logger.info(
                    "User filtering completed",
                    total_candidates=len(user_ids),
                    filtered_count=len(filtered_users),
                    delivery_type=delivery_type,
                    news_category=news_item.get('category'),
                    news_importance=news_item.get('importance_score', 1)
                )
                
                return filtered_users
                
        except Exception as e:
            self.logger.error(
                "Error in user filtering",
                delivery_type=delivery_type,
                news_title=news_item.get('title', 'Unknown'),
                error=str(e),
                exc_info=True
            )
            return []
    
    async def _get_user_delivery_profile(self, telegram_id: str) -> Dict[str, Any]:
        """Get comprehensive user delivery profile"""
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                
                # Get user settings
                settings = await user_repo.get_user_settings(telegram_id)
                if not settings:
                    return {}
                
                # Get user categories
                categories = await user_repo.get_user_categories(telegram_id)
                
                # Get delivery statistics from Redis
                redis = await get_redis()
                stats_key = f"{self.redis_key_prefix}stats:{telegram_id}"
                daily_count_key = f"{self.redis_key_prefix}daily:{telegram_id}:{datetime.now().strftime('%Y-%m-%d')}"
                
                stats_data = await redis.get(stats_key)
                daily_count = await redis.get(daily_count_key)
                
                profile = {
                    'telegram_id': telegram_id,
                    'settings': settings,
                    'categories': {cat['category']: cat for cat in categories},
                    'daily_notifications_sent': int(daily_count or 0),
                    'delivery_stats': json.loads(stats_data) if stats_data else {}
                }
                
                return profile
                
        except Exception as e:
            self.logger.error(
                "Error getting user delivery profile",
                telegram_id=telegram_id,
                error=str(e)
            )
            return {}
    
    async def _should_user_receive_news(
        self, 
        user_profile: Dict[str, Any], 
        news_item: Dict[str, Any], 
        delivery_type: str
    ) -> bool:
        """Determine if user should receive specific news item"""
        try:
            if not user_profile:
                return False
            
            settings = user_profile.get('settings', {})
            categories = user_profile.get('categories', {})
            
            # Check if user is active and has proper settings
            if not settings.get('urgent_notifications', False) and delivery_type in ['urgent', 'regular']:
                return False
            
            if not settings.get('daily_digest', False) and delivery_type == 'digest':
                return False
            
            # Check daily notification limits
            daily_sent = user_profile.get('daily_notifications_sent', 0)
            max_daily = settings.get('max_daily_notifications', 10)
            
            if delivery_type == 'regular' and daily_sent >= max_daily:
                self.logger.debug(
                    "User reached daily notification limit",
                    telegram_id=user_profile.get('telegram_id'),
                    daily_sent=daily_sent,
                    max_daily=max_daily
                )
                return False
            
            # Check importance score filter
            min_importance = settings.get('min_importance_score', 1)
            news_importance = news_item.get('importance_score', 1)
            
            if news_importance < min_importance:
                return False
            
            # Check category preferences
            news_category = news_item.get('category', 'general')
            
            # If user has category preferences, check them
            if categories:
                category_pref = categories.get(news_category)
                if category_pref:
                    # User has specific preference for this category
                    if not category_pref.get('is_subscribed', False):
                        return False
                    
                    # Check category-specific minimum importance
                    category_min_importance = category_pref.get('min_importance', 1)
                    if news_importance < category_min_importance:
                        return False
                else:
                    # User has categories configured but not this one - check if they want general news
                    if news_category != 'general':
                        return False
            
            # Urgent news bypass some filters
            if delivery_type == 'urgent' and news_item.get('is_urgent', False):
                return True  # Urgent news bypasses most filters except basic subscription
            
            # Check for content quality and spam prevention
            if await self._is_likely_spam_for_user(user_profile, news_item):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Error in user news filtering decision",
                telegram_id=user_profile.get('telegram_id', 'unknown'),
                news_title=news_item.get('title', 'Unknown'),
                error=str(e)
            )
            return False
    
    async def _is_likely_spam_for_user(self, user_profile: Dict[str, Any], news_item: Dict[str, Any]) -> bool:
        """Check if news item is likely spam for this specific user"""
        try:
            # Basic spam indicators
            title = news_item.get('title', '').lower()
            content = news_item.get('content', '').lower()
            
            # Check for low-quality content indicators
            spam_indicators = [
                'click here', 'limited time', 'act now', 'free money',
                '100% profit', 'guaranteed', 'risk-free', 'get rich quick'
            ]
            
            text = f"{title} {content}"
            spam_score = sum(1 for indicator in spam_indicators if indicator in text)
            
            # High spam score indicates likely spam
            if spam_score >= 3:
                self.logger.debug(
                    "News item flagged as potential spam",
                    news_title=news_item.get('title'),
                    spam_score=spam_score
                )
                return True
            
            # Check if user has received similar news recently (duplicate prevention)
            return await self._is_duplicate_for_user(user_profile, news_item)
            
        except Exception as e:
            self.logger.error(
                "Error in spam detection",
                error=str(e)
            )
            return False
    
    async def _is_duplicate_for_user(self, user_profile: Dict[str, Any], news_item: Dict[str, Any]) -> bool:
        """Check if user recently received similar news"""
        try:
            redis = await get_redis()
            telegram_id = user_profile.get('telegram_id')
            
            # Create content fingerprint
            title_words = set(news_item.get('title', '').lower().split())
            content_preview = news_item.get('content', '')[:200].lower()
            
            # Check recent news hashes for this user
            user_recent_key = f"{self.redis_key_prefix}recent:{telegram_id}"
            recent_news = await redis.lrange(user_recent_key, 0, 9)  # Last 10 items
            
            for recent_item in recent_news:
                try:
                    recent_data = json.loads(recent_item)
                    recent_title_words = set(recent_data.get('title', '').lower().split())
                    
                    # Check for significant title overlap
                    if title_words and recent_title_words:
                        overlap = len(title_words.intersection(recent_title_words))
                        if overlap >= len(title_words) * 0.7:  # 70% title overlap
                            return True
                    
                except json.JSONDecodeError:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(
                "Error in duplicate detection",
                error=str(e)
            )
            return False
    
    async def record_news_delivery(
        self, 
        telegram_id: str, 
        news_item: Dict[str, Any], 
        delivery_type: str,
        success: bool
    ) -> None:
        """Record news delivery for analytics and filtering"""
        try:
            redis = await get_redis()
            
            # Update daily count
            daily_key = f"{self.redis_key_prefix}daily:{telegram_id}:{datetime.now().strftime('%Y-%m-%d')}"
            await redis.incr(daily_key)
            await redis.expire(daily_key, 86400)  # 24 hours
            
            # Add to recent news list
            recent_key = f"{self.redis_key_prefix}recent:{telegram_id}"
            news_record = {
                'title': news_item.get('title', ''),
                'category': news_item.get('category', 'general'),
                'importance': news_item.get('importance_score', 1),
                'delivered_at': datetime.now().isoformat(),
                'delivery_type': delivery_type,
                'success': success
            }
            
            await redis.lpush(recent_key, json.dumps(news_record))
            await redis.ltrim(recent_key, 0, 19)  # Keep last 20 items
            await redis.expire(recent_key, 604800)  # 7 days
            
            # Update delivery statistics
            stats_key = f"{self.redis_key_prefix}stats:{telegram_id}"
            stats_data = await redis.get(stats_key)
            
            if stats_data:
                stats = json.loads(stats_data)
            else:
                stats = {'total_delivered': 0, 'categories': {}, 'delivery_types': {}}
            
            stats['total_delivered'] += 1
            category = news_item.get('category', 'general')
            stats['categories'][category] = stats['categories'].get(category, 0) + 1
            stats['delivery_types'][delivery_type] = stats['delivery_types'].get(delivery_type, 0) + 1
            stats['last_delivery'] = datetime.now().isoformat()
            
            await redis.setex(stats_key, 2592000, json.dumps(stats))  # 30 days
            
        except Exception as e:
            self.logger.error(
                "Error recording news delivery",
                telegram_id=telegram_id,
                delivery_type=delivery_type,
                error=str(e)
            )
    
    async def get_user_delivery_stats(self, telegram_id: str) -> Dict[str, Any]:
        """Get user's news delivery statistics"""
        try:
            redis = await get_redis()
            
            # Get current day count
            daily_key = f"{self.redis_key_prefix}daily:{telegram_id}:{datetime.now().strftime('%Y-%m-%d')}"
            daily_count = await redis.get(daily_key)
            
            # Get overall stats
            stats_key = f"{self.redis_key_prefix}stats:{telegram_id}"
            stats_data = await redis.get(stats_key)
            
            # Get recent deliveries
            recent_key = f"{self.redis_key_prefix}recent:{telegram_id}"
            recent_items = await redis.lrange(recent_key, 0, 4)  # Last 5 items
            
            stats = {
                'daily_notifications_sent': int(daily_count or 0),
                'total_stats': json.loads(stats_data) if stats_data else {},
                'recent_deliveries': [json.loads(item) for item in recent_items if item],
                'timestamp': datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Error getting user delivery stats",
                telegram_id=telegram_id,
                error=str(e)
            )
            return {}
    
    async def reset_daily_limits(self) -> int:
        """Reset daily notification limits (called by scheduler)"""
        try:
            redis = await get_redis()
            yesterday_pattern = f"{self.redis_key_prefix}daily:*:{(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}"
            
            # Clean up old daily counters
            old_keys = []
            async for key in redis.scan_iter(match=yesterday_pattern):
                old_keys.append(key)
            
            if old_keys:
                await redis.delete(*old_keys)
                self.logger.info("Cleaned up daily notification counters", count=len(old_keys))
            
            return len(old_keys)
            
        except Exception as e:
            self.logger.error(
                "Error resetting daily limits",
                error=str(e),
                exc_info=True
            )
            return 0