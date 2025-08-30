"""
最终验证有效的RSS源配置文件
验证日期: 2025-08-31
成功率: 73.9% (17/23个源通过验证)
"""

from typing import List, Dict

# ✅ 验证通过的交易所RSS源 (5个)
VERIFIED_EXCHANGE_SOURCES = [
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

# ✅ 验证通过的新闻媒体RSS源 (10个)
VERIFIED_NEWS_SOURCES = [
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

# ✅ 验证通过的专业类别RSS源 (2个)
VERIFIED_SPECIALIZED_SOURCES = [
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

# 合并所有验证有效的RSS源
ALL_VERIFIED_RSS_SOURCES = VERIFIED_EXCHANGE_SOURCES + VERIFIED_NEWS_SOURCES + VERIFIED_SPECIALIZED_SOURCES

# ❌ 验证失败的RSS源记录
INVALID_RSS_SOURCES = [
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/feed", "reason": "HTTP 403"},
    {"name": "金色财经", "url": "https://www.jinse.cn/rss", "reason": "HTTP 404"},
    {"name": "巴比特", "url": "https://www.8btc.cn/rss", "reason": "连接超时"},
    {"name": "币世界", "url": "https://www.bishijie.com/feed", "reason": "DNS解析失败"},
    {"name": "链节点", "url": "https://www.chainnode.com/rss", "reason": "连接被拒绝"},
    {"name": "DeFi Prime", "url": "https://defiprime.com/rss.xml", "reason": "HTTP 404"}
]

# 交易所特定关键词（用于紧急新闻检测）
EXCHANGE_URGENT_KEYWORDS = {
    "en": [
        "listing", "delisting", "maintenance", "suspension", "trading halt",
        "new pair", "airdrop", "fork support", "withdrawal suspended",
        "deposit suspended", "security notice", "system upgrade",
        "trading competition", "fee adjustment", "api update",
        "margin trading", "futures launch", "spot trading"
    ],
    "zh": [
        "上币", "下架", "维护", "暂停", "交易暂停", 
        "新交易对", "空投", "分叉支持", "提币暂停",
        "充币暂停", "安全提醒", "系统升级",
        "交易大赛", "手续费调整", "API更新"
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

def get_all_sources() -> List[Dict]:
    """获取所有验证有效的RSS源"""
    return ALL_VERIFIED_RSS_SOURCES

def get_high_priority_sources() -> List[Dict]:
    """获取高优先级RSS源（优先级4+）"""
    return [source for source in ALL_VERIFIED_RSS_SOURCES if source["priority"] >= 4]

def get_sources_by_category(category: str) -> List[Dict]:
    """根据分类获取RSS源"""
    return [source for source in ALL_VERIFIED_RSS_SOURCES if source["category"] == category]

if __name__ == "__main__":
    print("📊 验证有效的RSS源统计:")
    print(f"   ✅ 总计: {len(ALL_VERIFIED_RSS_SOURCES)} 个")
    print(f"   🏦 交易所: {len(VERIFIED_EXCHANGE_SOURCES)} 个")
    print(f"   📰 新闻媒体: {len(VERIFIED_NEWS_SOURCES)} 个")
    print(f"   🎨 专业类别: {len(VERIFIED_SPECIALIZED_SOURCES)} 个")
    print(f"   ❌ 失效源: {len(INVALID_RSS_SOURCES)} 个")
    print(f"   🎯 验证时间: 2025-08-31")
    print(f"   📈 成功率: 73.9%")