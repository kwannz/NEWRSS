import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.auth import get_password_hash, verify_password

class TestUser:
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """测试创建用户"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            telegram_id="123456789",
            telegram_username="testuser_tg",
            is_active=True,
            is_verified=True,
            urgent_notifications=True,
            daily_digest=False,
            push_settings='{"importance_threshold": 3}'
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.telegram_id == "123456789"
        assert user.telegram_username == "testuser_tg"
        assert user.is_active is True
        assert user.is_verified is True
        assert user.urgent_notifications is True
        assert user.daily_digest is False
        assert user.push_settings == '{"importance_threshold": 3}'
        assert user.created_at is not None
        assert user.updated_at is None

    @pytest.mark.asyncio
    async def test_user_defaults(self, db_session: AsyncSession):
        """测试用户默认值"""
        user = User(
            username="defaultuser",
            email="default@example.com",
            hashed_password=get_password_hash("password")
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.is_active is True
        assert user.is_verified is False
        assert user.urgent_notifications is True
        assert user.daily_digest is False
        assert user.telegram_id is None
        assert user.telegram_username is None
        assert user.push_settings is None

    @pytest.mark.asyncio
    async def test_user_unique_username(self, db_session: AsyncSession):
        """测试用户名唯一性约束"""
        user1 = User(
            username="uniqueuser",
            email="user1@example.com",
            hashed_password=get_password_hash("password1")
        )
        
        user2 = User(
            username="uniqueuser",  # 相同用户名
            email="user2@example.com",
            hashed_password=get_password_hash("password2")
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # 用户名唯一性约束
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_unique_email(self, db_session: AsyncSession):
        """测试邮箱唯一性约束"""
        email = "duplicate@example.com"
        
        user1 = User(
            username="user1",
            email=email,
            hashed_password=get_password_hash("password1")
        )
        
        user2 = User(
            username="user2",
            email=email,  # 相同邮箱
            hashed_password=get_password_hash("password2")
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # 邮箱唯一性约束
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_unique_telegram_id(self, db_session: AsyncSession):
        """测试Telegram ID唯一性约束"""
        telegram_id = "987654321"
        
        user1 = User(
            username="tguser1",
            email="tg1@example.com",
            hashed_password=get_password_hash("password1"),
            telegram_id=telegram_id
        )
        
        user2 = User(
            username="tguser2",
            email="tg2@example.com",
            hashed_password=get_password_hash("password2"),
            telegram_id=telegram_id  # 相同Telegram ID
        )
        
        db_session.add(user1)
        await db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Telegram ID唯一性约束
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_password_hashing(self, db_session: AsyncSession):
        """测试密码哈希和验证"""
        password = "mysecurepassword123"
        hashed_password = get_password_hash(password)
        
        user = User(
            username="hashuser",
            email="hash@example.com",
            hashed_password=hashed_password
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 验证密码哈希不是明文
        assert user.hashed_password != password
        assert len(user.hashed_password) > 50  # bcrypt哈希长度
        
        # 验证密码验证功能
        assert verify_password(password, user.hashed_password) is True
        assert verify_password("wrongpassword", user.hashed_password) is False

    @pytest.mark.asyncio
    async def test_user_update_notification_settings(self, db_session: AsyncSession):
        """测试更新用户通知设置"""
        user = User(
            username="settingsuser",
            email="settings@example.com",
            hashed_password=get_password_hash("password"),
            urgent_notifications=True,
            daily_digest=False
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 更新设置
        user.urgent_notifications = False
        user.daily_digest = True
        user.push_settings = '{"categories": ["bitcoin", "ethereum"], "min_importance": 3}'
        
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.urgent_notifications is False
        assert user.daily_digest is True
        assert user.push_settings == '{"categories": ["bitcoin", "ethereum"], "min_importance": 3}'
        assert user.updated_at is not None

    @pytest.mark.asyncio
    async def test_user_telegram_integration(self, db_session: AsyncSession):
        """测试Telegram集成字段"""
        user = User(
            username="telegramuser",
            email="telegram@example.com",
            hashed_password=get_password_hash("password")
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # 添加Telegram信息
        user.telegram_id = "555666777"
        user.telegram_username = "crypto_fan"
        
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.telegram_id == "555666777"
        assert user.telegram_username == "crypto_fan"

    @pytest.mark.asyncio
    async def test_user_deactivation(self, db_session: AsyncSession):
        """测试用户停用功能"""
        user = User(
            username="deactivateuser",
            email="deactivate@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.is_active is True
        
        # 停用用户
        user.is_active = False
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.is_active is False