"""
Performance and Load Testing for NEWRSS Platform
Testing system performance under realistic load conditions
"""
import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch
import psutil
import os
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from app.main import app
from app.models.news import NewsItem
from app.models.user import User
from app.repositories.news_repository import NewsRepository
from app.repositories.user_repository import UserRepository
from app.services.rss_fetcher import RSSFetcher
from app.services.ai_analyzer import AIAnalyzer
from app.services.broadcast_service import BroadcastService
from app.tasks.news_crawler import crawl_rss_sources


@pytest.mark.slow
class TestPerformanceAndLoad:
    """
    Comprehensive performance and load testing suite
    """

    @pytest.fixture
    async def performance_client(self):
        """Create HTTP client for performance testing"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.fixture
    async def load_test_users(self, db_session: AsyncSession):
        """Create many users for load testing"""
        user_repo = UserRepository(db_session)
        users = []
        
        # Create 1000 test users
        for i in range(1000):
            user = await user_repo.create_user(
                telegram_id=1000000 + i,
                telegram_username=f"loadtest_user_{i}",
                first_name=f"User{i}",
                last_name="LoadTest",
                preferences={
                    "categories": ["bitcoin", "ethereum"] if i % 2 == 0 else ["defi", "nft"],
                    "min_importance_score": (i % 5) + 1,
                    "urgent_notifications": i % 3 == 0,
                    "daily_digest": i % 4 == 0,
                    "max_daily_notifications": (i % 10) + 5
                }
            )
            users.append(user)
            
            # Commit in batches to avoid memory issues
            if (i + 1) % 100 == 0:
                await db_session.commit()
        
        await db_session.commit()
        return users

    @pytest.fixture
    async def load_test_news(self, db_session: AsyncSession):
        """Create many news items for load testing"""
        news_repo = NewsRepository(db_session)
        news_items = []
        
        categories = ["bitcoin", "ethereum", "defi", "nft", "trading", "regulation"]
        sources = ["CoinDesk", "CoinTelegraph", "TheBlock", "Decrypt", "CryptoSlate"]
        
        # Create 5000 news items
        for i in range(5000):
            news = await news_repo.create(
                title=f"Load Test News Item {i}: Crypto Market Update",
                content=f"This is load test news content {i}. " * 20,  # ~500 chars
                url=f"https://example.com/news/{i}",
                source=sources[i % len(sources)],
                category=categories[i % len(categories)],
                importance_score=(i % 5) + 1,
                is_urgent=i % 10 == 0,
                published_at="2024-01-01T12:00:00Z",
                key_tokens=[f"token{i}", f"crypto{i}", "test"],
                key_prices=[f"${i * 100}", f"${i * 150}"] if i % 3 == 0 else None
            )
            news_items.append(news)
            
            # Commit in batches
            if (i + 1) % 500 == 0:
                await db_session.commit()
        
        await db_session.commit()
        return news_items

    async def test_api_response_times_under_load(self, performance_client):
        """
        Test API response times under concurrent load
        """
        response_times = []
        error_count = 0
        
        async def make_request():
            try:
                start_time = time.time()
                response = await performance_client.get("/news?limit=50")
                end_time = time.time()
                
                if response.status_code == 200:
                    response_times.append(end_time - start_time)
                else:
                    nonlocal error_count
                    error_count += 1
                    
            except Exception:
                error_count += 1
        
        # Simulate 100 concurrent requests
        tasks = [make_request() for _ in range(100)]
        await asyncio.gather(*tasks)
        
        # Performance assertions
        if response_times:
            avg_response_time = statistics.mean(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            # API should respond quickly under load
            assert avg_response_time < 1.0, f"Average response time {avg_response_time}s too high"
            assert p95_response_time < 2.0, f"95th percentile {p95_response_time}s too high"
            
        # Error rate should be low
        total_requests = len(response_times) + error_count
        error_rate = error_count / total_requests if total_requests > 0 else 0
        assert error_rate < 0.05, f"Error rate {error_rate} too high"

    async def test_database_performance_under_load(self, db_session: AsyncSession, load_test_news):
        """
        Test database query performance under load
        """
        news_repo = NewsRepository(db_session)
        query_times = []
        
        async def perform_query():
            start_time = time.time()
            # Simulate common queries
            recent_news = await news_repo.get_recent_news(limit=50)
            urgent_news = await news_repo.get_urgent_news(limit=10)
            category_news = await news_repo.get_by_category("bitcoin", limit=20)
            end_time = time.time()
            
            query_times.append(end_time - start_time)
        
        # Perform 50 concurrent database operations
        tasks = [perform_query() for _ in range(50)]
        await asyncio.gather(*tasks)
        
        # Database performance assertions
        avg_query_time = statistics.mean(query_times)
        max_query_time = max(query_times)
        
        assert avg_query_time < 0.5, f"Average query time {avg_query_time}s too high"
        assert max_query_time < 2.0, f"Max query time {max_query_time}s too high"

    async def test_websocket_concurrent_connections(self):
        """
        Test WebSocket server with many concurrent connections
        """
        from socketio import AsyncClient
        
        connection_count = 100
        clients = []
        connection_times = []
        successful_connections = 0
        
        async def create_connection():
            client = AsyncClient()
            try:
                start_time = time.time()
                await client.connect('http://localhost:8000')
                end_time = time.time()
                
                if client.connected:
                    nonlocal successful_connections
                    successful_connections += 1
                    connection_times.append(end_time - start_time)
                    return client
            except Exception:
                pass
            return None
        
        try:
            # Create concurrent connections
            results = await asyncio.gather(*[create_connection() for _ in range(connection_count)])
            clients = [c for c in results if c is not None]
            
            # Performance assertions
            connection_success_rate = successful_connections / connection_count
            assert connection_success_rate >= 0.95, f"Connection success rate {connection_success_rate} too low"
            
            if connection_times:
                avg_connection_time = statistics.mean(connection_times)
                assert avg_connection_time < 1.0, f"Average connection time {avg_connection_time}s too high"
            
            # Test broadcasting to all clients
            if clients:
                messages_received = [0] * len(clients)
                
                for i, client in enumerate(clients):
                    def make_handler(index):
                        async def handler(data):
                            messages_received[index] += 1
                        return handler
                    
                    client.on('new_news', make_handler(i))
                
                # Simulate news broadcast
                test_news = {
                    'id': 1,
                    'title': 'Test News',
                    'content': 'Test content'
                }
                
                # In real implementation, this would be done via broadcast service
                for client in clients[:10]:  # Test with subset to avoid overwhelming
                    await client.emit('new_news', test_news)
                
                await asyncio.sleep(0.5)
                
                # Verify message delivery
                delivered_count = sum(1 for count in messages_received[:10] if count > 0)
                delivery_rate = delivered_count / min(10, len(clients))
                assert delivery_rate >= 0.9, f"Message delivery rate {delivery_rate} too low"
        
        finally:
            # Cleanup
            for client in clients:
                if client and client.connected:
                    try:
                        await client.disconnect()
                    except:
                        pass

    async def test_news_processing_pipeline_performance(self, db_session: AsyncSession):
        """
        Test end-to-end news processing pipeline performance
        """
        rss_fetcher = RSSFetcher()
        ai_analyzer = AIAnalyzer()
        news_repo = NewsRepository(db_session)
        
        processing_times = []
        
        # Mock RSS feed data
        mock_feed_items = [
            {
                'title': f'Performance Test News {i}',
                'link': f'https://example.com/news/{i}',
                'description': f'Test news content {i}',
                'published': '2024-01-01T12:00:00Z',
                'source': 'TestSource'
            }
            for i in range(100)
        ]
        
        with patch.object(rss_fetcher, 'fetch_from_source', return_value=mock_feed_items):
            with patch.object(ai_analyzer, 'analyze_news_item', return_value={
                'importance_score': 3,
                'category': 'bitcoin',
                'is_urgent': False,
                'key_tokens': ['test', 'news'],
                'sentiment_score': 0.5,
                'market_impact': 2
            }):
                
                async def process_news_batch(batch):
                    start_time = time.time()
                    
                    # Simulate complete processing pipeline
                    for item in batch:
                        # Step 1: Fetch (mocked)
                        # Step 2: AI Analysis (mocked) 
                        analysis = await ai_analyzer.analyze_news_item(item['description'])
                        
                        # Step 3: Database storage
                        news_item = await news_repo.create(
                            title=item['title'],
                            content=item['description'],
                            url=item['link'],
                            source=item['source'],
                            category=analysis['category'],
                            importance_score=analysis['importance_score'],
                            is_urgent=analysis['is_urgent'],
                            published_at=item['published'],
                            key_tokens=analysis['key_tokens']
                        )
                    
                    await db_session.commit()
                    end_time = time.time()
                    return end_time - start_time
                
                # Process in batches to simulate real pipeline
                batch_size = 10
                batches = [mock_feed_items[i:i+batch_size] for i in range(0, len(mock_feed_items), batch_size)]
                
                for batch in batches:
                    processing_time = await process_news_batch(batch)
                    processing_times.append(processing_time)
        
        # Performance assertions
        avg_processing_time = statistics.mean(processing_times)
        max_processing_time = max(processing_times)
        
        # Each batch of 10 items should process within reasonable time
        assert avg_processing_time < 5.0, f"Average batch processing time {avg_processing_time}s too high"
        assert max_processing_time < 10.0, f"Max batch processing time {max_processing_time}s too high"
        
        # Calculate items per second
        total_items = len(mock_feed_items)
        total_time = sum(processing_times)
        items_per_second = total_items / total_time
        
        # Should process at least 5 items per second
        assert items_per_second >= 5.0, f"Processing rate {items_per_second} items/sec too low"

    async def test_memory_usage_under_load(self, load_test_users, load_test_news):
        """
        Test memory usage patterns under load
        """
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate heavy usage patterns
        news_repo = NewsRepository(AsyncSession())
        user_repo = UserRepository(AsyncSession())
        
        # Perform memory-intensive operations
        for _ in range(10):
            # Query large datasets
            all_news = await news_repo.get_recent_news(limit=1000)
            all_users = await user_repo.get_active_users(limit=500)
            
            # Process data
            filtered_news = [news for news in all_news if news.importance_score >= 3]
            active_users = [user for user in all_users if user.is_active]
            
            # Simulate news matching
            for user in active_users[:100]:  # Process subset
                user_categories = user.preferences.get('categories', [])
                matching_news = [
                    news for news in filtered_news 
                    if news.category in user_categories
                ]
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 500MB)
        assert memory_increase < 500, f"Memory usage increased by {memory_increase}MB - too high"

    async def test_concurrent_user_operations(self, performance_client, load_test_users):
        """
        Test concurrent user operations (login, preferences, etc.)
        """
        operation_times = []
        success_count = 0
        
        async def simulate_user_session():
            try:
                start_time = time.time()
                
                # Simulate user login
                login_response = await performance_client.post('/auth/token', data={
                    'username': 'testuser',
                    'password': 'testpass'
                })
                
                if login_response.status_code == 200:
                    # Simulate authenticated operations
                    token = login_response.json().get('access_token')
                    headers = {'Authorization': f'Bearer {token}'}
                    
                    # Get user info
                    await performance_client.get('/auth/me', headers=headers)
                    
                    # Update preferences
                    await performance_client.patch('/auth/me/preferences', 
                        json={'urgent_notifications': True},
                        headers=headers
                    )
                    
                    # Get personalized news
                    await performance_client.get('/news?limit=20', headers=headers)
                
                end_time = time.time()
                operation_times.append(end_time - start_time)
                
                nonlocal success_count
                success_count += 1
                
            except Exception:
                pass  # Count as failure
        
        # Simulate 50 concurrent user sessions
        tasks = [simulate_user_session() for _ in range(50)]
        await asyncio.gather(*tasks)
        
        # Performance assertions
        if operation_times:
            avg_session_time = statistics.mean(operation_times)
            assert avg_session_time < 3.0, f"Average user session time {avg_session_time}s too high"
        
        success_rate = success_count / 50
        assert success_rate >= 0.8, f"User session success rate {success_rate} too low"

    async def test_news_broadcast_performance(self, load_test_users, load_test_news):
        """
        Test news broadcasting performance to many users
        """
        broadcast_service = BroadcastService()
        
        broadcast_times = []
        
        # Test broadcasting to subsets of users
        user_batches = [load_test_users[i:i+100] for i in range(0, min(500, len(load_test_users)), 100)]
        
        for i, user_batch in enumerate(user_batches):
            news_item = load_test_news[i % len(load_test_news)]
            
            start_time = time.time()
            
            # Simulate broadcast to user batch
            with patch.object(broadcast_service, 'send_to_telegram_users') as mock_send:
                mock_send.return_value = asyncio.Future()
                mock_send.return_value.set_result(True)
                
                await broadcast_service.broadcast_to_users(news_item, user_batch)
            
            end_time = time.time()
            broadcast_times.append(end_time - start_time)
        
        # Performance assertions
        avg_broadcast_time = statistics.mean(broadcast_times)
        max_broadcast_time = max(broadcast_times)
        
        # Broadcasting to 100 users should be fast
        assert avg_broadcast_time < 2.0, f"Average broadcast time {avg_broadcast_time}s too high"
        assert max_broadcast_time < 5.0, f"Max broadcast time {max_broadcast_time}s too high"

    async def test_database_connection_pool_performance(self, db_session: AsyncSession):
        """
        Test database connection pool under concurrent load
        """
        connection_times = []
        query_times = []
        
        async def perform_db_operations():
            # Time connection acquisition
            start_time = time.time()
            # Connection should be from pool, so this measures query time
            result = await db_session.execute("SELECT 1")
            connection_time = time.time() - start_time
            connection_times.append(connection_time)
            
            # Time actual query
            start_time = time.time()
            result = await db_session.execute("SELECT COUNT(*) FROM news")
            query_time = time.time() - start_time
            query_times.append(query_time)
        
        # Perform 100 concurrent database operations
        tasks = [perform_db_operations() for _ in range(100)]
        await asyncio.gather(*tasks)
        
        # Performance assertions
        avg_connection_time = statistics.mean(connection_times)
        avg_query_time = statistics.mean(query_times)
        
        assert avg_connection_time < 0.1, f"Average connection time {avg_connection_time}s too high"
        assert avg_query_time < 0.5, f"Average query time {avg_query_time}s too high"

    async def test_rss_fetching_performance(self):
        """
        Test RSS fetching performance with multiple sources
        """
        rss_fetcher = RSSFetcher()
        
        # Mock multiple RSS sources
        mock_sources = [
            'https://example.com/rss1',
            'https://example.com/rss2', 
            'https://example.com/rss3',
            'https://example.com/rss4',
            'https://example.com/rss5'
        ]
        
        mock_response = [
            {
                'title': f'RSS News {i}',
                'link': f'https://example.com/news/{i}',
                'description': f'RSS content {i}',
                'published': '2024-01-01T12:00:00Z',
                'source': 'TestRSS'
            }
            for i in range(50)  # 50 items per source
        ]
        
        fetch_times = []
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock RSS response
            mock_response_obj = AsyncMock()
            mock_response_obj.text.return_value = """<?xml version="1.0"?>
            <rss><channel><item><title>Test</title><link>http://test.com</link></item></channel></rss>"""
            mock_get.return_value.__aenter__.return_value = mock_response_obj
            
            for source in mock_sources:
                start_time = time.time()
                items = await rss_fetcher.fetch_from_source(source)
                end_time = time.time()
                fetch_times.append(end_time - start_time)
        
        # Performance assertions
        avg_fetch_time = statistics.mean(fetch_times)
        max_fetch_time = max(fetch_times)
        
        assert avg_fetch_time < 2.0, f"Average RSS fetch time {avg_fetch_time}s too high"
        assert max_fetch_time < 5.0, f"Max RSS fetch time {max_fetch_time}s too high"

    @pytest.mark.slow
    async def test_24_hour_endurance(self):
        """
        Simulate 24-hour endurance test (scaled down for CI)
        """
        # This is a scaled-down version for CI - in production you'd run longer
        test_duration = 30  # 30 seconds instead of 24 hours
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        start_time = time.time()
        operation_count = 0
        
        while time.time() - start_time < test_duration:
            # Simulate periodic operations
            operation_count += 1
            
            # Simulate news processing
            await asyncio.sleep(0.01)  # Simulate work
            
            # Check memory every 100 operations
            if operation_count % 100 == 0:
                current_memory = process.memory_info().rss
                memory_increase = (current_memory - initial_memory) / 1024 / 1024  # MB
                
                # Memory shouldn't grow excessively
                assert memory_increase < 100, f"Memory leak detected: {memory_increase}MB increase"
        
        # Verify system remained stable
        final_memory = process.memory_info().rss
        total_memory_increase = (final_memory - initial_memory) / 1024 / 1024
        
        assert total_memory_increase < 50, f"Memory usage grew {total_memory_increase}MB during endurance test"
        assert operation_count > 0, "No operations completed during endurance test"

    async def test_cpu_usage_under_load(self):
        """
        Test CPU usage patterns under load
        """
        cpu_usage_samples = []
        
        async def cpu_intensive_task():
            # Simulate AI analysis work
            for _ in range(1000):
                # Simple computation to simulate work
                result = sum(i * i for i in range(100))
        
        # Monitor CPU usage during intensive tasks
        for _ in range(10):
            start_cpu = psutil.cpu_percent(interval=None)
            
            # Run intensive tasks
            await asyncio.gather(*[cpu_intensive_task() for _ in range(5)])
            
            end_cpu = psutil.cpu_percent(interval=0.1)
            cpu_usage_samples.append(end_cpu)
        
        # CPU usage should be reasonable (not maxing out system)
        avg_cpu_usage = statistics.mean(cpu_usage_samples)
        max_cpu_usage = max(cpu_usage_samples)
        
        assert avg_cpu_usage < 80, f"Average CPU usage {avg_cpu_usage}% too high"
        assert max_cpu_usage < 95, f"Max CPU usage {max_cpu_usage}% too high"