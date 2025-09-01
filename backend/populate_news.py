import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine, Base
from app.models.news import NewsItem
from app.services.rss_fetcher import RSSFetcher
from sqlalchemy import select
from app.core.logging import get_logger

logger = get_logger("populate_news")

async def populate_news_database():
    """手动填充新闻数据库"""
    logger.info("Starting news database population")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
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
        }
    ]
    
    async with RSSFetcher() as fetcher:
        news_items = await fetcher.fetch_multiple_feeds(sources)
        logger.info("RSS feeds fetched", total_items=len(news_items))
        
        from sqlalchemy.ext.asyncio import async_sessionmaker
        SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
        
        async with SessionLocal() as session:
            existing_urls = set()
            result = await session.execute(select(NewsItem.url))
            for row in result.fetchall():
                existing_urls.add(row[0])
            
            new_items = []
            for item in news_items:
                if item.get('url') not in existing_urls:
                    news_obj = NewsItem(
                        title=item.get('title', ''),
                        content=item.get('content', ''),
                        url=item.get('url', ''),
                        source=item.get('source', ''),
                        category=item.get('category', 'news'),
                        published_at=item.get('published_at'),
                        importance_score=item.get('importance_score', 1),
                        is_urgent=item.get('is_urgent', False),
                        market_impact=1,
                        sentiment_score=0.0,
                        is_processed=False
                    )
                    new_items.append(news_obj)
                    session.add(news_obj)
            
            await session.commit()
            logger.info("News items added to database", new_items_count=len(new_items))
            
            total_result = await session.execute(select(NewsItem))
            total_count = len(total_result.scalars().all())
            logger.info("Database population completed", total_items_in_db=total_count)

if __name__ == "__main__":
    asyncio.run(populate_news_database())