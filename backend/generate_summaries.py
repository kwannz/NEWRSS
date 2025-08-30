import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.core.database import engine, Base
from app.models.news import NewsItem
from app.services.ai_analyzer import AINewsAnalyzer
from sqlalchemy import select, update

async def generate_summaries():
    """为所有新闻生成摘要"""
    print("正在为新闻生成摘要...")
    
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
    
    async with SessionLocal() as session:
        # 获取所有新闻的基本信息
        result = await session.execute(
            select(NewsItem.id, NewsItem.title, NewsItem.content, NewsItem.summary)
            .where((NewsItem.summary == None) | (NewsItem.summary == ""))
        )
        news_rows = result.fetchall()
        
        if not news_rows:
            print("所有新闻都已有摘要")
            return
        
        print(f"找到 {len(news_rows)} 条需要生成摘要的新闻")
        
        # 批量处理
        for i, row in enumerate(news_rows):
            try:
                news_id, title, content, current_summary = row
                
                # 清理HTML标签
                import re
                content_clean = re.sub(r'<[^>]+>', '', content)
                content_clean = re.sub(r'\s+', ' ', content_clean).strip()
                
                # 生成简洁摘要
                sentences = content_clean.split('.')[:2]
                summary = '. '.join(s.strip() for s in sentences if s.strip()).strip()
                
                if len(summary) > 200:
                    summary = summary[:200] + '...'
                elif len(summary) < 20:
                    summary = title[:100] + '...'
                
                # 提取代币信息
                tokens = extract_tokens_from_text(f"{title} {content}")
                
                # 更新数据库
                await session.execute(
                    update(NewsItem)
                    .where(NewsItem.id == news_id)
                    .values(
                        summary=summary,
                        key_tokens=str(tokens) if tokens else None,
                        is_processed=True
                    )
                )
                
                if (i + 1) % 10 == 0:
                    await session.commit()
                    print(f"已处理 {i + 1}/{len(news_rows)} 条新闻")
            
            except Exception as e:
                print(f"处理新闻 {news_id if 'news_id' in locals() else 'unknown'} 时出错: {e}")
                continue
        
        await session.commit()
        print(f"完成! 共处理 {len(news_rows)} 条新闻")

def extract_tokens_from_text(text):
    """从文本中提取代币符号"""
    import re
    
    # 扩展的代币列表
    tokens = [
        'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'XRP', 'SOL', 'ADA', 'DOGE', 'MATIC', 
        'DOT', 'AVAX', 'LINK', 'LTC', 'BCH', 'FIL', 'ETC', 'XLM', 'VET', 'TRX',
        'ALGO', 'ATOM', 'XTZ', 'EOS', 'IOTA', 'NEO', 'WAVES', 'ZEC', 'DASH', 'XMR',
        'THETA', 'COMP', 'UNI', 'AAVE', 'MKR', 'YFI', 'SNX', 'CRV', 'BAL', 'SUSHI',
        'RUNE', 'CAKE', 'ALPHA', 'NEAR', 'FTM', 'ONE', 'HBAR', 'ENJ', 'MANA', 'SAND',
        'CHZ', 'BAT', 'ZRX', 'KNC', 'LRC', 'REN', 'STORJ', 'GRT', 'BAND', 'OCEAN',
        'PENGU', 'PUMP', 'HYPE', 'SUI', 'OP', 'ARB', 'APT', 'ICP', 'FLOW', 'EGLD',
        'MINA', 'ROSE', 'KAVA', 'CELO', 'ANKR', 'SKL', 'NKN', 'RVN', 'ZIL', 'ICX'
    ]
    
    found_tokens = []
    text_upper = text.upper()
    
    for token in tokens:
        # 使用单词边界确保完整匹配
        pattern = r'\b' + re.escape(token) + r'\b'
        if re.search(pattern, text_upper):
            found_tokens.append(token)
    
    return found_tokens

if __name__ == "__main__":
    asyncio.run(generate_summaries())