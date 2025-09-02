import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock
import json

from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.models.subscription import UserSubscription, UserCategory
from app.core.database import SessionLocal


@pytest.fixture
async def user_repo(db_session: AsyncSession):
    """Create user repository fixture"""
    return UserRepository(db_session)


@pytest.fixture
def telegram_user_data():
    """Sample Telegram user data"""
    return {
        "id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "en"
    }


@pytest.fixture 
async def sample_user(db_session: AsyncSession, telegram_user_data):
    """Create sample user in database"""
    user = User(
        telegram_id=str(telegram_user_data["id"]),
        telegram_username=telegram_user_data["username"],
        telegram_first_name=telegram_user_data["first_name"],
        telegram_last_name=telegram_user_data["last_name"],
        telegram_language_code=telegram_user_data["language_code"],
        is_telegram_user=True,
        is_active=True
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


class TestUserRepository:
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_exists(self, user_repo, sample_user):
        """Test getting existing user by Telegram ID"""
        user = await user_repo.get_user_by_telegram_id(sample_user.telegram_id)
        
        assert user is not None
        assert user.telegram_id == sample_user.telegram_id
        assert user.telegram_username == sample_user.telegram_username
        
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id_not_exists(self, user_repo):
        """Test getting non-existing user by Telegram ID"""
        user = await user_repo.get_user_by_telegram_id("999999999")
        
        assert user is None
        
    @pytest.mark.asyncio
    async def test_create_telegram_user(self, user_repo, telegram_user_data):
        """Test creating new Telegram user"""
        user = await user_repo.create_telegram_user(telegram_user_data)
        
        assert user is not None
        assert user.telegram_id == str(telegram_user_data["id"])
        assert user.telegram_username == telegram_user_data["username"]
        assert user.telegram_first_name == telegram_user_data["first_name"]
        assert user.is_telegram_user is True
        assert user.is_active is True
        assert user.urgent_notifications is True  # Default value
        assert user.daily_digest is False  # Default value
        
    @pytest.mark.asyncio
    async def test_update_user_activity(self, user_repo, sample_user):
        """Test updating user activity timestamp"""
        original_activity = sample_user.last_activity
        
        await user_repo.update_user_activity(sample_user.id)
        
        # Refresh user from database
        await user_repo.db.refresh(sample_user)
        assert sample_user.last_activity is not None
        assert sample_user.last_activity != original_activity
        
    @pytest.mark.asyncio
    async def test_update_user_subscription_status(self, user_repo, sample_user):
        """Test updating user subscription status"""
        # Test enabling subscription
        result = await user_repo.update_user_subscription_status(
            sample_user.telegram_id, True
        )
        
        assert result is True
        await user_repo.db.refresh(sample_user)
        assert sample_user.urgent_notifications is True
        
        # Test disabling subscription
        result = await user_repo.update_user_subscription_status(
            sample_user.telegram_id, False
        )
        
        assert result is True
        await user_repo.db.refresh(sample_user)
        assert sample_user.urgent_notifications is False
        
    @pytest.mark.asyncio
    async def test_update_user_subscription_status_non_existing(self, user_repo):
        """Test updating subscription status for non-existing user"""
        result = await user_repo.update_user_subscription_status("999999999", True)
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_update_user_settings(self, user_repo, sample_user):
        """Test updating user settings"""
        settings = {
            "urgent_notifications": False,
            "daily_digest": True,
            "digest_time": "08:00",
            "min_importance_score": 3,
            "max_daily_notifications": 5,
            "timezone": "America/New_York",
            "push_settings": {"notifications": True, "sounds": False}
        }
        
        result = await user_repo.update_user_settings(
            sample_user.telegram_id, settings
        )
        
        assert result is True
        await user_repo.db.refresh(sample_user)
        
        assert sample_user.urgent_notifications is False
        assert sample_user.daily_digest is True
        assert sample_user.digest_time == "08:00"
        assert sample_user.min_importance_score == 3
        assert sample_user.max_daily_notifications == 5
        assert sample_user.timezone == "America/New_York"
        
        # Check JSON settings
        stored_settings = json.loads(sample_user.push_settings)
        assert stored_settings["notifications"] is True
        assert stored_settings["sounds"] is False
        
    @pytest.mark.asyncio
    async def test_get_user_settings(self, user_repo, sample_user):
        """Test getting user settings"""
        # First update some settings
        settings = {
            "urgent_notifications": True,
            "daily_digest": False,
            "digest_time": "10:00",
            "min_importance_score": 2
        }
        await user_repo.update_user_settings(sample_user.telegram_id, settings)
        
        # Get settings
        retrieved_settings = await user_repo.get_user_settings(sample_user.telegram_id)
        
        assert retrieved_settings is not None
        assert retrieved_settings["urgent_notifications"] is True
        assert retrieved_settings["daily_digest"] is False
        assert retrieved_settings["digest_time"] == "10:00"
        assert retrieved_settings["min_importance_score"] == 2
        
    @pytest.mark.asyncio 
    async def test_get_user_settings_non_existing(self, user_repo):
        """Test getting settings for non-existing user"""
        settings = await user_repo.get_user_settings("999999999")
        
        assert settings is None
        
    @pytest.mark.asyncio
    async def test_get_subscribed_user_ids(self, user_repo, sample_user):
        """Test getting subscribed user IDs"""
        # Enable notifications for sample user
        await user_repo.update_user_subscription_status(sample_user.telegram_id, True)
        
        # Get all subscribed users
        user_ids = await user_repo.get_subscribed_user_ids()
        
        assert sample_user.telegram_id in user_ids
        
        # Test urgent only
        user_ids_urgent = await user_repo.get_subscribed_user_ids(urgent_only=True)
        
        assert sample_user.telegram_id in user_ids_urgent
        
    @pytest.mark.asyncio
    async def test_get_digest_subscribers(self, user_repo, sample_user):
        """Test getting digest subscribers"""
        # Enable daily digest for sample user
        await user_repo.update_user_settings(
            sample_user.telegram_id, 
            {"daily_digest": True, "digest_time": "09:00"}
        )
        
        digest_users = await user_repo.get_digest_subscribers()
        
        assert len(digest_users) >= 1
        
        # Find our user in the results
        user_found = False
        for user in digest_users:
            if user["telegram_id"] == sample_user.telegram_id:
                user_found = True
                assert user["digest_time"] == "09:00"
                break
                
        assert user_found is True
        
    @pytest.mark.asyncio
    async def test_subscribe_to_category(self, user_repo, sample_user):
        """Test subscribing user to category"""
        result = await user_repo.subscribe_to_category(
            sample_user.telegram_id, "bitcoin", 2
        )
        
        assert result is True
        
        # Check category was created
        categories = await user_repo.get_user_categories(sample_user.telegram_id)
        
        bitcoin_category = None
        for cat in categories:
            if cat["category"] == "bitcoin":
                bitcoin_category = cat
                break
                
        assert bitcoin_category is not None
        assert bitcoin_category["is_subscribed"] is True
        assert bitcoin_category["min_importance"] == 2
        
    @pytest.mark.asyncio
    async def test_unsubscribe_from_category(self, user_repo, sample_user):
        """Test unsubscribing user from category"""
        # First subscribe to category
        await user_repo.subscribe_to_category(sample_user.telegram_id, "ethereum")
        
        # Then unsubscribe
        result = await user_repo.unsubscribe_from_category(
            sample_user.telegram_id, "ethereum"
        )
        
        assert result is True
        
        # Check category subscription status
        categories = await user_repo.get_user_categories(sample_user.telegram_id)
        
        ethereum_category = None
        for cat in categories:
            if cat["category"] == "ethereum":
                ethereum_category = cat
                break
                
        assert ethereum_category is not None
        assert ethereum_category["is_subscribed"] is False
        
    @pytest.mark.asyncio
    async def test_get_user_categories(self, user_repo, sample_user):
        """Test getting user categories"""
        # Subscribe to multiple categories
        await user_repo.subscribe_to_category(sample_user.telegram_id, "bitcoin", 3)
        await user_repo.subscribe_to_category(sample_user.telegram_id, "defi", 2)
        
        categories = await user_repo.get_user_categories(sample_user.telegram_id)
        
        assert len(categories) == 2
        
        # Check categories
        category_names = [cat["category"] for cat in categories]
        assert "bitcoin" in category_names
        assert "defi" in category_names
        
    @pytest.mark.asyncio
    async def test_get_users_for_news_notification(self, user_repo, sample_user):
        """Test getting users for news notification"""
        # Set up user preferences
        await user_repo.update_user_settings(
            sample_user.telegram_id,
            {
                "urgent_notifications": True,
                "min_importance_score": 2
            }
        )
        
        # Subscribe to bitcoin category
        await user_repo.subscribe_to_category(sample_user.telegram_id, "bitcoin", 2)
        
        # Test general notification (no category)
        user_ids = await user_repo.get_users_for_news_notification(3)
        assert sample_user.telegram_id in user_ids
        
        # Test category-specific notification
        user_ids_category = await user_repo.get_users_for_news_notification(
            3, "bitcoin"
        )
        assert sample_user.telegram_id in user_ids_category
        
        # Test with importance too low
        user_ids_low = await user_repo.get_users_for_news_notification(1)
        assert sample_user.telegram_id not in user_ids_low
        
    @pytest.mark.asyncio
    async def test_subscribe_to_category_updates_existing(self, user_repo, sample_user):
        """Test that subscribing to existing category updates it"""
        # Subscribe with min importance 1
        await user_repo.subscribe_to_category(sample_user.telegram_id, "nft", 1)
        
        # Subscribe again with different min importance  
        await user_repo.subscribe_to_category(sample_user.telegram_id, "nft", 3)
        
        categories = await user_repo.get_user_categories(sample_user.telegram_id)
        
        nft_category = None
        for cat in categories:
            if cat["category"] == "nft":
                nft_category = cat
                break
                
        assert nft_category is not None
        assert nft_category["min_importance"] == 3  # Updated value
        assert nft_category["is_subscribed"] is True
        
        # Check only one NFT category exists
        nft_count = sum(1 for cat in categories if cat["category"] == "nft")
        assert nft_count == 1