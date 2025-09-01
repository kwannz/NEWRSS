"""
Exchange API Service for cryptocurrency news aggregation from major exchanges.

This service provides connectors for:
- Binance announcements API
- Coinbase Pro API
- OKX announcement feeds

Features:
- Rate limiting compliance
- Robust error handling
- Real-time price data integration
- Market impact analysis
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from app.core.logging import get_service_logger
from app.core.redis import get_redis


@dataclass
class ExchangeAnnouncement:
    """Standardized format for exchange announcements"""
    title: str
    content: str
    url: str
    exchange: str
    category: str
    published_at: datetime
    importance_score: int
    market_impact: Optional[str] = None
    affected_tokens: Optional[List[str]] = None
    announcement_type: Optional[str] = None


@dataclass
class PriceData:
    """Real-time price data structure"""
    symbol: str
    price: float
    change_24h: float
    change_percent_24h: float
    volume_24h: float
    last_updated: datetime
    exchange: str


class RateLimiter:
    """Simple rate limiter using Redis for persistence"""
    
    def __init__(self, redis_key: str, max_requests: int, time_window: int):
        self.redis_key = redis_key
        self.max_requests = max_requests
        self.time_window = time_window
        self.logger = get_service_logger("rate_limiter")
    
    async def can_proceed(self) -> bool:
        """Check if request can proceed within rate limits"""
        redis = await get_redis()
        current_time = int(datetime.utcnow().timestamp())
        window_start = current_time - self.time_window
        
        # Clean old entries
        await redis.zremrangebyscore(self.redis_key, 0, window_start)
        
        # Count current requests
        current_count = await redis.zcard(self.redis_key)
        
        if current_count >= self.max_requests:
            self.logger.warning(
                "Rate limit exceeded",
                redis_key=self.redis_key,
                current_count=current_count,
                max_requests=self.max_requests
            )
            return False
        
        # Add current request
        await redis.zadd(self.redis_key, {str(current_time): current_time})
        await redis.expire(self.redis_key, self.time_window)
        
        return True
    
    async def wait_if_needed(self) -> None:
        """Wait if rate limit is hit"""
        while not await self.can_proceed():
            self.logger.info(
                "Rate limit hit, waiting",
                redis_key=self.redis_key,
                wait_seconds=10
            )
            await asyncio.sleep(10)


class ExchangeAPIService:
    """
    Unified service for fetching cryptocurrency news and data from major exchanges.
    Handles rate limiting, error recovery, and data standardization.
    """
    
    def __init__(self):
        self.session = None
        self.logger = get_service_logger("exchange_api")
        
        # Exchange-specific rate limiters
        self.binance_limiter = RateLimiter("binance_api_calls", 1200, 60)  # 1200/min
        self.coinbase_limiter = RateLimiter("coinbase_api_calls", 10, 1)   # 10/sec
        self.okx_limiter = RateLimiter("okx_api_calls", 20, 2)            # 20/2sec
        
        # Base URLs
        self.binance_base = "https://www.binance.com/bapi"
        self.coinbase_base = "https://api.coinbase.com/v2"
        self.okx_base = "https://www.okx.com/api"
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'NEWRSS/1.0 (Cryptocurrency News Aggregator)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    # BINANCE API INTEGRATION
    
    async def fetch_binance_announcements(self, limit: int = 20) -> List[ExchangeAnnouncement]:
        """
        Fetch latest announcements from Binance.
        Uses Binance's public API for announcements.
        """
        await self.binance_limiter.wait_if_needed()
        
        try:
            # Binance announcement endpoint
            url = f"{self.binance_base}/cms/v1/public/cms/article/list/query"
            params = {
                'type': 1,  # Announcements
                'catalogId': 48,  # General announcements
                'pageNo': 1,
                'pageSize': limit
            }
            
            async with self.session.post(url, json=params) as response:
                if response.status != 200:
                    self.logger.error(
                        "Binance API request failed",
                        status=response.status,
                        url=url
                    )
                    return []
                
                data = await response.json()
                return await self._parse_binance_announcements(data)
                
        except Exception as e:
            self.logger.error(
                "Error fetching Binance announcements",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def _parse_binance_announcements(self, data: Dict) -> List[ExchangeAnnouncement]:
        """Parse Binance API response into standardized format"""
        announcements = []
        
        if not data.get('data', {}).get('catalogs'):
            return announcements
        
        for item in data['data']['catalogs'][0].get('articles', []):
            try:
                # Parse timestamp
                published_at = datetime.fromtimestamp(item.get('releaseDate', 0) / 1000)
                
                # Determine importance and market impact
                title = item.get('title', '')
                importance_score = self._calculate_binance_importance(title)
                affected_tokens = self._extract_tokens_from_text(title)
                
                announcement = ExchangeAnnouncement(
                    title=title,
                    content=item.get('body', ''),
                    url=f"https://www.binance.com/en/support/announcement/{item.get('code', '')}",
                    exchange="Binance",
                    category=item.get('type', {}).get('name', 'General'),
                    published_at=published_at,
                    importance_score=importance_score,
                    affected_tokens=affected_tokens,
                    announcement_type="exchange_announcement"
                )
                announcements.append(announcement)
                
            except Exception as e:
                self.logger.error(
                    "Error parsing Binance announcement",
                    item_id=item.get('id'),
                    error=str(e)
                )
        
        self.logger.info(
            "Binance announcements fetched",
            count=len(announcements),
            exchange="Binance"
        )
        return announcements
    
    # COINBASE PRO API INTEGRATION
    
    async def fetch_coinbase_announcements(self, limit: int = 20) -> List[ExchangeAnnouncement]:
        """
        Fetch announcements from Coinbase Pro.
        Uses Coinbase's public blog RSS and product updates.
        """
        await self.coinbase_limiter.wait_if_needed()
        
        try:
            # Coinbase blog RSS (crypto announcements)
            blog_url = "https://blog.coinbase.com/feed"
            
            async with self.session.get(blog_url) as response:
                if response.status != 200:
                    self.logger.error(
                        "Coinbase blog RSS request failed",
                        status=response.status,
                        url=blog_url
                    )
                    return []
                
                content = await response.text()
                return await self._parse_coinbase_rss(content)
                
        except Exception as e:
            self.logger.error(
                "Error fetching Coinbase announcements",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def _parse_coinbase_rss(self, rss_content: str) -> List[ExchangeAnnouncement]:
        """Parse Coinbase RSS feed into standardized format"""
        import feedparser
        
        announcements = []
        feed = feedparser.parse(rss_content)
        
        for entry in feed.entries[:20]:  # Limit to latest 20
            try:
                # Parse timestamp
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])
                else:
                    published_at = datetime.now()
                
                # Filter for crypto-related content
                title = entry.get('title', '')
                if not self._is_crypto_related(title):
                    continue
                
                importance_score = self._calculate_coinbase_importance(title)
                affected_tokens = self._extract_tokens_from_text(title)
                
                announcement = ExchangeAnnouncement(
                    title=title,
                    content=entry.get('summary', ''),
                    url=entry.get('link', ''),
                    exchange="Coinbase",
                    category="Blog",
                    published_at=published_at,
                    importance_score=importance_score,
                    affected_tokens=affected_tokens,
                    announcement_type="blog_post"
                )
                announcements.append(announcement)
                
            except Exception as e:
                self.logger.error(
                    "Error parsing Coinbase RSS entry",
                    entry_title=entry.get('title'),
                    error=str(e)
                )
        
        self.logger.info(
            "Coinbase announcements fetched",
            count=len(announcements),
            exchange="Coinbase"
        )
        return announcements
    
    # OKX API INTEGRATION
    
    async def fetch_okx_announcements(self, limit: int = 20) -> List[ExchangeAnnouncement]:
        """
        Fetch announcements from OKX exchange.
        Uses OKX's public announcement API.
        """
        await self.okx_limiter.wait_if_needed()
        
        try:
            # OKX public announcement endpoint
            url = f"{self.okx_base}/v5/public/announcements"
            params = {
                'annType': 'all',
                'limit': str(limit)
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    self.logger.error(
                        "OKX API request failed",
                        status=response.status,
                        url=url
                    )
                    return []
                
                data = await response.json()
                return await self._parse_okx_announcements(data)
                
        except Exception as e:
            self.logger.error(
                "Error fetching OKX announcements",
                error=str(e),
                exc_info=True
            )
            return []
    
    async def _parse_okx_announcements(self, data: Dict) -> List[ExchangeAnnouncement]:
        """Parse OKX API response into standardized format"""
        announcements = []
        
        for item in data.get('data', []):
            try:
                # Parse timestamp (OKX uses milliseconds)
                published_at = datetime.fromtimestamp(int(item.get('cTime', 0)) / 1000)
                
                title = item.get('title', '')
                importance_score = self._calculate_okx_importance(title, item.get('annType', ''))
                affected_tokens = self._extract_tokens_from_text(title)
                
                announcement = ExchangeAnnouncement(
                    title=title,
                    content=item.get('content', ''),
                    url=f"https://www.okx.com/support/hc/en-us/articles/{item.get('id', '')}",
                    exchange="OKX",
                    category=item.get('annType', 'General'),
                    published_at=published_at,
                    importance_score=importance_score,
                    affected_tokens=affected_tokens,
                    announcement_type="exchange_announcement"
                )
                announcements.append(announcement)
                
            except Exception as e:
                self.logger.error(
                    "Error parsing OKX announcement",
                    item_id=item.get('id'),
                    error=str(e)
                )
        
        self.logger.info(
            "OKX announcements fetched",
            count=len(announcements),
            exchange="OKX"
        )
        return announcements
    
    # UNIFIED FETCHING METHOD
    
    async def fetch_all_exchange_announcements(self) -> List[ExchangeAnnouncement]:
        """
        Fetch announcements from all supported exchanges concurrently.
        Returns combined and deduplicated list.
        """
        self.logger.info("Starting comprehensive exchange announcement fetch")
        
        # Fetch from all exchanges concurrently
        tasks = [
            self.fetch_binance_announcements(),
            self.fetch_coinbase_announcements(),
            self.fetch_okx_announcements()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_announcements = []
        exchange_names = ["Binance", "Coinbase", "OKX"]
        
        for i, result in enumerate(results):
            if isinstance(result, list):
                all_announcements.extend(result)
                self.logger.info(
                    "Exchange fetch completed",
                    exchange=exchange_names[i],
                    count=len(result)
                )
            elif isinstance(result, Exception):
                self.logger.error(
                    "Exchange fetch failed",
                    exchange=exchange_names[i],
                    error=str(result)
                )
        
        # Deduplicate based on title and content hash
        deduplicated = await self._deduplicate_announcements(all_announcements)
        
        self.logger.info(
            "Exchange announcement fetch completed",
            total_fetched=len(all_announcements),
            deduplicated_count=len(deduplicated),
            exchanges=len(exchange_names)
        )
        
        return deduplicated
    
    # UTILITY METHODS
    
    def _calculate_binance_importance(self, title: str) -> int:
        """Calculate importance score for Binance announcements (1-5)"""
        title_lower = title.lower()
        
        # High importance keywords
        if any(keyword in title_lower for keyword in [
            'listing', 'delisting', 'mainnet', 'trading halt', 'maintenance'
        ]):
            return 5
        
        # Medium-high importance
        if any(keyword in title_lower for keyword in [
            'upgrade', 'fork', 'airdrop', 'staking', 'new product'
        ]):
            return 4
        
        # Medium importance
        if any(keyword in title_lower for keyword in [
            'feature', 'update', 'promotion', 'contest'
        ]):
            return 3
        
        # Default importance
        return 2
    
    def _calculate_coinbase_importance(self, title: str) -> int:
        """Calculate importance score for Coinbase announcements (1-5)"""
        title_lower = title.lower()
        
        # High importance - institutional/regulatory
        if any(keyword in title_lower for keyword in [
            'sec', 'regulation', 'institutional', 'custody', 'listing'
        ]):
            return 5
        
        # Medium-high importance
        if any(keyword in title_lower for keyword in [
            'defi', 'nft', 'staking', 'earn', 'pro'
        ]):
            return 4
        
        return 3  # Coinbase posts are generally high quality
    
    def _calculate_okx_importance(self, title: str, announcement_type: str) -> int:
        """Calculate importance score for OKX announcements (1-5)"""
        title_lower = title.lower()
        
        # Critical announcements
        if announcement_type in ['system', 'trading'] or any(keyword in title_lower for keyword in [
            'listing', 'delisting', 'halt', 'maintenance', 'upgrade'
        ]):
            return 5
        
        # High importance
        if any(keyword in title_lower for keyword in [
            'new', 'launch', 'feature', 'product'
        ]):
            return 4
        
        return 3
    
    def _is_crypto_related(self, text: str) -> bool:
        """Check if text content is cryptocurrency related"""
        crypto_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'blockchain',
            'defi', 'nft', 'token', 'coin', 'wallet', 'trading', 'exchange',
            'staking', 'mining', 'altcoin', 'web3', 'dapp', 'smart contract'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in crypto_keywords)
    
    def _extract_tokens_from_text(self, text: str) -> List[str]:
        """Extract cryptocurrency tokens/symbols from text"""
        import re
        
        # Common token patterns
        token_patterns = [
            r'\b[A-Z]{3,6}\b',  # 3-6 letter uppercase (BTC, ETH, etc.)
            r'\$[A-Z]{3,6}\b'   # With dollar sign ($BTC, $ETH)
        ]
        
        tokens = set()
        text_upper = text.upper()
        
        for pattern in token_patterns:
            matches = re.findall(pattern, text_upper)
            tokens.update(matches)
        
        # Filter common false positives
        exclude = {'USD', 'EUR', 'GBP', 'JPY', 'API', 'FAQ', 'NEW', 'GET', 'SET', 'ALL'}
        tokens = [token.replace('$', '') for token in tokens if token not in exclude]
        
        return list(tokens)
    
    async def _deduplicate_announcements(self, announcements: List[ExchangeAnnouncement]) -> List[ExchangeAnnouncement]:
        """Remove duplicate announcements based on content similarity"""
        import hashlib
        
        seen_hashes = set()
        deduplicated = []
        
        for announcement in announcements:
            # Create content hash for deduplication
            content_for_hash = f"{announcement.title}{announcement.exchange}"
            content_hash = hashlib.md5(content_for_hash.encode()).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduplicated.append(announcement)
        
        return deduplicated


class PriceDataService:
    """
    Service for fetching real-time cryptocurrency price data.
    Integrates with news for market impact analysis.
    """
    
    def __init__(self):
        self.session = None
        self.logger = get_service_logger("price_data")
        self.rate_limiter = RateLimiter("price_api_calls", 100, 60)  # 100/minute
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def fetch_token_prices(self, symbols: List[str]) -> List[PriceData]:
        """
        Fetch current prices for specified cryptocurrency symbols.
        Uses CoinGecko API for reliable price data.
        """
        if not symbols:
            return []
        
        await self.rate_limiter.wait_if_needed()
        
        try:
            # CoinGecko API for price data
            symbols_str = ','.join(symbols).lower()
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': symbols_str,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    self.logger.error(
                        "Price API request failed",
                        status=response.status,
                        symbols=symbols
                    )
                    return []
                
                data = await response.json()
                return self._parse_price_data(data)
                
        except Exception as e:
            self.logger.error(
                "Error fetching price data",
                symbols=symbols,
                error=str(e),
                exc_info=True
            )
            return []
    
    def _parse_price_data(self, data: Dict) -> List[PriceData]:
        """Parse price API response into standardized format"""
        price_data_list = []
        
        for symbol, price_info in data.items():
            try:
                price_data = PriceData(
                    symbol=symbol.upper(),
                    price=price_info.get('usd', 0.0),
                    change_24h=price_info.get('usd_24h_change', 0.0),
                    change_percent_24h=price_info.get('usd_24h_change', 0.0),
                    volume_24h=price_info.get('usd_24h_vol', 0.0),
                    last_updated=datetime.utcnow(),
                    exchange="coingecko"
                )
                price_data_list.append(price_data)
                
            except Exception as e:
                self.logger.error(
                    "Error parsing price data",
                    symbol=symbol,
                    error=str(e)
                )
        
        return price_data_list
    
    async def analyze_market_impact(
        self, 
        announcement: ExchangeAnnouncement, 
        price_data: List[PriceData]
    ) -> Dict[str, Any]:
        """
        Analyze potential market impact of an announcement based on price data.
        Returns impact analysis with recommendations.
        """
        try:
            # Find affected tokens in price data
            affected_prices = []
            if announcement.affected_tokens:
                for token in announcement.affected_tokens:
                    for price in price_data:
                        if price.symbol == token.upper():
                            affected_prices.append(price)
                            break
            
            # Calculate impact metrics
            impact_analysis = {
                'announcement_id': f"{announcement.exchange}_{announcement.title[:50]}",
                'affected_token_count': len(affected_prices),
                'high_volatility_tokens': [
                    price.symbol for price in affected_prices 
                    if abs(price.change_percent_24h) > 10
                ],
                'market_cap_impact': 'unknown',  # Would need market cap data
                'sentiment_indicator': self._determine_sentiment(announcement),
                'urgency_level': announcement.importance_score,
                'recommended_alert_level': self._calculate_alert_level(announcement, affected_prices)
            }
            
            self.logger.info(
                "Market impact analysis completed",
                exchange=announcement.exchange,
                affected_tokens=len(affected_prices),
                alert_level=impact_analysis['recommended_alert_level']
            )
            
            return impact_analysis
            
        except Exception as e:
            self.logger.error(
                "Error in market impact analysis",
                announcement_title=announcement.title,
                error=str(e),
                exc_info=True
            )
            return {'error': str(e)}
    
    def _determine_sentiment(self, announcement: ExchangeAnnouncement) -> str:
        """Determine sentiment based on announcement content"""
        title_content = f"{announcement.title} {announcement.content}".lower()
        
        positive_keywords = ['listing', 'launch', 'partnership', 'upgrade', 'integration']
        negative_keywords = ['delisting', 'halt', 'issue', 'problem', 'maintenance']
        
        positive_score = sum(1 for keyword in positive_keywords if keyword in title_content)
        negative_score = sum(1 for keyword in negative_keywords if keyword in title_content)
        
        if positive_score > negative_score:
            return 'positive'
        elif negative_score > positive_score:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_alert_level(
        self, 
        announcement: ExchangeAnnouncement, 
        affected_prices: List[PriceData]
    ) -> str:
        """Calculate recommended alert level based on announcement and price data"""
        
        # Base level on announcement importance
        if announcement.importance_score >= 5:
            base_level = 'critical'
        elif announcement.importance_score >= 4:
            base_level = 'high'
        elif announcement.importance_score >= 3:
            base_level = 'medium'
        else:
            base_level = 'low'
        
        # Adjust based on price volatility
        if affected_prices:
            max_volatility = max(abs(price.change_percent_24h) for price in affected_prices)
            if max_volatility > 20:  # >20% price change
                if base_level in ['low', 'medium']:
                    return 'high'
                elif base_level == 'high':
                    return 'critical'
        
        return base_level