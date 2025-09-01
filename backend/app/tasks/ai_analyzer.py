import asyncio
from celery import current_app
from app.services.ai_analyzer import AINewsAnalyzer
from app.core.database import get_db
from app.models.news import NewsItem
from sqlalchemy import select
from app.core.logging import get_task_logger

async def _analyze_unprocessed_news_async():
    """异步分析未处理的新闻"""
    logger = get_task_logger("ai_analyzer")
    async for db in get_db():
        try:
            result = await db.execute(
                select(NewsItem).where(NewsItem.is_processed == False)
            )
            unprocessed_news = result.scalars().all()
            
            if not unprocessed_news:
                logger.info("No unprocessed news items found for AI analysis")
                return
            
            analyzer = AINewsAnalyzer()
            
            for news_item in unprocessed_news:
                try:
                    analysis = await analyzer.analyze_news({
                        'title': news_item.title,
                        'content': news_item.content
                    })
                    
                    if analysis:
                        news_item.sentiment_score = analysis.get('sentiment', 0)
                        news_item.market_impact = analysis.get('market_impact', 1)
                        news_item.is_processed = True
                        
                    await db.commit()
                    logger.info(
                        "News item analyzed",
                        news_id=news_item.id,
                        title=news_item.title[:50],
                        sentiment=analysis.get('sentiment'),
                        market_impact=analysis.get('market_impact')
                    )
                    
                except Exception as e:
                    logger.error(
                        "AI analysis failed for news item",
                        news_id=news_item.id,
                        title=news_item.title[:50],
                        error=str(e),
                        exc_info=True
                    )
                    continue
            
        except Exception as e:
            logger.error(
                "Database error during AI analysis",
                error=str(e),
                exc_info=True
            )
        finally:
            break

@current_app.task
def analyze_unprocessed_news():
    """分析未处理的新闻"""
    logger = get_task_logger("ai_analyzer")
    try:
        logger.info("Starting AI analysis of unprocessed news")
        asyncio.run(_analyze_unprocessed_news_async())
        logger.info("AI analysis task completed successfully")
    except Exception as e:
        logger.error(
            "AI analysis task failed",
            error=str(e),
            exc_info=True
        )