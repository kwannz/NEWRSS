"""
已验证有效的RSS源配置文件
验证日期: 2025-08-31
仅包含通过HTTP和内容验证的RSS源 (17个有效源)
"""

from typing import List, Dict

# ✅ 验证有效的交易所RSS源 (5个)
EXCHANGE_RSS_SOURCES = [
    {
        "url": "https://blog.kraken.com/feed/",
        "name": "Kraken Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 5,
        "language": "en",
        "region": "us"
    },
    {
        "url": "https://blog.gemini.com/rss",
        "name": "Gemini Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 4,
        "language": "en",
        "region": "us"
    },
    {
        "url": "https://blog.cex.io/feed",
        "name": "CEX.IO Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 4,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://changelly.com/blog/feed",
        "name": "Changelly Blog",
        "category": "exchange",
        "source_type": "blog",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://cryptopanic.com/news/rss/",
        "name": "CryptoPanic",
        "category": "exchange",
        "source_type": "aggregator",
        "priority": 4,
        "language": "en",
        "region": "global"
    }
]

# ✅ 验证有效的新闻媒体RSS源 (16个)
CRYPTO_NEWS_SOURCES = [
    {
        "url": "https://cointelegraph.com/rss",
        "name": "Cointelegraph",
        "category": "news",
        "source_type": "rss",
        "priority": 5,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "name": "CoinDesk",
        "category": "news",
        "source_type": "rss",
        "priority": 5,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://decrypt.co/feed",
        "name": "Decrypt",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://www.theblockcrypto.com/rss.xml",
        "name": "The Block",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://news.bitcoin.com/feed/",
        "name": "Bitcoin.com News",
        "category": "bitcoin",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://cryptobriefing.com/feed/",
        "name": "Crypto Briefing",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://beincrypto.com/feed/",
        "name": "BeInCrypto",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://cryptoslate.com/feed/",
        "name": "CryptoSlate",
        "category": "news",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://ambcrypto.com/feed/",
        "name": "AMBCrypto",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://blockonomi.com/feed/",
        "name": "Blockonomi",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://coinjournal.net/feed/",
        "name": "CoinJournal",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://cryptodaily.co.uk/feed",
        "name": "Crypto Daily",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://dailycoin.com/feed/",
        "name": "DailyCoin",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://www.newsbtc.com/feed/",
        "name": "NewsBTC",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://cryptopotato.com/feed/",
        "name": "CryptoPotato",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://bitcoinist.com/feed/",
        "name": "Bitcoinist",
        "category": "bitcoin",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://99bitcoins.com/feed/",
        "name": "99Bitcoins",
        "category": "bitcoin",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://u.today/rss",
        "name": "U.Today",
        "category": "news",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    }
]

# ✅ 验证有效的专业类别RSS源 (2个)
DEFI_NFT_SOURCES = [
    {
        "url": "https://nftnow.com/feed/",
        "name": "NFT Now",
        "category": "nft",
        "source_type": "rss",
        "priority": 3,
        "language": "en",
        "region": "global"
    },
    {
        "url": "https://thedefiant.io/rss",
        "name": "The Defiant",
        "category": "defi",
        "source_type": "rss",
        "priority": 4,
        "language": "en",
        "region": "global"
    }
]

# 空的中文源列表 (待添加有效的中文RSS源)
CHINESE_NEWS_SOURCES = []

# 合并所有验证有效的RSS源
ALL_RSS_SOURCES = EXCHANGE_RSS_SOURCES + CRYPTO_NEWS_SOURCES + DEFI_NFT_SOURCES + CHINESE_NEWS_SOURCES

# 交易所特定关键词（用于紧急新闻检测）
EXCHANGE_URGENT_KEYWORDS = {
    "en": [
        "listing", "delisting", "maintenance", "suspension", "trading halt",
        "new pair", "airdrop", "fork support", "withdrawal suspended",
        "deposit suspended", "security notice", "system upgrade",
        "trading competition", "fee adjustment", "api update",
        "margin trading", "futures launch", "spot trading",
        "trading bot", "algorithmic trading", "leveraged tokens"
    ],
    "zh": [
        "上币", "下架", "维护", "暂停", "交易暂停", 
        "新交易对", "空投", "分叉支持", "提币暂停",
        "充币暂停", "安全提醒", "系统升级",
        "交易大赛", "手续费调整", "API更新",
        "杠杆交易", "期货上线", "现货交易",
        "交易机器人", "算法交易", "杠杆代币"
    ]
}

# 重要性评分权重
IMPORTANCE_WEIGHTS = {
    "exchange_announcement": 3,
    "listing_news": 4,
    "security_alert": 5,
    "regulatory_news": 4,
    "partnership": 2,
    "technical_update": 2,
    "market_analysis": 1
}

def get_sources_by_category(category: str) -> List[Dict]:
    """根据分类获取RSS源"""
    return [source for source in ALL_RSS_SOURCES if source["category"] == category]

def get_sources_by_language(language: str) -> List[Dict]:
    """根据语言获取RSS源"""
    return [source for source in ALL_RSS_SOURCES if source["language"] == language]

def get_high_priority_sources() -> List[Dict]:
    """获取高优先级RSS源"""
    return [source for source in ALL_RSS_SOURCES if source["priority"] >= 4]

def get_all_sources() -> List[Dict]:
    """获取所有验证有效的RSS源"""
    return ALL_RSS_SOURCES

if __name__ == "__main__":
    # Use print for script execution since logging may not be initialized
    from app.core.logging import get_logger
    logger = get_logger("rss_sources_stats")
    
    logger.info(
        "RSS source verification statistics",
        total_sources=len(ALL_RSS_SOURCES),
        exchange_sources=len(EXCHANGE_RSS_SOURCES),
        news_sources=len(CRYPTO_NEWS_SOURCES),
        specialized_sources=len(DEFI_NFT_SOURCES),
        chinese_sources=len(CHINESE_NEWS_SOURCES)
    )