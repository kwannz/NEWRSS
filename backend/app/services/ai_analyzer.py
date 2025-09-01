from openai import AsyncOpenAI
from typing import Dict, List
import re
import json
from app.core.settings import settings
from app.core.logging import get_service_logger

class AINewsAnalyzer:
    def __init__(self, api_key: str = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.logger = get_service_logger("ai_analyzer")
    
    async def analyze_news(self, news_item: dict) -> dict:
        """综合分析新闻"""
        analysis = {}
        
        # 并行执行多个分析任务
        import asyncio
        tasks = [
            self.generate_summary(news_item['content']),
            self.analyze_sentiment(news_item['content']),
            self.extract_key_information(news_item['content'])
        ]
        
        summary, sentiment, key_info = await asyncio.gather(*tasks, return_exceptions=True)
        
        analysis['summary'] = summary if not isinstance(summary, Exception) else "摘要生成失败"
        analysis['sentiment'] = sentiment if not isinstance(sentiment, Exception) else 0.0
        analysis['key_info'] = key_info if not isinstance(key_info, Exception) else {}
        analysis['market_impact'] = await self.calculate_market_impact(news_item)
        
        return analysis
    
    async def generate_summary(self, content: str) -> str:
        """生成新闻摘要"""
        if not self.client.api_key:
            return "未配置 OpenAI API Key"
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个专业的加密货币新闻分析师。请生成简洁的中文摘要，突出关键信息。"
                    },
                    {
                        "role": "user", 
                        "content": f"请为以下新闻生成摘要（50字以内）：\n\n{content}"
                    }
                ],
                max_tokens=100,
                temperature=0.3
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            self.logger.error(
                "AI summary generation failed",
                content_length=len(content),
                error=str(e),
                exc_info=True
            )
            return "摘要生成失败"
    
    async def analyze_sentiment(self, content: str) -> float:
        """分析情感倾向 (-1 to 1)"""
        if not self.client.api_key:
            return 0.0
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "分析以下加密货币新闻的市场情感。返回 -1 到 1 之间的数值：-1 极度负面，0 中性，1 极度正面。只返回数值。"
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            sentiment_text = response.choices[0].message.content or "0"
            return float(sentiment_text.strip())
        except Exception as e:
            self.logger.error(
                "AI sentiment analysis failed",
                content_length=len(content),
                error=str(e),
                exc_info=True
            )
            return 0.0
    
    async def calculate_market_impact(self, news_item: dict) -> int:
        """计算市场影响评分 (1-5)"""
        content = news_item.get('content', '').lower()
        title = news_item.get('title', '').lower()
        source = news_item.get('source', '').lower()
        
        # 关键词权重
        high_impact_keywords = [
            'regulation', 'ban', 'approval', 'etf', 'sec', 'fed', 'federal reserve',
            '监管', '禁止', '批准', '央行', '政策', 'lawsuit', 'fine', 'penalty',
            'hack', 'exploit', 'vulnerability', 'breach', 'stolen', 'freeze'
        ]
        
        medium_impact_keywords = [
            'partnership', 'adoption', 'launch', 'upgrade', 'fork',
            '合作', '采用', '发布', '升级', 'listing', 'delisting',
            'acquisition', 'merger', 'investment', 'funding'
        ]
        
        score = 1
        text = f"{title} {content}"
        
        # 检查高影响关键词
        for keyword in high_impact_keywords:
            if keyword in text:
                score += 2
        
        # 检查中等影响关键词
        for keyword in medium_impact_keywords:
            if keyword in text:
                score += 1
        
        # 来源权重
        high_authority_sources = [
            'sec', 'federal reserve', 'treasury', 'cftc', 'finra',
            '央行', '证监会', 'binance', 'coinbase', 'kraken'
        ]
        
        if any(auth_source in source for auth_source in high_authority_sources):
            score += 2
        
        return min(score, 5)
    
    async def extract_key_information(self, content: str) -> dict:
        """提取关键信息"""
        key_info = {
            'tokens': [],
            'prices': [],
            'dates': [],
            'exchanges': [],
            'people': []
        }
        
        # 提取代币符号 (2-6 个大写字母)
        token_pattern = r'\b[A-Z]{2,6}\b'
        tokens = re.findall(token_pattern, content)
        # 过滤常见非代币词汇
        excluded_words = {'SEC', 'CEO', 'CTO', 'CFO', 'USA', 'USD', 'API', 'FAQ', 'ATH', 'ATL'}
        key_info['tokens'] = list(set(tokens) - excluded_words)
        
        # 提取价格信息
        price_patterns = [
            r'\$[\d,]+\.?\d*',  # $1,000.50
            r'[\d,]+\.?\d*\s*USD',  # 1000 USD
            r'[\d,]+\.?\d*\s*美元',  # 1000 美元
        ]
        
        for pattern in price_patterns:
            prices = re.findall(pattern, content, re.IGNORECASE)
            key_info['prices'].extend(prices)
        
        # 提取交易所名称
        exchanges = [
            'Binance', 'Coinbase', 'OKX', 'Kraken', 'Huobi', 'Bybit',
            'KuCoin', 'Gate.io', 'FTX', 'Bitfinex', 'Bitget'
        ]
        for exchange in exchanges:
            if exchange.lower() in content.lower():
                key_info['exchanges'].append(exchange)
        
        # 去重
        key_info['exchanges'] = list(set(key_info['exchanges']))
        key_info['prices'] = list(set(key_info['prices']))
        
        return key_info