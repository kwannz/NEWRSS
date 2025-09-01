from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from pydantic import BaseModel
import json
from app.core.database import get_db
from app.models.news import NewsItem
from app.services.translator import translator
from app.core.broadcast_utils import broadcast_news, broadcast_urgent

def safe_json_loads(data):
    """安全解析JSON数据"""
    if not data:
        return None
    try:
        if isinstance(data, str):
            if data.startswith('[') and data.endswith(']'):
                return json.loads(data)
            else:
                # 处理字符串列表格式 "['BTC', 'ETH']"
                import ast
                return ast.literal_eval(data)
        return data
    except:
        return None

router = APIRouter(prefix="/news", tags=["news"])

class NewsItemResponse(BaseModel):
    id: int
    title: str
    titleEn: Optional[str] = None
    content: str
    contentEn: Optional[str] = None
    summary: Optional[str] = None
    summaryEn: Optional[str] = None
    url: str
    source: str
    category: Optional[str] = None
    publishedAt: str
    importanceScore: int
    isUrgent: bool
    marketImpact: int
    sentimentScore: Optional[float] = None
    keyTokens: Optional[List[str]] = None
    keyPrices: Optional[List[str]] = None
    createdAt: str

    class Config:
        from_attributes = True

@router.get("/", response_model=List[NewsItemResponse])
async def get_news_list(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    source: Optional[str] = None,
    urgent_only: bool = False,
    min_importance: int = Query(1, ge=1, le=5),
    db: AsyncSession = Depends(get_db)
):
    query = select(NewsItem).order_by(desc(NewsItem.published_at))
    
    if category:
        query = query.where(NewsItem.category == category)
    if source:
        query = query.where(NewsItem.source == source)
    if urgent_only:
        query = query.where(NewsItem.is_urgent == True)
    if min_importance > 1:
        query = query.where(NewsItem.importance_score >= min_importance)
    
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    news_items = result.scalars().all()
    
    return [
        NewsItemResponse(
            id=item.id,
            title=item.title,
            titleEn=translator.translate_to_english(item.title),
            content=item.content,
            contentEn=translator.translate_to_english(item.content),
            summary=item.summary,
            summaryEn=translator.translate_to_english(item.summary) if item.summary else None,
            url=item.url,
            source=item.source,
            category=item.category,
            publishedAt=item.published_at.isoformat(),
            importanceScore=item.importance_score,
            isUrgent=item.is_urgent,
            marketImpact=item.market_impact,
            sentimentScore=item.sentiment_score,
            keyTokens=safe_json_loads(item.key_tokens),
            keyPrices=safe_json_loads(item.key_prices),
            createdAt=item.created_at.isoformat()
        )
        for item in news_items
    ]

@router.post("/broadcast")
async def broadcast_news_item(
    news_id: int,
    db: AsyncSession = Depends(get_db)
):
    """根据已有 `news_id` 触发实时推送，便于联调前端WebSocket显示。

    - 非紧急新闻: 发送 `new_news`
    - 紧急新闻: 发送 `urgent_news`
    """
    result = await db.execute(select(NewsItem).where(NewsItem.id == news_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")

    payload = NewsItemResponse(
        id=item.id,
        title=item.title,
        titleEn=translator.translate_to_english(item.title),
        content=item.content,
        contentEn=translator.translate_to_english(item.content),
        summary=item.summary,
        summaryEn=translator.translate_to_english(item.summary) if item.summary else None,
        url=item.url,
        source=item.source,
        category=item.category,
        publishedAt=item.published_at.isoformat(),
        importanceScore=item.importance_score,
        isUrgent=item.is_urgent,
        marketImpact=item.market_impact,
        sentimentScore=item.sentiment_score,
        keyTokens=safe_json_loads(item.key_tokens),
        keyPrices=safe_json_loads(item.key_prices),
        createdAt=item.created_at.isoformat()
    ).model_dump()

    if item.is_urgent:
        await broadcast_urgent(payload)
    else:
        await broadcast_news(payload)

    return {"status": "ok", "broadcasted": "urgent_news" if item.is_urgent else "new_news", "id": item.id}

@router.get("/{news_id}", response_model=NewsItemResponse)
async def get_news_item(
    news_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(NewsItem).where(NewsItem.id == news_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    
    return NewsItemResponse(
        id=item.id,
        title=item.title,
        titleEn=translator.translate_to_english(item.title),
        content=item.content,
        contentEn=translator.translate_to_english(item.content),
        summary=item.summary,
        summaryEn=translator.translate_to_english(item.summary) if item.summary else None,
        url=item.url,
        source=item.source,
        category=item.category,
        publishedAt=item.published_at.isoformat(),
        importanceScore=item.importance_score,
        isUrgent=item.is_urgent,
        marketImpact=item.market_impact,
        sentimentScore=item.sentiment_score,
        keyTokens=safe_json_loads(item.key_tokens),
        keyPrices=safe_json_loads(item.key_prices),
        createdAt=item.created_at.isoformat()
    )