from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.subscription import UserSubscription, UserCategory
from app.core.logging import get_service_logger
import json

logger = get_service_logger("user_repository")

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        """Get user by Telegram ID"""
        try:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by Telegram ID {telegram_id}: {str(e)}")
            raise

    async def create_telegram_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new Telegram user"""
        try:
            user = User(
                telegram_id=str(user_data["id"]),
                telegram_username=user_data.get("username"),
                telegram_first_name=user_data.get("first_name"),
                telegram_last_name=user_data.get("last_name"),
                telegram_language_code=user_data.get("language_code", "en"),
                is_telegram_user=True,
                is_active=True
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Created Telegram user: {user.telegram_id}, username: {user.telegram_username}")
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating Telegram user: {str(e)}")
            raise

    async def update_user_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp"""
        try:
            from sqlalchemy.sql import func
            stmt = update(User).where(User.id == user_id).values(last_activity=func.now())
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating user activity for user {user_id}: {str(e)}")
            raise

    async def update_user_subscription_status(self, telegram_id: str, is_subscribed: bool) -> bool:
        """Update user's general subscription status"""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return False
                
            user.urgent_notifications = is_subscribed
            await self.db.commit()
            
            logger.info(f"Updated subscription status for user {telegram_id}: {is_subscribed}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription status: {str(e)}")
            await self.db.rollback()
            raise

    async def update_user_settings(self, telegram_id: str, settings: Dict[str, Any]) -> bool:
        """Update user notification settings"""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return False

            # Update individual settings
            if "urgent_notifications" in settings:
                user.urgent_notifications = settings["urgent_notifications"]
            if "daily_digest" in settings:
                user.daily_digest = settings["daily_digest"]
            if "digest_time" in settings:
                user.digest_time = settings["digest_time"]
            if "min_importance_score" in settings:
                user.min_importance_score = settings["min_importance_score"]
            if "max_daily_notifications" in settings:
                user.max_daily_notifications = settings["max_daily_notifications"]
            if "timezone" in settings:
                user.timezone = settings["timezone"]
            
            # Store additional settings as JSON
            if "push_settings" in settings:
                user.push_settings = json.dumps(settings["push_settings"])

            await self.db.commit()
            logger.info(f"Updated settings for user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user settings: {str(e)}")
            await self.db.rollback()
            raise

    async def get_user_settings(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Get user's notification settings"""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return None

            settings = {
                "urgent_notifications": user.urgent_notifications,
                "daily_digest": user.daily_digest,
                "digest_time": user.digest_time,
                "min_importance_score": user.min_importance_score,
                "max_daily_notifications": user.max_daily_notifications,
                "timezone": user.timezone,
                "push_settings": json.loads(user.push_settings) if user.push_settings else {}
            }
            
            return settings
            
        except Exception as e:
            logger.error(f"Error getting user settings: {str(e)}")
            raise

    async def get_subscribed_user_ids(self, urgent_only: bool = False) -> List[str]:
        """Get Telegram IDs of subscribed users"""
        try:
            conditions = [User.is_active == True, User.telegram_id.isnot(None)]
            
            if urgent_only:
                conditions.append(User.urgent_notifications == True)
            
            stmt = select(User.telegram_id).where(and_(*conditions))
            result = await self.db.execute(stmt)
            
            user_ids = [row[0] for row in result.fetchall() if row[0]]
            logger.debug(f"Found {len(user_ids)} subscribed users (urgent_only={urgent_only})")
            
            return user_ids
            
        except Exception as e:
            logger.error(f"Error getting subscribed user IDs: {str(e)}")
            raise

    async def get_digest_subscribers(self) -> List[Dict[str, Any]]:
        """Get users who want daily digest"""
        try:
            stmt = select(User).where(
                and_(
                    User.is_active == True,
                    User.telegram_id.isnot(None),
                    User.daily_digest == True
                )
            )
            
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            
            digest_users = []
            for user in users:
                digest_users.append({
                    "telegram_id": user.telegram_id,
                    "digest_time": user.digest_time,
                    "timezone": user.timezone,
                    "min_importance_score": user.min_importance_score
                })
            
            logger.debug(f"Found {len(digest_users)} digest subscribers")
            return digest_users
            
        except Exception as e:
            logger.error(f"Error getting digest subscribers: {str(e)}")
            raise

    async def subscribe_to_category(self, telegram_id: str, category: str, min_importance: int = 1) -> bool:
        """Subscribe user to a news category"""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return False

            # Check if subscription already exists
            stmt = select(UserCategory).where(
                and_(
                    UserCategory.user_id == user.id,
                    UserCategory.category == category
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.is_subscribed = True
                existing.min_importance = min_importance
            else:
                subscription = UserCategory(
                    user_id=user.id,
                    category=category,
                    is_subscribed=True,
                    min_importance=min_importance
                )
                self.db.add(subscription)

            await self.db.commit()
            logger.info(f"User {telegram_id} subscribed to category {category}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to category: {str(e)}")
            await self.db.rollback()
            raise

    async def unsubscribe_from_category(self, telegram_id: str, category: str) -> bool:
        """Unsubscribe user from a news category"""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return False

            stmt = update(UserCategory).where(
                and_(
                    UserCategory.user_id == user.id,
                    UserCategory.category == category
                )
            ).values(is_subscribed=False)
            
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(f"User {telegram_id} unsubscribed from category {category}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error unsubscribing from category: {str(e)}")
            await self.db.rollback()
            raise

    async def get_user_categories(self, telegram_id: str) -> List[Dict[str, Any]]:
        """Get user's category subscriptions"""
        try:
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []

            stmt = select(UserCategory).where(UserCategory.user_id == user.id)
            result = await self.db.execute(stmt)
            categories = result.scalars().all()

            return [
                {
                    "category": cat.category,
                    "is_subscribed": cat.is_subscribed,
                    "min_importance": cat.min_importance
                }
                for cat in categories
            ]

        except Exception as e:
            logger.error(f"Error getting user categories: {str(e)}")
            raise

    async def get_users_for_news_notification(self, importance_score: int, category: str = None) -> List[str]:
        """Get users who should receive a news notification based on importance and category"""
        try:
            conditions = [
                User.is_active == True,
                User.telegram_id.isnot(None),
                User.urgent_notifications == True,
                User.min_importance_score <= importance_score
            ]

            if category:
                # Join with UserCategory to check category subscriptions
                stmt = (
                    select(User.telegram_id)
                    .join(UserCategory, User.id == UserCategory.user_id)
                    .where(
                        and_(
                            *conditions,
                            UserCategory.category == category,
                            UserCategory.is_subscribed == True,
                            UserCategory.min_importance <= importance_score
                        )
                    )
                )
            else:
                stmt = select(User.telegram_id).where(and_(*conditions))

            result = await self.db.execute(stmt)
            user_ids = [row[0] for row in result.fetchall() if row[0]]
            
            logger.debug(f"Found {len(user_ids)} users for notification (importance={importance_score}, category={category})")
            return user_ids

        except Exception as e:
            logger.error(f"Error getting users for notification: {str(e)}")
            raise