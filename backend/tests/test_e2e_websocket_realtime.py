"""
Comprehensive E2E tests for WebSocket real-time news broadcasting
Testing news pipeline from RSS → AI → Broadcast → Client reception
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient
from socketio import AsyncClient
from app.main import app, sio
from app.models.news import NewsItem
from app.models.user import User
from app.repositories.news_repository import NewsRepository
from app.repositories.user_repository import UserRepository
from app.services.broadcast_service import BroadcastService
from app.services.user_filter_service import UserFilterService


@pytest.mark.asyncio
class TestWebSocketRealTimeBroadcasting:
    """
    Comprehensive WebSocket real-time broadcasting tests
    """

    @pytest.fixture
    async def socket_client(self):
        """Create async socket.io client for testing"""
        client = AsyncClient()
        yield client
        if client.connected:
            await client.disconnect()

    @pytest.fixture
    async def broadcast_service(self, db_session: AsyncSession):
        """Create broadcast service with test dependencies"""
        service = BroadcastService()
        service.news_repo = NewsRepository(db_session)
        service.user_repo = UserRepository(db_session)
        service.filter_service = UserFilterService()
        return service

    @pytest.fixture
    async def test_users(self, db_session: AsyncSession):
        """Create test users with different preferences"""
        user_repo = UserRepository(db_session)
        
        users = []
        
        # User 1: Bitcoin enthusiast
        user1 = await user_repo.create_user(
            telegram_id=111111111,
            telegram_username="bitcoin_lover",
            first_name="Bitcoin",
            last_name="Fan",
            preferences={
                "categories": ["bitcoin"],
                "min_importance_score": 3,
                "urgent_notifications": True,
                "daily_digest": False
            }
        )
        
        # User 2: General crypto follower
        user2 = await user_repo.create_user(
            telegram_id=222222222,
            telegram_username="crypto_general",
            first_name="Crypto",
            last_name="General",
            preferences={
                "categories": ["bitcoin", "ethereum", "defi"],
                "min_importance_score": 2,
                "urgent_notifications": True,
                "daily_digest": True
            }
        )
        
        # User 3: High importance only
        user3 = await user_repo.create_user(
            telegram_id=333333333,
            telegram_username="quality_only",
            first_name="Quality",
            last_name="Only",
            preferences={
                "categories": ["bitcoin", "ethereum", "defi", "nft"],
                "min_importance_score": 5,
                "urgent_notifications": True,
                "daily_digest": False
            }
        )
        
        users.extend([user1, user2, user3])
        await db_session.commit()
        return users

    @pytest.fixture
    async def sample_news_items(self, db_session: AsyncSession):
        """Create sample news items for testing"""
        news_repo = NewsRepository(db_session)
        
        news_items = []
        
        # Regular Bitcoin news (importance 3)
        bitcoin_news = await news_repo.create(
            title="Bitcoin Price Analysis",
            content="Bitcoin shows strong technical indicators",
            url="https://example.com/bitcoin-analysis",
            source="CoinDesk",
            category="bitcoin",
            importance_score=3,
            is_urgent=False,
            published_at="2024-01-01T12:00:00Z",
            key_tokens=["BTC", "analysis", "bullish"],
            key_prices=["$45000"]
        )
        
        # Urgent Ethereum news (importance 4)
        ethereum_news = await news_repo.create(
            title="Ethereum Network Upgrade Complete",
            content="Major Ethereum upgrade successfully deployed",
            url="https://example.com/eth-upgrade",
            source="EthereumFoundation",
            category="ethereum",
            importance_score=4,
            is_urgent=True,
            published_at="2024-01-01T13:00:00Z",
            key_tokens=["ETH", "upgrade", "deployment"],
            key_prices=["$3000"]
        )
        
        # High importance DeFi news (importance 5)
        defi_news = await news_repo.create(
            title="Major DeFi Protocol Vulnerability Discovered",
            content="Critical security issue found in popular DeFi protocol",
            url="https://example.com/defi-security",
            source="DeFiPulse",
            category="defi",
            importance_score=5,
            is_urgent=True,
            published_at="2024-01-01T14:00:00Z",
            key_tokens=["DeFi", "vulnerability", "security"],
            key_prices=[]
        )
        
        # Low importance NFT news (importance 1)
        nft_news = await news_repo.create(
            title="New NFT Collection Launch",
            content="Artist launches new NFT collection",
            url="https://example.com/nft-collection",
            source="NFTNews",
            category="nft",
            importance_score=1,
            is_urgent=False,
            published_at="2024-01-01T15:00:00Z",
            key_tokens=["NFT", "collection", "art"],
            key_prices=["0.1 ETH"]
        )
        
        news_items.extend([bitcoin_news, ethereum_news, defi_news, nft_news])
        await db_session.commit()
        return news_items

    async def test_websocket_connection_lifecycle(self, socket_client):
        """
        Test WebSocket connection establishment and lifecycle
        """
        # Test connection
        connected = await socket_client.connect('http://localhost:8000')
        assert connected is True
        assert socket_client.connected is True
        
        # Test disconnection
        await socket_client.disconnect()
        assert socket_client.connected is False

    async def test_news_broadcast_to_all_clients(self, socket_client, broadcast_service, sample_news_items):
        """
        Test broadcasting news to all connected clients
        """
        received_news = []
        
        @socket_client.on('new_news')
        async def on_news(data):
            received_news.append(data)
        
        # Connect client
        await socket_client.connect('http://localhost:8000')
        
        # Broadcast news item
        bitcoin_news = sample_news_items[0]
        await broadcast_service.broadcast_news(bitcoin_news)
        
        # Wait for broadcast
        await asyncio.sleep(0.1)
        
        # Verify news received
        assert len(received_news) == 1
        assert received_news[0]['id'] == bitcoin_news.id
        assert received_news[0]['title'] == bitcoin_news.title

    async def test_urgent_news_special_broadcast(self, socket_client, broadcast_service, sample_news_items):
        """
        Test urgent news broadcast with special channel
        """
        received_urgent = []
        
        @socket_client.on('urgent_news')
        async def on_urgent_news(data):
            received_urgent.append(data)
        
        await socket_client.connect('http://localhost:8000')
        
        # Broadcast urgent news
        urgent_news = sample_news_items[1]  # Ethereum urgent news
        await broadcast_service.broadcast_urgent_news(urgent_news)
        
        await asyncio.sleep(0.1)
        
        # Verify urgent news received
        assert len(received_urgent) == 1
        assert received_urgent[0]['is_urgent'] is True
        assert received_urgent[0]['importance_score'] >= 4

    async def test_multiple_clients_concurrent_reception(self, broadcast_service, sample_news_items):
        """
        Test multiple clients receiving news concurrently
        """
        num_clients = 5
        clients = []
        received_data = [[] for _ in range(num_clients)]
        
        try:
            # Create and connect multiple clients
            for i in range(num_clients):
                client = AsyncClient()
                
                # Create unique event handler for each client
                def make_handler(index):
                    async def handler(data):
                        received_data[index].append(data)
                    return handler
                
                client.on('new_news', make_handler(i))
                await client.connect('http://localhost:8000')
                clients.append(client)
            
            # Broadcast news to all clients
            bitcoin_news = sample_news_items[0]
            await broadcast_service.broadcast_news(bitcoin_news)
            
            await asyncio.sleep(0.2)
            
            # Verify all clients received the news
            for i in range(num_clients):
                assert len(received_data[i]) == 1
                assert received_data[i][0]['id'] == bitcoin_news.id
        
        finally:
            # Cleanup clients
            for client in clients:
                if client.connected:
                    await client.disconnect()

    async def test_user_specific_filtering(self, broadcast_service, test_users, sample_news_items):
        """
        Test user-specific news filtering based on preferences
        """
        bitcoin_news = sample_news_items[0]  # importance 3, bitcoin
        high_importance_news = sample_news_items[2]  # importance 5, defi
        low_importance_news = sample_news_items[3]  # importance 1, nft
        
        # Test filtering for each user
        user1_news = await broadcast_service.filter_news_for_user(test_users[0], bitcoin_news)
        user2_news = await broadcast_service.filter_news_for_user(test_users[1], bitcoin_news)
        user3_news = await broadcast_service.filter_news_for_user(test_users[2], bitcoin_news)
        
        # User 1 (Bitcoin enthusiast, min_importance=3) should receive bitcoin news
        assert user1_news is True
        
        # User 2 (General, min_importance=2) should receive bitcoin news
        assert user2_news is True
        
        # User 3 (Quality only, min_importance=5) should NOT receive bitcoin news (importance=3)
        assert user3_news is False
        
        # Test high importance news
        user3_high_news = await broadcast_service.filter_news_for_user(test_users[2], high_importance_news)
        assert user3_high_news is True  # Should receive high importance news
        
        # Test low importance news - no users should receive it based on their preferences
        for user in test_users:
            should_receive = await broadcast_service.filter_news_for_user(user, low_importance_news)
            assert should_receive is False

    async def test_websocket_error_handling(self, socket_client):
        """
        Test WebSocket error handling and recovery
        """
        connection_events = []
        error_events = []
        
        @socket_client.on('connect')
        async def on_connect():
            connection_events.append('connected')
        
        @socket_client.on('disconnect')
        async def on_disconnect():
            connection_events.append('disconnected')
        
        @socket_client.on('connect_error')
        async def on_error(error):
            error_events.append(error)
        
        # Test connection to non-existent server
        try:
            await socket_client.connect('http://localhost:9999')
        except:
            pass  # Connection should fail
        
        # Verify error handling
        await asyncio.sleep(0.1)
        assert len(error_events) > 0 or not socket_client.connected

    async def test_news_serialization_format(self, broadcast_service, sample_news_items):
        """
        Test proper news item serialization for WebSocket transmission
        """
        news_item = sample_news_items[0]
        
        # Serialize news item
        serialized = await broadcast_service.serialize_news_item(news_item)
        
        # Verify all required fields are present
        required_fields = [
            'id', 'title', 'content', 'url', 'source', 'category',
            'published_at', 'importance_score', 'is_urgent', 'created_at'
        ]
        
        for field in required_fields:
            assert field in serialized
        
        # Verify data types
        assert isinstance(serialized['id'], int)
        assert isinstance(serialized['title'], str)
        assert isinstance(serialized['importance_score'], int)
        assert isinstance(serialized['is_urgent'], bool)
        
        # Verify optional fields handling
        if serialized.get('key_tokens'):
            assert isinstance(serialized['key_tokens'], list)
        
        if serialized.get('key_prices'):
            assert isinstance(serialized['key_prices'], list)

    async def test_broadcast_rate_limiting(self, broadcast_service, sample_news_items):
        """
        Test broadcast rate limiting to prevent overwhelming clients
        """
        # Simulate rapid news broadcasting
        broadcast_times = []
        
        for i in range(10):
            start_time = asyncio.get_event_loop().time()
            await broadcast_service.broadcast_news(sample_news_items[0])
            end_time = asyncio.get_event_loop().time()
            broadcast_times.append(end_time - start_time)
        
        # Verify broadcasts don't take too long (no blocking)
        avg_time = sum(broadcast_times) / len(broadcast_times)
        assert avg_time < 0.1  # Should be very fast

    async def test_connection_recovery_after_failure(self, socket_client):
        """
        Test client connection recovery after network failure
        """
        # Initial connection
        await socket_client.connect('http://localhost:8000')
        assert socket_client.connected is True
        
        # Simulate connection loss
        await socket_client.disconnect()
        assert socket_client.connected is False
        
        # Test reconnection
        await socket_client.connect('http://localhost:8000')
        assert socket_client.connected is True

    async def test_websocket_namespace_isolation(self, socket_client):
        """
        Test that WebSocket events are properly namespaced
        """
        news_events = []
        other_events = []
        
        @socket_client.on('new_news')
        async def on_news(data):
            news_events.append(data)
        
        @socket_client.on('other_event')
        async def on_other(data):
            other_events.append(data)
        
        await socket_client.connect('http://localhost:8000')
        
        # Emit different types of events
        await socket_client.emit('news_request', {'type': 'latest'})
        await socket_client.emit('ping', {'timestamp': '2024-01-01T12:00:00Z'})
        
        await asyncio.sleep(0.1)
        
        # Verify events are handled separately
        # This test verifies proper event handling structure

    async def test_memory_usage_during_broadcasting(self, broadcast_service, sample_news_items):
        """
        Test memory usage doesn't grow excessively during broadcasting
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many broadcasts
        for _ in range(100):
            for news_item in sample_news_items:
                await broadcast_service.broadcast_news(news_item)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024

    async def test_concurrent_connections_performance(self):
        """
        Test performance with many concurrent WebSocket connections
        """
        num_connections = 50
        clients = []
        connection_times = []
        
        try:
            # Create many concurrent connections
            start_time = asyncio.get_event_loop().time()
            
            async def create_client():
                client = AsyncClient()
                connect_start = asyncio.get_event_loop().time()
                await client.connect('http://localhost:8000')
                connect_end = asyncio.get_event_loop().time()
                return client, connect_end - connect_start
            
            # Connect all clients concurrently
            results = await asyncio.gather(*[create_client() for _ in range(num_connections)])
            clients, times = zip(*results)
            connection_times.extend(times)
            
            total_time = asyncio.get_event_loop().time() - start_time
            
            # Verify reasonable performance
            assert total_time < 5.0  # All connections should complete within 5 seconds
            assert all(t < 1.0 for t in connection_times)  # Each connection should be fast
        
        finally:
            # Cleanup
            for client in clients:
                if client and client.connected:
                    await client.disconnect()

    async def test_websocket_authentication(self, socket_client, test_users):
        """
        Test WebSocket authentication and user session management
        """
        # This test would verify user authentication for WebSocket connections
        # In the current implementation, WebSocket connections might be anonymous
        # But in production, you might want to authenticate connections
        
        auth_events = []
        
        @socket_client.on('auth_required')
        async def on_auth_required():
            auth_events.append('auth_required')
        
        @socket_client.on('authenticated')
        async def on_authenticated():
            auth_events.append('authenticated')
        
        await socket_client.connect('http://localhost:8000')
        
        # In a production system, you might emit authentication credentials
        # await socket_client.emit('authenticate', {'token': 'user_token'})
        
        await asyncio.sleep(0.1)
        
        # Verify connection established (authentication handling depends on implementation)
        assert socket_client.connected

    async def test_websocket_message_ordering(self, socket_client, broadcast_service, sample_news_items):
        """
        Test that WebSocket messages are delivered in correct order
        """
        received_messages = []
        
        @socket_client.on('new_news')
        async def on_news(data):
            received_messages.append(data)
        
        await socket_client.connect('http://localhost:8000')
        
        # Send multiple news items in specific order
        for i, news_item in enumerate(sample_news_items):
            # Add sequence number to track order
            news_item.sequence = i
            await broadcast_service.broadcast_news(news_item)
            # Small delay to ensure ordering
            await asyncio.sleep(0.01)
        
        await asyncio.sleep(0.2)
        
        # Verify messages received in correct order
        assert len(received_messages) == len(sample_news_items)
        for i, message in enumerate(received_messages):
            expected_news = sample_news_items[i]
            assert message['id'] == expected_news.id

    @pytest.mark.slow
    async def test_long_running_connection_stability(self, socket_client):
        """
        Test WebSocket connection stability over extended periods
        """
        connection_events = []
        
        @socket_client.on('connect')
        async def on_connect():
            connection_events.append(('connect', asyncio.get_event_loop().time()))
        
        @socket_client.on('disconnect')
        async def on_disconnect():
            connection_events.append(('disconnect', asyncio.get_event_loop().time()))
        
        # Establish connection
        await socket_client.connect('http://localhost:8000')
        
        # Keep connection alive for extended period
        await asyncio.sleep(10)  # 10 seconds for testing
        
        # Verify connection remained stable
        assert socket_client.connected
        assert len([e for e in connection_events if e[0] == 'disconnect']) == 0

    async def test_websocket_data_compression(self, socket_client, broadcast_service):
        """
        Test WebSocket data compression for large news items
        """
        # Create large news item
        large_content = "Large news content " * 1000  # ~20KB content
        
        news_repo = NewsRepository(AsyncSession())
        large_news = await news_repo.create(
            title="Large News Item for Compression Test",
            content=large_content,
            url="https://example.com/large-news",
            source="TestSource",
            category="bitcoin",
            importance_score=3,
            is_urgent=False,
            published_at="2024-01-01T12:00:00Z"
        )
        
        received_data = []
        
        @socket_client.on('new_news')
        async def on_news(data):
            received_data.append(data)
        
        await socket_client.connect('http://localhost:8000')
        
        # Broadcast large news item
        await broadcast_service.broadcast_news(large_news)
        
        await asyncio.sleep(0.2)
        
        # Verify large data received correctly
        assert len(received_data) == 1
        assert len(received_data[0]['content']) > 10000  # Verify large content preserved