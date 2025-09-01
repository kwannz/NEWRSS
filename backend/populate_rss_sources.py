#!/usr/bin/env python3
"""
填充RSS源数据到数据库
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.news import NewsSource
from app.config.rss_sources import get_all_sources
from datetime import datetime
from app.core.logging import get_logger

# Initialize logging
logger = get_logger("populate_rss_sources")

async def populate_news_sources():
    """填充新闻源到数据库"""
    async with SessionLocal() as session:
        try:
            # 获取所有RSS源配置
            rss_sources = get_all_sources()
            
            logger.info("Starting RSS source population", total_sources=len(rss_sources))
            
            for source_config in rss_sources:
                # 检查是否已存在
                result = await session.execute(
                    select(NewsSource).where(NewsSource.name == source_config["name"])
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info("Updating RSS source", source_name=source_config['name'])
                    # 更新现有记录
                    existing.url = source_config["url"]
                    existing.source_type = source_config["source_type"]
                    existing.category = source_config["category"]
                    existing.priority = source_config["priority"]
                    existing.is_active = True
                    existing.fetch_interval = 1800  # 30分钟
                    existing.updated_at = datetime.utcnow()
                else:
                    logger.info("Adding new RSS source", source_name=source_config['name'], url=source_config['url'])
                    # 创建新记录
                    news_source = NewsSource(
                        name=source_config["name"],
                        url=source_config["url"],
                        source_type=source_config["source_type"],
                        category=source_config["category"],
                        is_active=True,
                        fetch_interval=1800,  # 30分钟
                        priority=source_config["priority"],
                        created_at=datetime.utcnow()
                    )
                    session.add(news_source)
            
            await session.commit()
            logger.info("RSS source population completed successfully")
            
            # 显示统计信息
            exchange_count = len([s for s in rss_sources if s["category"] == "exchange"])
            news_count = len([s for s in rss_sources if s["category"] == "news"])
            chinese_count = len([s for s in rss_sources if s["language"] == "zh"])
            
            logger.info(
                "RSS source population statistics",
                exchange_sources=exchange_count,
                news_sources=news_count,
                chinese_sources=chinese_count,
                total_sources=len(rss_sources)
            )
            
        except Exception as e:
            logger.error(
                "RSS source population failed",
                error=str(e),
                exc_info=True
            )
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(populate_news_sources())