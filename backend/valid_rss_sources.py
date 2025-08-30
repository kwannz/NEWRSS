"""
验证有效的RSS源配置
基于2025-08-31验证结果，仅包含测试通过的RSS源
"""

from typing import List, Dict

# 验证有效的交易所RSS源
VALID_EXCHANGE_RSS_SOURCES = [
    {
        "url": "https://blog.kraken.com/feed/",
        "name": "Kraken Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 5,
        "language": "en",
        "region": "us",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://blog.gemini.com/rss",
        "name": "Gemini Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 4,
        "language": "en",
        "region": "us",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://blog.cex.io/feed",
        "name": "CEX.IO Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 4,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://changelly.com/blog/feed",
        "name": "Changelly Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 3,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://cryptopanic.com/news/rss/",
        "name": "CryptoPanic",
        "category": "exchange",
        "source_type": "aggregator",
        "priority": 4,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    }
]

# 验证有效的加密货币新闻源
VALID_CRYPTO_NEWS_SOURCES = [
    {
        "url": "https://cointelegraph.com/rss",
        "name": "Cointelegraph",
        "category": "news",
        "source_type": "rss",
        "priority": 5,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "name": "CoinDesk",
        "category": "news",
        "source_type": "rss",
        "priority": 5,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://decrypt.co/feed",
        "name": "Decrypt",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://www.theblockcrypto.com/rss.xml",
        "name": "The Block",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://news.bitcoin.com/feed/",
        "name": "Bitcoin.com News",
        "category": "bitcoin",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://www.newsbtc.com/feed/",
        "name": "NewsBTC",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://cryptopotato.com/feed/",
        "name": "CryptoPotato",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://bitcoinist.com/feed/",
        "name": "Bitcoinist",
        "category": "bitcoin",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://99bitcoins.com/feed/",
        "name": "99Bitcoins",
        "category": "bitcoin",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://u.today/rss",
        "name": "U.Today",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    }
]

# 验证有效的专业分类源
VALID_SPECIALIZED_SOURCES = [
    {
        "url": "https://nftnow.com/feed/",
        "name": "NFT Now",
        "category": "nft",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    },
    {
        "url": "https://thedefiant.io/rss",
        "name": "The Defiant",
        "category": "defi",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global",
        "status": "verified_2025_08_31"
    }
]

# 有效的中文RSS源 (通过RSSHub)
VALID_CHINESE_RSS_SOURCES = [
    {
        "url": "https://rsshub.app/jinse/lives",
        "name": "金色财经快讯",
        "category": "news",
        "source_type": "rss",
        "priority": 5,
        "language": "zh",
        "region": "cn",
        "status": "verified_2025_08_31_rsshub"
    },
    {
        "url": "https://rsshub.app/jinse/timeline",
        "name": "金色财经深度",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "zh",
        "region": "cn",
        "status": "verified_2025_08_31_rsshub"
    },
    {
        "url": "https://cointelegraphcn.com/rss",
        "name": "Cointelegraph中文",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "zh",
        "region": "cn",
        "status": "verified_2025_08_31"
    }
]

# 合并所有有效RSS源
ALL_VALID_RSS_SOURCES = VALID_EXCHANGE_RSS_SOURCES + VALID_CRYPTO_NEWS_SOURCES + VALID_SPECIALIZED_SOURCES + VALID_CHINESE_RSS_SOURCES

# RSS源统计
RSS_STATS = {
    "total_valid": len(ALL_VALID_RSS_SOURCES),
    "exchanges": len(VALID_EXCHANGE_RSS_SOURCES),
    "news": len(VALID_CRYPTO_NEWS_SOURCES),
    "specialized": len(VALID_SPECIALIZED_SOURCES),
    "chinese": len(VALID_CHINESE_RSS_SOURCES),
    "validation_date": "2025-08-31",
    "success_rate": "85.0%"  # 更新成功率 (17+3)/23*100
}

def get_valid_sources() -> List[Dict]:
    """获取所有验证有效的RSS源"""
    return ALL_VALID_RSS_SOURCES

def get_sources_by_priority(min_priority: int = 4) -> List[Dict]:
    """获取高优先级的有效RSS源"""
    return [source for source in ALL_VALID_RSS_SOURCES if source["priority"] >= min_priority]

def get_high_reliability_sources() -> List[Dict]:
    """获取最可靠的RSS源（优先级5）"""
    return [source for source in ALL_VALID_RSS_SOURCES if source["priority"] == 5]

if __name__ == "__main__":
    print("📊 有效RSS源统计:")
    print(f"   总计: {RSS_STATS['total_valid']} 个")
    print(f"   交易所: {RSS_STATS['exchanges']} 个")
    print(f"   新闻媒体: {RSS_STATS['news']} 个")
    print(f"   专业类别: {RSS_STATS['specialized']} 个")
    print(f"   验证时间: {RSS_STATS['validation_date']}")
    print(f"   成功率: {RSS_STATS['success_rate']}")