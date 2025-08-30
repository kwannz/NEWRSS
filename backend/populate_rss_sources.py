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

async def populate_news_sources():
    """填充新闻源到数据库"""
    async with SessionLocal() as session:
        try:
            # 获取所有RSS源配置
            rss_sources = get_all_sources()
            
            print(f"开始填充 {len(rss_sources)} 个RSS源...")
            
            for source_config in rss_sources:
                # 检查是否已存在
                result = await session.execute(
                    select(NewsSource).where(NewsSource.name == source_config["name"])
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    print(f"更新RSS源: {source_config['name']}")
                    # 更新现有记录
                    existing.url = source_config["url"]
                    existing.source_type = source_config["source_type"]
                    existing.category = source_config["category"]
                    existing.priority = source_config["priority"]
                    existing.is_active = True
                    existing.fetch_interval = 1800  # 30分钟
                    existing.updated_at = datetime.utcnow()
                else:
                    print(f"添加新RSS源: {source_config['name']}")
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
            print("✅ RSS源数据填充完成!")
            
            # 显示统计信息
            exchange_count = len([s for s in rss_sources if s["category"] == "exchange"])
            news_count = len([s for s in rss_sources if s["category"] == "news"])
            chinese_count = len([s for s in rss_sources if s["language"] == "zh"])
            
            print(f"\n📊 统计信息:")
            print(f"   交易所源: {exchange_count}")
            print(f"   新闻源: {news_count}")
            print(f"   中文源: {chinese_count}")
            print(f"   总计: {len(rss_sources)}")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(populate_news_sources())