"""AI-powered news analysis service for cryptocurrency market intelligence.

This module provides comprehensive news analysis capabilities including:
- Automated news summarization using OpenAI GPT models
- Sentiment analysis for market impact assessment
- Key information extraction (tokens, prices, exchanges)
- Market impact scoring based on content analysis
- Parallel processing for improved performance

The service is designed to handle high-volume news processing with
proper error handling, logging, and graceful degradation when
AI services are unavailable.

Typical usage example:
    analyzer = AINewsAnalyzer(api_key="your-openai-key")
    analysis = await analyzer.analyze_news(news_item)
    print(f"Sentiment: {analysis['sentiment']}")

Author: NEWRSS Development Team
Version: 1.0.0
"""

import re
import json
import asyncio
from typing import Dict, List, Optional, Union, Any

from openai import AsyncOpenAI

from app.core.settings import settings
from app.core.logging import get_service_logger


class AINewsAnalyzer:
    """AI-powered news analysis service using OpenAI GPT models.
    
    This service provides comprehensive analysis of cryptocurrency news including
    sentiment analysis, summarization, and key information extraction. It uses
    parallel processing for efficiency and includes proper error handling for
    production environments.
    
    Attributes:
        client: Async OpenAI client instance for API calls.
        logger: Structured logger for service operations.
    """
    
    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the AI News Analyzer with OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, uses settings.OPENAI_API_KEY.
                    Service will gracefully degrade if no key is provided.
        """
        api_key_to_use = api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=api_key_to_use) if api_key_to_use else None
        self.logger = get_service_logger("ai_analyzer")
    
    async def analyze_news(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive analysis of a news item.
        
        Executes multiple analysis tasks in parallel for optimal performance:
        - News summarization
        - Sentiment analysis
        - Key information extraction
        - Market impact calculation
        
        Args:
            news_item: Dictionary containing news data with keys:
                - 'content': Full text content of the news
                - 'title': News headline
                - 'source': News source identifier
                
        Returns:
            Dict containing analysis results:
            - 'summary': Generated news summary (str)
            - 'sentiment': Sentiment score from -1 to 1 (float)
            - 'key_info': Extracted key information (dict)
            - 'market_impact': Market impact score 1-5 (int)
            
        Note:
            Failed analysis tasks return safe default values to ensure
            the service remains functional even with API issues.
        """
        if not self.client:
            return {
                'summary': news_item.get('title', 'No summary available'),
                'sentiment': 0.0,
                'key_info': {},
                'market_impact': 3
            }
            
        analysis: Dict[str, Any] = {}
        
        # Execute multiple analysis tasks in parallel for optimal performance
        tasks = [
            self.generate_summary(news_item['content']),
            self.analyze_sentiment(news_item['content']),
            self.extract_key_information(news_item['content'])
        ]
        
        summary, sentiment, key_info = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle task results with proper error fallbacks
        analysis['summary'] = summary if not isinstance(summary, Exception) else "Summary generation failed"
        analysis['sentiment'] = sentiment if not isinstance(sentiment, Exception) else 0.0
        analysis['key_info'] = key_info if not isinstance(key_info, Exception) else {}
        analysis['market_impact'] = await self.calculate_market_impact(news_item)
        
        return analysis
    
    async def generate_summary(self, content: str) -> str:
        """Generate concise summary of news content using OpenAI GPT.
        
        Creates a focused summary highlighting key information relevant
        to cryptocurrency markets. Uses Chinese prompts for better
        multilingual support.
        
        Args:
            content: Full text content to summarize.
            
        Returns:
            Generated summary string (max 50 Chinese characters).
            Returns fallback message if API is unavailable.
            
        Raises:
            No exceptions raised - errors are logged and handled gracefully.
        """
        if not self.client.api_key:
            return "OpenAI API Key not configured"
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional cryptocurrency news analyst. Generate concise Chinese summaries highlighting key information."
                    },
                    {
                        "role": "user", 
                        "content": f"Please generate a summary for the following news (within 50 characters):\n\n{content}"
                    }
                ],
                max_tokens=100,
                temperature=0.3  # Low temperature for consistent, focused summaries
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            self.logger.error(
                "AI summary generation failed",
                content_length=len(content),
                error=str(e),
                exc_info=True
            )
            return "Summary generation failed"
    
    async def analyze_sentiment(self, content: str) -> float:
        """Analyze market sentiment of news content.
        
        Uses OpenAI GPT to determine the sentiment impact on cryptocurrency
        markets. Returns a normalized score between -1 and 1.
        
        Args:
            content: News content to analyze for sentiment.
            
        Returns:
            Sentiment score:
            - -1.0: Extremely negative market impact
            - 0.0: Neutral market impact  
            - 1.0: Extremely positive market impact
            
        Note:
            Returns 0.0 (neutral) if analysis fails or API is unavailable.
        """
        if not self.client.api_key:
            return 0.0
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the market sentiment of cryptocurrency news. Return a value between -1 and 1: -1 extremely negative, 0 neutral, 1 extremely positive. Return only the numerical value."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=10,
                temperature=0.1  # Very low temperature for consistent scoring
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
    
    async def calculate_market_impact(self, news_item: Dict[str, Any]) -> int:
        """Calculate market impact score based on content and source analysis.
        
        Analyzes news content using keyword matching and source authority
        to determine potential market impact. This is a rule-based system
        that doesn't require external API calls.
        
        Args:
            news_item: Dictionary containing:
                - 'content': News text content
                - 'title': News headline
                - 'source': Source identifier
                
        Returns:
            Market impact score:
            - 1: Low impact (general news, minor updates)
            - 2: Minor impact (partnerships, minor listings)
            - 3: Moderate impact (major partnerships, significant updates)
            - 4: High impact (regulatory news, major technical issues)
            - 5: Critical impact (major regulatory actions, security breaches)
            
        Algorithm:
            - Base score: 1
            - High impact keywords: +2 each
            - Medium impact keywords: +1 each
            - High authority sources: +2
            - Maximum score capped at 5
        """
        content = news_item.get('content', '').lower()
        title = news_item.get('title', '').lower()
        source = news_item.get('source', '').lower()
        
        # High impact keywords that significantly affect market sentiment
        high_impact_keywords = [
            'regulation', 'ban', 'approval', 'etf', 'sec', 'fed', 'federal reserve',
            '监管', '禁止', '批准', '央行', '政策', 'lawsuit', 'fine', 'penalty',
            'hack', 'exploit', 'vulnerability', 'breach', 'stolen', 'freeze'
        ]
        
        # Medium impact keywords for moderate market effects
        medium_impact_keywords = [
            'partnership', 'adoption', 'launch', 'upgrade', 'fork',
            '合作', '采用', '发布', '升级', 'listing', 'delisting',
            'acquisition', 'merger', 'investment', 'funding'
        ]
        
        score = 1  # Base score
        combined_text = f"{title} {content}"
        
        # Check for high impact keywords
        for keyword in high_impact_keywords:
            if keyword in combined_text:
                score += 2
        
        # Check for medium impact keywords
        for keyword in medium_impact_keywords:
            if keyword in combined_text:
                score += 1
        
        # High authority sources get additional weight
        high_authority_sources = [
            'sec', 'federal reserve', 'treasury', 'cftc', 'finra',
            '央行', '证监会', 'binance', 'coinbase', 'kraken'
        ]
        
        if any(auth_source in source for auth_source in high_authority_sources):
            score += 2
        
        # Cap the maximum score at 5
        return min(score, 5)
    
    async def extract_key_information(self, content: str) -> Dict[str, List[str]]:
        """Extract key information from news content using regex patterns.
        
        Identifies and extracts:
        - Cryptocurrency tokens/symbols
        - Price information and values
        - Exchange platform mentions
        - Dates and timeframes (future enhancement)
        - Key people/entities (future enhancement)
        
        Args:
            content: News text content to analyze.
            
        Returns:
            Dictionary with extracted information:
            - 'tokens': List of cryptocurrency symbols
            - 'prices': List of price mentions
            - 'exchanges': List of exchange platforms
            - 'dates': List of dates (placeholder)
            - 'people': List of people mentioned (placeholder)
            
        Note:
            This is a rule-based extraction system that works offline.
            Future versions may integrate with NLP models for better accuracy.
        """
        key_info: Dict[str, List[str]] = {
            'tokens': [],
            'prices': [],
            'dates': [],
            'exchanges': [],
            'people': []
        }
        
        # Extract cryptocurrency symbols (2-6 uppercase letters)
        # Filter out common false positives
        token_pattern = r'\b[A-Z]{2,6}\b'
        tokens = re.findall(token_pattern, content)
        excluded_words = {'SEC', 'CEO', 'CTO', 'CFO', 'USA', 'USD', 'API', 'FAQ', 'ATH', 'ATL'}
        key_info['tokens'] = list(set(tokens) - excluded_words)
        
        # Extract price information with multiple formats
        price_patterns = [
            r'\$[\d,]+\.?\d*',      # $1,000.50
            r'[\d,]+\.?\d*\s*USD',  # 1000 USD
            r'[\d,]+\.?\d*\s*美元',  # 1000 美元
        ]
        
        for pattern in price_patterns:
            prices = re.findall(pattern, content, re.IGNORECASE)
            key_info['prices'].extend(prices)
        
        # Extract major cryptocurrency exchange mentions
        exchanges = [
            'Binance', 'Coinbase', 'OKX', 'Kraken', 'Huobi', 'Bybit',
            'KuCoin', 'Gate.io', 'FTX', 'Bitfinex', 'Bitget'
        ]
        for exchange in exchanges:
            if exchange.lower() in content.lower():
                key_info['exchanges'].append(exchange)
        
        # Remove duplicates from all lists
        for key in key_info:
            if key_info[key]:
                key_info[key] = list(set(key_info[key]))
        
        return key_info