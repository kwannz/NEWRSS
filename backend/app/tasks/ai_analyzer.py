import asyncio
from celery import current_app
from app.services.ai_analyzer import AINewsAnalyzer
from app.core.database import get_db
from app.models.news import NewsItem
from sqlalchemy import select

async def _analyze_unprocessed_news_async():
    """异步分析未处理的新闻"""
    async for db in get_db():
        try:
            result = await db.execute(
                select(NewsItem).where(NewsItem.is_processed == False)
            )
            unprocessed_news = result.scalars().all()
            
            if not unprocessed_news:
                print("No unprocessed news items found")
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
                    print(f"Analyzed: {news_item.title}")
                    
                except Exception as e:
                    print(f"Error analyzing news {news_item.id}: {e}")
                    continue
            
        except Exception as e:
            print(f"Database error in analysis: {e}")
        finally:
            break

@current_app.task
def analyze_unprocessed_news():
    """分析未处理的新闻"""
    try:
        asyncio.run(_analyze_unprocessed_news_async())
    except Exception as e:
        print(f"Error in analyze_unprocessed_news: {e}")