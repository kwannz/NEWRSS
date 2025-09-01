import asyncio
from celery import Celery
from typing import Dict
from datetime import datetime
from sqlalchemy import select
from app.services.rss_fetcher import RSSFetcher
from app.core.settings import settings
from app.core.logging import get_task_logger

celery_app = Celery(
    'newrss',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'crawl-news-every-30-seconds': {
        'task': 'app.tasks.news_crawler.crawl_news_sources',
        'schedule': 30.0,  # Every 30 seconds
    },
    'monitor-exchanges-every-minute': {
        'task': 'app.tasks.news_crawler.monitor_exchange_announcements',
        'schedule': 60.0,  # Every minute
    },
    'reset-daily-limits-at-midnight': {
        'task': 'app.tasks.news_crawler.reset_daily_notification_limits',
        'schedule': 86400.0,  # Every 24 hours
    },
}
celery_app.conf.timezone = 'UTC'

async def _crawl_news_sources_async():
    """异步抓取新闻源（由 Celery 同步任务驱动）"""
    sources = [
        {
            "url": "https://cointelegraph.com/rss",
            "name": "Cointelegraph",
            "category": "news"
        },
        {
            "url": "https://decrypt.co/feed",
            "name": "Decrypt",
            "category": "news"
        },
        {
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "name": "CoinDesk",
            "category": "news"
        },
        {
            "url": "https://bitcoinmagazine.com/feed",
            "name": "Bitcoin Magazine",
            "category": "bitcoin"
        },
        {
            "url": "https://www.theblockcrypto.com/rss.xml",
            "name": "The Block",
            "category": "news"
        }
    ]
    
    async with RSSFetcher() as fetcher:
        news_items = await fetcher.fetch_multiple_feeds(sources)
        
        processed_items = []
        for item in news_items:
            # Check for duplicates
            if not await fetcher.is_duplicate(item.get('content_hash', '')):
                # Analyze urgency based on keywords
                item['is_urgent'] = is_urgent_news(item)
                item['importance_score'] = calculate_importance(item)
                processed_items.append(item)
        
        logger = get_task_logger("news_crawler")
        logger.info(
            "News crawling completed",
            processed_count=len(processed_items),
            sources_count=len(sources),
            urgent_count=len([item for item in processed_items if item.get('is_urgent')])
        )
        return processed_items

async def _crawl_and_broadcast_news():
    """Complete pipeline: crawl news and broadcast via WebSocket + Telegram"""
    from app.services.broadcast_service import BroadcastService
    
    logger = get_task_logger("news_crawler")
    
    try:
        # Step 1: Crawl news sources
        logger.info("Starting news crawling phase")
        processed_items = await _crawl_news_sources_async()
        
        if not processed_items:
            logger.info("No new news items to broadcast")
            return
        
        # Step 2: Initialize broadcast service and process/broadcast news
        logger.info("Starting news broadcasting phase")
        broadcast_service = BroadcastService()
        
        # Process and broadcast news items
        broadcast_stats = await broadcast_service.process_and_broadcast_news(processed_items)
        
        # Log comprehensive statistics
        logger.info(
            "Complete news pipeline finished",
            **broadcast_stats,
            pipeline_phase="complete"
        )
        
        # Performance check: log if processing took too long
        if broadcast_stats.get('total_processed', 0) > 0:
            processing_efficiency = (broadcast_stats.get('database_saved', 0) / broadcast_stats.get('total_processed', 1)) * 100
            logger.info(
                "Processing efficiency metrics",
                processing_efficiency_percent=round(processing_efficiency, 2),
                ai_enhancement_rate=round((broadcast_stats.get('ai_analyzed', 0) / broadcast_stats.get('total_processed', 1)) * 100, 2),
                broadcast_success_rate=round((broadcast_stats.get('websocket_broadcasts', 0) / broadcast_stats.get('total_processed', 1)) * 100, 2)
            )
        
        return broadcast_stats
        
    except Exception as e:
        logger.error(
            "Critical error in complete news pipeline",
            error=str(e),
            exc_info=True,
            pipeline_phase="failed"
        )
        raise

def is_urgent_news(item: Dict) -> bool:
    """判断是否为紧急新闻"""
    urgent_keywords = [
        'breaking', 'urgent', 'alert', 'sec', 'regulation', 'ban', 
        'hack', 'exploit', 'crash', 'pump', 'dump', 'listing',
        '紧急', '突发', '监管', '禁止', '黑客', '攻击', '暴跌', '暴涨'
    ]
    
    text = f"{item.get('title', '')} {item.get('content', '')}".lower()
    return any(keyword in text for keyword in urgent_keywords)

def calculate_importance(item: Dict) -> int:
    """计算新闻重要性评分 (1-5)"""
    title = item.get('title', '').lower()
    content = item.get('content', '').lower()
    source = item.get('source', '').lower()
    
    score = 1
    
    # Source weight
    high_priority_sources = ['sec', 'federal reserve', 'coinbase', 'binance']
    if any(source_name in source for source_name in high_priority_sources):
        score += 2
    
    # Keyword weight
    high_impact_keywords = ['regulation', 'etf', 'approval', 'ban', 'listing']
    medium_impact_keywords = ['partnership', 'upgrade', 'launch', 'adoption']
    
    text = f"{title} {content}"
    for keyword in high_impact_keywords:
        if keyword in text:
            score += 2
    
    for keyword in medium_impact_keywords:
        if keyword in text:
            score += 1
    
    return min(score, 5)

@celery_app.task
def crawl_news_sources():
    """定时抓取新闻源（Celery 同步任务包装异步逻辑）"""
    logger = get_task_logger("news_crawler")
    try:
        logger.info("Starting scheduled news crawling task")
        asyncio.run(_crawl_and_broadcast_news())
        logger.info("News crawling and broadcasting task completed successfully")
    except Exception as e:
        logger.error(
            "News crawling task failed",
            error=str(e),
            exc_info=True
        )

async def _monitor_exchange_announcements_async():
    """异步监控交易所公告（完整实现）"""
    from app.services.exchange_api_service import ExchangeAPIService, PriceDataService
    from app.services.broadcast_service import BroadcastService
    
    logger = get_task_logger("exchange_monitor")
    logger.info("Starting comprehensive exchange announcement monitoring")
    
    try:
        # Step 1: Fetch announcements from all exchanges
        async with ExchangeAPIService() as exchange_service:
            announcements = await exchange_service.fetch_all_exchange_announcements()
        
        if not announcements:
            logger.info("No new exchange announcements found")
            return {"announcements_processed": 0, "price_analyses": 0}
        
        logger.info(
            "Exchange announcements fetched",
            count=len(announcements),
            exchanges=["Binance", "Coinbase", "OKX"]
        )
        
        # Step 2: Price impact analysis for announcements with affected tokens
        async with PriceDataService() as price_service:
            price_analyses = []
            
            for announcement in announcements:
                if announcement.affected_tokens:
                    # Fetch price data for affected tokens
                    price_data = await price_service.fetch_token_prices(announcement.affected_tokens)
                    
                    if price_data:
                        # Perform market impact analysis
                        impact_analysis = await price_service.analyze_market_impact(announcement, price_data)
                        price_analyses.append(impact_analysis)
                        
                        # Update announcement with analysis results
                        announcement.market_impact_level = impact_analysis.get('recommended_alert_level', 'low')
                        announcement.sentiment_indicator = impact_analysis.get('sentiment_indicator', 'neutral')
        
        # Step 3: Save announcements to database and broadcast
        from app.core.database import get_db
        from app.models.exchange import ExchangeAnnouncement as ExchangeAnnouncementModel
        
        saved_announcements = []
        async for session in get_db():
            try:
                for announcement in announcements:
                    # Check if announcement already exists
                    existing = await session.execute(
                        select(ExchangeAnnouncementModel).filter(
                            ExchangeAnnouncementModel.url == announcement.url
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue  # Skip duplicates
                    
                    # Create new announcement record
                    db_announcement = ExchangeAnnouncementModel(
                        title=announcement.title,
                        content=announcement.content,
                        url=announcement.url,
                        exchange=announcement.exchange,
                        category=announcement.category,
                        published_at=announcement.published_at,
                        importance_score=announcement.importance_score,
                        announcement_type=announcement.announcement_type,
                        affected_tokens=announcement.affected_tokens,
                        market_impact_level=getattr(announcement, 'market_impact_level', None),
                        sentiment_indicator=getattr(announcement, 'sentiment_indicator', None),
                        is_processed=False
                    )
                    
                    session.add(db_announcement)
                    saved_announcements.append(announcement)
                
                await session.commit()
                break  # Exit the async generator
                
            except Exception as e:
                logger.error(
                    "Database error saving exchange announcements",
                    error=str(e),
                    exc_info=True
                )
                await session.rollback()
                raise
        
        # Step 4: Broadcast high-importance announcements
        if saved_announcements:
            broadcast_service = BroadcastService()
            
            # Convert to format compatible with existing broadcast system
            news_items = []
            for announcement in saved_announcements:
                # Only broadcast high importance or urgent announcements
                if announcement.importance_score >= 4:
                    news_item = {
                        'title': f"[{announcement.exchange}] {announcement.title}",
                        'content': announcement.content,
                        'url': announcement.url,
                        'source': f"{announcement.exchange} API",
                        'category': 'exchange_announcement',
                        'published_at': announcement.published_at,
                        'importance_score': announcement.importance_score,
                        'is_urgent': announcement.importance_score >= 5,
                        'market_impact': announcement.importance_score,
                        'affected_tokens': announcement.affected_tokens
                    }
                    news_items.append(news_item)
            
            # Broadcast exchange announcements
            if news_items:
                broadcast_stats = await broadcast_service.process_and_broadcast_news(news_items)
                
                logger.info(
                    "Exchange announcements broadcasted",
                    **broadcast_stats,
                    announcement_source="exchange_api"
                )
        
        # Step 5: Performance metrics
        processing_summary = {
            "announcements_fetched": len(announcements),
            "announcements_saved": len(saved_announcements),
            "price_analyses_performed": len(price_analyses),
            "high_importance_broadcasted": len([a for a in saved_announcements if a.importance_score >= 4])
        }
        
        logger.info(
            "Exchange monitoring completed successfully",
            **processing_summary
        )
        
        return processing_summary
        
    except Exception as e:
        logger.error(
            "Critical error in exchange monitoring",
            error=str(e),
            exc_info=True
        )
        return {"error": str(e), "announcements_processed": 0}

@celery_app.task
def monitor_exchange_announcements():
    """监控交易所公告（Celery 同步任务包装异步逻辑）"""
    logger = get_task_logger("exchange_monitor")
    try:
        logger.info("Starting exchange monitoring task")
        asyncio.run(_monitor_exchange_announcements_async())
        logger.info("Exchange monitoring task completed")
    except Exception as e:
        logger.error(
            "Exchange monitoring task failed",
            error=str(e),
            exc_info=True
        )

@celery_app.task
def reset_daily_notification_limits():
    """Reset daily notification limits for all users"""
    logger = get_task_logger("daily_reset")
    try:
        logger.info("Starting daily notification limit reset task")
        asyncio.run(_reset_daily_limits_async())
        logger.info("Daily notification limit reset completed")
    except Exception as e:
        logger.error(
            "Daily limit reset task failed",
            error=str(e),
            exc_info=True
        )

async def _reset_daily_limits_async():
    """Reset daily notification limits asynchronously"""
    from app.services.user_filter_service import UserFilterService
    
    logger = get_task_logger("daily_reset")
    
    try:
        user_filter = UserFilterService()
        reset_count = await user_filter.reset_daily_limits()
        
        logger.info(
            "Daily notification limits reset successfully",
            reset_count=reset_count,
            reset_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        return reset_count
        
    except Exception as e:
        logger.error(
            "Error in daily limits reset",
            error=str(e),
            exc_info=True
        )
        raise