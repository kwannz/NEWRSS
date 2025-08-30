import asyncio
from celery import current_app
from typing import Dict, List
from app.services.rss_fetcher import RSSFetcher
from app.config.rss_sources_clean import get_all_sources, EXCHANGE_URGENT_KEYWORDS, IMPORTANCE_WEIGHTS

async def _crawl_all_feeds_async():
    """异步抓取所有RSS订阅源"""
    sources = get_all_sources()
    
    async with RSSFetcher() as fetcher:
        news_items = await fetcher.fetch_multiple_feeds(sources)
        
        processed_items = []
        for item in news_items:
            if not await fetcher.is_duplicate(item.get('content_hash', '')):
                item['is_urgent'] = is_urgent_news(item)
                item['importance_score'] = calculate_importance(item)
                processed_items.append(item)
        
        print(f"Processed {len(processed_items)} new items")
        return processed_items

def is_urgent_news(item: Dict) -> bool:
    """判断是否为紧急新闻"""
    # 基础紧急关键词
    base_urgent_keywords = [
        'breaking', 'urgent', 'alert', 'sec', 'regulation', 'ban', 
        'hack', 'exploit', 'crash', 'pump', 'dump', 'scam',
        '紧急', '突发', '监管', '禁止', '黑客', '攻击', '暴跌', '暴涨', '骗局'
    ]
    
    # 交易所特定关键词
    exchange_keywords = EXCHANGE_URGENT_KEYWORDS["en"] + EXCHANGE_URGENT_KEYWORDS["zh"]
    
    # 合并所有关键词
    all_keywords = base_urgent_keywords + exchange_keywords
    
    text = f"{item.get('title', '')} {item.get('content', '')}".lower()
    
    # 检查是否包含紧急关键词
    for keyword in all_keywords:
        if keyword.lower() in text:
            return True
    
    # 检查是否为交易所公告
    source = item.get('source', '').lower()
    exchange_sources = ['binance', 'coinbase', 'okx', 'bybit', 'kraken', 'huobi', 'kucoin']
    if any(exchange in source for exchange in exchange_sources):
        # 交易所公告中的特定模式
        exchange_urgent_patterns = ['listing', 'delisting', 'maintenance', 'suspended', 'halted']
        if any(pattern in text for pattern in exchange_urgent_patterns):
            return True
    
    return False

def calculate_importance(item: Dict) -> int:
    """计算新闻重要性评分 (1-5)"""
    title = item.get('title', '').lower()
    content = item.get('content', '').lower()
    source = item.get('source', '').lower()
    
    score = 1
    
    # 交易所源基础评分
    major_exchanges = ['binance', 'coinbase', 'okx', 'bybit', 'kraken']
    if any(exchange in source for exchange in major_exchanges):
        score += IMPORTANCE_WEIGHTS["exchange_announcement"]
    
    # 监管机构和权威源
    authority_sources = ['sec', 'federal reserve', 'cftc', 'treasury', 'bis']
    if any(auth_source in source for auth_source in authority_sources):
        score += 3
    
    text = f"{title} {content}"
    
    # 安全警报（最高优先级）
    security_keywords = ['hack', 'exploit', 'vulnerability', 'security breach', 'stolen', '黑客', '漏洞', '被盗']
    if any(keyword in text for keyword in security_keywords):
        score += IMPORTANCE_WEIGHTS["security_alert"]
    
    # 上币/下架新闻
    listing_keywords = ['listing', 'delisting', 'new pair', 'trading pair', '上币', '下架', '新交易对']
    if any(keyword in text for keyword in listing_keywords):
        score += IMPORTANCE_WEIGHTS["listing_news"]
    
    # 监管新闻
    regulatory_keywords = ['regulation', 'regulatory', 'etf', 'approval', 'ban', 'legal', '监管', '批准', '禁止', '合规']
    if any(keyword in text for keyword in regulatory_keywords):
        score += IMPORTANCE_WEIGHTS["regulatory_news"]
    
    # 合作伙伴关系
    partnership_keywords = ['partnership', 'collaboration', 'integration', 'alliance', '合作', '集成', '联盟']
    if any(keyword in text for keyword in partnership_keywords):
        score += IMPORTANCE_WEIGHTS["partnership"]
    
    # 技术更新
    tech_keywords = ['upgrade', 'update', 'launch', 'mainnet', 'testnet', 'fork', '升级', '更新', '上线', '分叉']
    if any(keyword in text for keyword in tech_keywords):
        score += IMPORTANCE_WEIGHTS["technical_update"]
    
    # 市场分析（基础分数）
    analysis_keywords = ['analysis', 'forecast', 'prediction', 'outlook', '分析', '预测', '展望']
    if any(keyword in text for keyword in analysis_keywords):
        score += IMPORTANCE_WEIGHTS["market_analysis"]
    
    return min(score, 5)

@current_app.task
def crawl_all_feeds():
    """定时抓取所有RSS订阅源"""
    try:
        asyncio.run(_crawl_all_feeds_async())
    except Exception as e:
        print(f"Error in crawl_all_feeds: {e}")