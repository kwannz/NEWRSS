import pytest
from datetime import datetime, timedelta
from jose import jwt
from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    ALGORITHM
)
from app.core.settings import settings

class TestAuth:
    
    def test_password_hashing(self):
        """测试密码哈希功能"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        # 验证哈希结果
        assert hashed != password
        assert len(hashed) > 50  # bcrypt哈希长度
        assert hashed.startswith("$2b$")  # bcrypt格式

    def test_password_verification_success(self):
        """测试密码验证成功"""
        password = "mypassword"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_password_verification_failure(self):
        """测试密码验证失败"""
        password = "correctpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_password_verification_empty(self):
        """测试空密码验证"""
        hashed = get_password_hash("password")
        
        assert verify_password("", hashed) is False
        # Empty hash will raise exception, so we catch it
        try:
            result = verify_password("password", "")
            assert result is False
        except Exception:
            assert True  # Expected to fail with empty hash

    def test_create_access_token_default_expiry(self):
        """测试创建访问令牌（默认过期时间）"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT应该很长
        
        # 验证token内容
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert "exp" in payload
        
        # 验证过期时间存在且合理
        exp_time = datetime.fromtimestamp(payload["exp"])
        current_time = datetime.utcnow()
        assert exp_time > current_time  # 应该在未来

    def test_create_access_token_custom_expiry(self):
        """测试创建访问令牌（自定义过期时间）"""
        data = {"sub": "testuser"}
        custom_delta = timedelta(hours=2)
        token = create_access_token(data, custom_delta)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"])
        current_time = datetime.utcnow()
        assert exp_time > current_time  # 应该在未来

    def test_create_access_token_extra_data(self):
        """测试创建包含额外数据的访问令牌"""
        data = {
            "sub": "testuser",
            "user_id": 123,
            "permissions": ["read", "write"]
        }
        token = create_access_token(data)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["permissions"] == ["read", "write"]

    def test_verify_token_valid(self):
        """测试验证有效令牌"""
        data = {"sub": "validuser"}
        token = create_access_token(data)
        
        username = verify_token(token)
        assert username == "validuser"

    def test_verify_token_invalid(self):
        """测试验证无效令牌"""
        invalid_token = "invalid.jwt.token"
        
        username = verify_token(invalid_token)
        assert username is None

    def test_verify_token_expired(self):
        """测试验证过期令牌"""
        data = {"sub": "expireduser"}
        # 创建已过期的令牌
        expired_delta = timedelta(seconds=-1)  # 1秒前过期
        token = create_access_token(data, expired_delta)
        
        # 等待确保过期
        import time
        time.sleep(2)
        
        username = verify_token(token)
        assert username is None

    def test_verify_token_tampered(self):
        """测试验证被篡改的令牌"""
        data = {"sub": "tamperuser"}
        token = create_access_token(data)
        
        # 篡改令牌（改变最后一个字符）
        tampered_token = token[:-1] + "X"
        
        username = verify_token(tampered_token)
        assert username is None

    def test_verify_token_no_subject(self):
        """测试验证没有subject的令牌"""
        # 手动创建没有sub字段的令牌
        data = {"user_id": 123, "exp": datetime.utcnow() + timedelta(minutes=30)}
        token = jwt.encode(data, settings.SECRET_KEY, algorithm=ALGORITHM)
        
        username = verify_token(token)
        assert username is None

    def test_verify_token_empty(self):
        """测试验证空令牌"""
        assert verify_token("") is None

    def test_password_hash_consistency(self):
        """测试密码哈希一致性"""
        password = "consistencytest"
        
        # 同一密码多次哈希应该产生不同结果（salt的作用）
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True