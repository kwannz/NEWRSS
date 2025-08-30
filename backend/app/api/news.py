from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models.news import NewsItem
from app.api.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/news", tags=["news"])

class NewsItemResponse(BaseModel):
    id: int
    title: str
    content: str
    summary: Optional[str] = None
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
            content=item.content,
            summary=item.summary,
            url=item.url,
            source=item.source,
            category=item.category,
            publishedAt=item.published_at.isoformat(),
            importanceScore=item.importance_score,
            isUrgent=item.is_urgent,
            marketImpact=item.market_impact,
            sentimentScore=item.sentiment_score,
            keyTokens=eval(item.key_tokens) if item.key_tokens else None,
            keyPrices=eval(item.key_prices) if item.key_prices else None,
            createdAt=item.created_at.isoformat()
        )
        for item in news_items
    ]

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
        content=item.content,
        summary=item.summary,
        url=item.url,
        source=item.source,
        category=item.category,
        publishedAt=item.published_at.isoformat(),
        importanceScore=item.importance_score,
        isUrgent=item.is_urgent,
        marketImpact=item.market_impact,
        sentimentScore=item.sentiment_score,
        keyTokens=eval(item.key_tokens) if item.key_tokens else None,
        keyPrices=eval(item.key_prices) if item.key_prices else None,
        createdAt=item.created_at.isoformat()
    )