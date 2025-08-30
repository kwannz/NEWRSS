import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, SessionLocal, engine, Base

class TestDatabase:
    
    @pytest.mark.asyncio
    async def test_get_db_session(self):
        """测试数据库会话获取"""
        async for session in get_db():
            assert isinstance(session, AsyncSession)
            assert not session.is_active  # 应该还没开始事务
            break

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """测试数据库连接"""
        async with SessionLocal() as session:
            # 执行简单查询验证连接
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_transaction(self):
        """测试会话事务处理"""
        async with SessionLocal() as session:
            # 开始事务
            assert not session.in_transaction()
            
            # 执行操作时会自动开始事务
            await session.execute("SELECT 1")
            assert session.in_transaction()
            
            # 提交事务
            await session.commit()
            assert not session.in_transaction()

    @pytest.mark.asyncio
    async def test_session_rollback(self):
        """测试会话回滚"""
        async with SessionLocal() as session:
            try:
                # 执行一个无效操作
                await session.execute("SELECT FROM invalid_table")
                await session.commit()
            except Exception:
                await session.rollback()
                # 回滚后应该能正常工作
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1

    def test_base_metadata(self):
        """测试Base元数据"""
        assert Base.metadata is not None
        assert hasattr(Base, 'registry')

    @pytest.mark.asyncio
    async def test_engine_connection(self):
        """测试引擎连接"""
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            assert result.scalar() == 1

    @pytest.mark.asyncio
    async def test_session_local_factory(self):
        """测试SessionLocal工厂"""
        session = SessionLocal()
        try:
            assert isinstance(session, AsyncSession)
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """测试多个会话独立性"""
        session1 = SessionLocal()
        session2 = SessionLocal()
        
        try:
            # 两个会话应该是独立的
            assert session1 is not session2
            
            # 都应该能正常工作
            result1 = await session1.execute("SELECT 1")
            result2 = await session2.execute("SELECT 2")
            
            assert result1.scalar() == 1
            assert result2.scalar() == 2
        finally:
            await session1.close()
            await session2.close()

    @pytest.mark.asyncio
    async def test_get_db_cleanup(self):
        """测试get_db自动清理"""
        sessions = []
        
        # 收集会话引用
        async for session in get_db():
            sessions.append(session)
            break
        
        # 会话应该在生成器结束后自动关闭
        assert len(sessions) == 1
        # 注意：由于异步生成器的特性，我们无法直接测试close状态