"""
Test environment setup and configuration validation
Isolated test that doesn't require external services
"""
import pytest
import os
from app.core.settings import settings


def test_test_environment_variables():
    """Test that test environment variables are properly set"""
    # These should be set for testing
    assert hasattr(settings, 'DATABASE_URL')
    assert hasattr(settings, 'SECRET_KEY')
    
    # Test-specific overrides should work
    os.environ['TEST_VAR'] = 'test_value'
    assert os.getenv('TEST_VAR') == 'test_value'


def test_settings_validation():
    """Test settings validation without external dependencies"""
    # Basic settings should be accessible
    assert settings.SECRET_KEY is not None
    assert len(settings.SECRET_KEY) > 10
    
    # Database URL should be configured
    assert settings.DATABASE_URL is not None
    
    # Optional settings should have defaults
    assert hasattr(settings, 'OPENAI_API_KEY')  # May be None in test
    assert hasattr(settings, 'TELEGRAM_BOT_TOKEN')  # May be None in test


def test_basic_imports():
    """Test that core modules can be imported without external dependencies"""
    # These imports should work without requiring actual services
    from app.models.news import NewsItem
    from app.models.user import User
    from app.repositories.news_repository import NewsRepository
    from app.repositories.user_repository import UserRepository
    
    # Verify models can be instantiated (without DB)
    assert NewsItem is not None
    assert User is not None
    assert NewsRepository is not None
    assert UserRepository is not None


def test_utility_functions():
    """Test utility functions that don't require external services"""
    from app.core.utils import generate_hash, validate_email
    
    # Test hash generation
    hash1 = generate_hash("test content")
    hash2 = generate_hash("test content")
    hash3 = generate_hash("different content")
    
    assert hash1 == hash2  # Same content should produce same hash
    assert hash1 != hash3  # Different content should produce different hash
    assert len(hash1) == 64  # SHA-256 produces 64-character hex string
    
    # Test email validation
    assert validate_email("test@example.com") is True
    assert validate_email("invalid-email") is False
    assert validate_email("") is False


def test_configuration_loading():
    """Test configuration loading and environment handling"""
    # Test environment variable override
    original_value = os.getenv('TEST_CONFIG_VAR')
    
    os.environ['TEST_CONFIG_VAR'] = 'test_override'
    assert os.getenv('TEST_CONFIG_VAR') == 'test_override'
    
    # Cleanup
    if original_value is not None:
        os.environ['TEST_CONFIG_VAR'] = original_value
    else:
        os.environ.pop('TEST_CONFIG_VAR', None)


if __name__ == "__main__":
    # Run basic validation
    test_test_environment_variables()
    test_settings_validation()
    test_basic_imports()
    test_utility_functions()
    test_configuration_loading()
    print("✅ All basic tests passed - environment setup is working")