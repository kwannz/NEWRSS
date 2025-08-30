import pytest
from app.core.settings import Settings

class TestSettings:
    
    def test_settings_defaults(self):
        """测试设置默认值"""
        settings = Settings()
        
        assert settings.ENV == "dev"
        assert settings.DATABASE_URL == "sqlite+aiosqlite:///./newrss.db"
        assert settings.REDIS_URL == "redis://localhost:6379/0"
        assert settings.TELEGRAM_BOT_TOKEN == ""
        assert settings.TELEGRAM_WEBHOOK_URL is None
        assert settings.TELEGRAM_SECRET_TOKEN is None
        assert settings.OPENAI_API_KEY is None
        assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]
        assert settings.SECRET_KEY == "your-secret-key-change-in-production"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_settings_custom_values(self):
        """测试自定义设置值"""
        custom_settings = Settings(
            ENV="prod",
            DATABASE_URL="postgresql://custom:custom@localhost/custom",
            REDIS_URL="redis://localhost:6380/1",
            TELEGRAM_BOT_TOKEN="custom_bot_token",
            TELEGRAM_WEBHOOK_URL="https://example.com/webhook",
            TELEGRAM_SECRET_TOKEN="webhook_secret",
            OPENAI_API_KEY="custom_openai_key",
            CORS_ORIGINS=["https://production.com"],
            SECRET_KEY="production-secret-key",
            ACCESS_TOKEN_EXPIRE_MINUTES=60
        )
        
        assert custom_settings.ENV == "prod"
        assert custom_settings.DATABASE_URL == "postgresql://custom:custom@localhost/custom"
        assert custom_settings.REDIS_URL == "redis://localhost:6380/1"
        assert custom_settings.TELEGRAM_BOT_TOKEN == "custom_bot_token"
        assert custom_settings.TELEGRAM_WEBHOOK_URL == "https://example.com/webhook"
        assert custom_settings.TELEGRAM_SECRET_TOKEN == "webhook_secret"
        assert custom_settings.OPENAI_API_KEY == "custom_openai_key"
        assert custom_settings.CORS_ORIGINS == ["https://production.com"]
        assert custom_settings.SECRET_KEY == "production-secret-key"
        assert custom_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60

    def test_settings_type_validation(self):
        """测试设置类型验证"""
        # 测试整数类型
        settings = Settings(ACCESS_TOKEN_EXPIRE_MINUTES=120)
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 120
        assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        
        # 测试列表类型
        settings = Settings(CORS_ORIGINS=["http://test1.com", "http://test2.com"])
        assert len(settings.CORS_ORIGINS) == 2
        assert isinstance(settings.CORS_ORIGINS, list)

    def test_settings_env_file_config(self):
        """测试.env文件配置"""
        settings = Settings()
        assert hasattr(settings.Config, 'env_file')
        assert settings.Config.env_file == ".env"

    def test_settings_cors_origins_list(self):
        """测试CORS origins列表处理"""
        settings = Settings()
        
        assert isinstance(settings.CORS_ORIGINS, list)
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "http://127.0.0.1:3000" in settings.CORS_ORIGINS

    def test_settings_optional_fields(self):
        """测试可选字段"""
        settings = Settings()
        
        # 这些字段应该是可选的
        optional_fields = [
            'TELEGRAM_WEBHOOK_URL',
            'TELEGRAM_SECRET_TOKEN', 
            'OPENAI_API_KEY'
        ]
        
        for field in optional_fields:
            value = getattr(settings, field)
            assert value is None or isinstance(value, str)

    def test_settings_required_fields(self):
        """测试必需字段不为空"""
        settings = Settings()
        
        # 这些字段应该有默认值
        required_fields = {
            'ENV': str,
            'DATABASE_URL': str,
            'REDIS_URL': str,
            'SECRET_KEY': str,
            'ACCESS_TOKEN_EXPIRE_MINUTES': int,
            'CORS_ORIGINS': list
        }
        
        for field, expected_type in required_fields.items():
            value = getattr(settings, field)
            assert value is not None
            assert isinstance(value, expected_type)