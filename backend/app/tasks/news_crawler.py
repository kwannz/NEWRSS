import asyncio
from celery import Celery
from typing import Dict
from app.services.rss_fetcher import RSSFetcher
from app.core.settings import settings

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
        
        print(f"Processed {len(processed_items)} new items")
        return processed_items

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
    try:
        asyncio.run(_crawl_news_sources_async())
    except Exception as e:
        print(f"Error in crawl_news_sources: {e}")

async def _monitor_exchange_announcements_async():
    """异步监控交易所公告（示例占位）"""
    # TODO: 实现交易所 API 监控逻辑
    print("Monitoring exchange announcements...")
    return

@celery_app.task
def monitor_exchange_announcements():
    """监控交易所公告（Celery 同步任务包装异步逻辑）"""
    try:
        asyncio.run(_monitor_exchange_announcements_async())
    except Exception as e:
        print(f"Error in monitor_exchange_announcements: {e}")