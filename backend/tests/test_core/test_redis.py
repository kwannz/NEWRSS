import pytest
from unittest.mock import patch, AsyncMock
from app.core.redis import get_redis, redis_client

class TestRedis:
    
    @pytest.mark.asyncio
    async def test_get_redis_returns_client(self):
        """测试get_redis返回Redis客户端"""
        client = await get_redis()
        assert client is not None
        assert client == redis_client

    @pytest.mark.asyncio
    async def test_redis_client_configuration(self):
        """测试Redis客户端配置"""
        assert redis_client is not None
        
        # 验证配置属性
        connection_pool = redis_client.connection_pool
        assert connection_pool.connection_kwargs['decode_responses'] is True
        assert connection_pool.connection_kwargs['encoding'] == 'utf-8'

    @pytest.mark.asyncio 
    async def test_redis_basic_operations(self, redis_client):
        """测试Redis基本操作"""
        # 设置值
        await redis_client.set("test_key", "test_value")
        
        # 获取值
        value = await redis_client.get("test_key")
        assert value == "test_value"
        
        # 删除值
        await redis_client.delete("test_key")
        value = await redis_client.get("test_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_redis_expiration(self, redis_client):
        """测试Redis过期功能"""
        # 设置带过期时间的值
        await redis_client.setex("expire_key", 1, "expire_value")
        
        # 立即获取应该存在
        value = await redis_client.get("expire_key")
        assert value == "expire_value"
        
        # 检查TTL
        ttl = await redis_client.ttl("expire_key")
        assert 0 < ttl <= 1

    @pytest.mark.asyncio
    async def test_redis_exists_check(self, redis_client):
        """测试Redis存在性检查"""
        # 测试不存在的键
        exists = await redis_client.exists("nonexistent_key")
        assert exists == 0
        
        # 设置键后测试存在性
        await redis_client.set("exists_key", "value")
        exists = await redis_client.exists("exists_key")
        assert exists == 1
        
        # 清理
        await redis_client.delete("exists_key")

    @pytest.mark.asyncio
    async def test_redis_hash_operations(self, redis_client):
        """测试Redis哈希操作"""
        hash_key = "test_hash"
        
        # 设置哈希字段
        await redis_client.hset(hash_key, "field1", "value1")
        await redis_client.hset(hash_key, "field2", "value2")
        
        # 获取哈希字段
        value1 = await redis_client.hget(hash_key, "field1")
        value2 = await redis_client.hget(hash_key, "field2")
        
        assert value1 == "value1"
        assert value2 == "value2"
        
        # 获取所有哈希字段
        all_fields = await redis_client.hgetall(hash_key)
        assert all_fields == {"field1": "value1", "field2": "value2"}
        
        # 清理
        await redis_client.delete(hash_key)

    @pytest.mark.asyncio
    async def test_redis_list_operations(self, redis_client):
        """测试Redis列表操作"""
        list_key = "test_list"
        
        # 推入列表
        await redis_client.lpush(list_key, "item1", "item2", "item3")
        
        # 获取列表长度
        length = await redis_client.llen(list_key)
        assert length == 3
        
        # 获取列表范围
        items = await redis_client.lrange(list_key, 0, -1)
        assert "item3" in items  # lpush逆序插入
        assert "item2" in items
        assert "item1" in items
        
        # 清理
        await redis_client.delete(list_key)

    @pytest.mark.asyncio
    async def test_redis_set_operations(self, redis_client):
        """测试Redis集合操作"""
        set_key = "test_set"
        
        # 添加集合成员
        await redis_client.sadd(set_key, "member1", "member2", "member3")
        
        # 检查成员数量
        count = await redis_client.scard(set_key)
        assert count == 3
        
        # 检查成员存在性
        is_member = await redis_client.sismember(set_key, "member1")
        assert is_member is True
        
        is_not_member = await redis_client.sismember(set_key, "nonexistent")
        assert is_not_member is False
        
        # 获取所有成员
        members = await redis_client.smembers(set_key)
        assert len(members) == 3
        assert "member1" in members
        assert "member2" in members
        assert "member3" in members
        
        # 清理
        await redis_client.delete(set_key)

    @pytest.mark.asyncio
    async def test_redis_incr_operations(self, redis_client):
        """测试Redis计数器操作"""
        counter_key = "test_counter"
        
        # 增加计数器
        count1 = await redis_client.incr(counter_key)
        assert count1 == 1
        
        count2 = await redis_client.incr(counter_key)
        assert count2 == 2
        
        # 按指定值增加
        count3 = await redis_client.incrby(counter_key, 5)
        assert count3 == 7
        
        # 减少计数器
        count4 = await redis_client.decr(counter_key)
        assert count4 == 6
        
        # 清理
        await redis_client.delete(counter_key)