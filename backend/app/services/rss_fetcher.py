import aiohttp
import asyncio
from typing import List, Dict
import feedparser
from datetime import datetime
import hashlib
from app.core.redis import get_redis

class RSSFetcher:
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_feed(self, url: str, source_name: str = None) -> List[Dict]:
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    print(f"Error fetching {url}: HTTP {response.status}")
                    return []
                
                content = await response.text()
                feed = feedparser.parse(content)
                
                if feed.bozo:
                    print(f"Warning: Feed {url} may have parsing issues")
                
                items = []
                for entry in feed.entries:
                    # Create unique hash for deduplication
                    content_hash = hashlib.md5(
                        f"{entry.get('title', '')}{entry.get('link', '')}".encode()
                    ).hexdigest()
                    
                    published_at = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published_at = datetime(*entry.published_parsed[:6])
                        except (TypeError, ValueError):
                            published_at = datetime.now()
                    else:
                        published_at = datetime.now()
                    
                    item = {
                        'title': entry.get('title', 'No Title'),
                        'content': entry.get('summary', entry.get('description', '')),
                        'url': entry.get('link', ''),
                        'source': source_name or feed.feed.get('title', 'Unknown'),
                        'published_at': published_at,
                        'content_hash': content_hash,
                        'raw_entry': entry
                    }
                    items.append(item)
                
                return items
        except asyncio.TimeoutError:
            print(f"Timeout fetching {url}")
            return []
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return []
    
    async def fetch_multiple_feeds(self, sources: List[Dict[str, str]]) -> List[Dict]:
        """
        sources format: [{"url": "...", "name": "...", "category": "..."}, ...]
        """
        tasks = [
            self.fetch_feed(source["url"], source.get("name"))
            for source in sources
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_items = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                # Add category and source info
                for item in result:
                    item["category"] = sources[i].get("category", "general")
                all_items.extend(result)
            elif isinstance(result, Exception):
                print(f"Error processing source {sources[i]['url']}: {result}")
        
        return all_items
    
    async def is_duplicate(self, content_hash: str) -> bool:
        """Check if content already exists using Redis cache"""
        redis = await get_redis()
        exists = await redis.exists(f"news:hash:{content_hash}")
        if not exists:
            # Cache for 24 hours
            await redis.setex(f"news:hash:{content_hash}", 86400, "1")
            return False
        return True