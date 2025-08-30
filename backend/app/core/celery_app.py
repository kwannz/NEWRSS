from celery import Celery
from app.core.settings import settings

celery_app = Celery(
    "newrss",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.crawler", "app.tasks.ai_analyzer", "app.tasks.news_aggregator"]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'crawl-news-feeds': {
            'task': 'app.tasks.crawler.crawl_all_feeds',
            'schedule': 300.0,  # Every 5 minutes
        },
        'analyze-news': {
            'task': 'app.tasks.ai_analyzer.analyze_unprocessed_news',
            'schedule': 600.0,  # Every 10 minutes
        },
        'aggregate-news': {
            'task': 'app.tasks.news_aggregator.aggregate_daily_news',
            'schedule': 86400.0,  # Daily
        },
    }
)