from fastapi import APIRouter, Depends, Query, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import json
from app.core.database import get_db
from app.models.news import NewsItem
from app.services.translator import translator
from app.core.broadcast_utils import broadcast_news, broadcast_urgent
from app.core.rate_limiting import limiter, rate_limit, RateLimitType
from app.core.input_validation import PaginationModel, SearchQueryModel, InputSanitizer
from app.api.auth import get_current_user
from app.models.user import User

def safe_json_loads(data):
    """Safely parse JSON data"""
    if not data:
        return None
    try:
        if isinstance(data, str):
            if data.startswith('[') and data.endswith(']'):
                return json.loads(data)
            else:
                # Handle string list format "['BTC', 'ETH']"
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

class NewsFilterParams(BaseModel):
    """Enhanced news filtering with validation"""
    page: int = Field(default=1, ge=1, le=10000, description="Page number")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    category: Optional[str] = Field(default=None, max_length=50, description="News category")
    source: Optional[str] = Field(default=None, max_length=100, description="News source")
    urgent_only: bool = Field(default=False, description="Show only urgent news")
    min_importance: int = Field(default=1, ge=1, le=5, description="Minimum importance score")
    search: Optional[str] = Field(default=None, max_length=200, description="Search query")
    
    @validator('category')
    def sanitize_category(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_html(v.strip())
    
    @validator('source')
    def sanitize_source(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_html(v.strip())
    
    @validator('search')
    def sanitize_search(cls, v):
        if v is None:
            return v
        return InputSanitizer.sanitize_search_query(v)

class BroadcastRequest(BaseModel):
    """Request model for news broadcasting"""
    news_id: int = Field(..., gt=0, description="News item ID")

@router.get("/", response_model=List[NewsItemResponse])
@limiter.limit("50/minute")  # Rate limit news listing
async def get_news_list(
    request: Request,
    params: NewsFilterParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Get news list with enhanced security and filtering
    
    Includes rate limiting, input validation, and XSS protection
    """
    try:
        query = select(NewsItem).order_by(desc(NewsItem.published_at))
        
        # Apply filters with sanitized input
        if params.category:
            query = query.where(NewsItem.category == params.category)
        if params.source:
            query = query.where(NewsItem.source == params.source)
        if params.urgent_only:
            query = query.where(NewsItem.is_urgent == True)
        if params.min_importance > 1:
            query = query.where(NewsItem.importance_score >= params.min_importance)
        
        # Search functionality with XSS protection
        if params.search:
            search_term = f"%{params.search}%"
            query = query.where(
                NewsItem.title.ilike(search_term) | 
                NewsItem.content.ilike(search_term)
            )
        
        # Apply pagination
        offset = (params.page - 1) * params.limit
        query = query.offset(offset).limit(params.limit)
        
        result = await db.execute(query)
        news_items = result.scalars().all()
        
        # Sanitize output to prevent XSS
        response_items = []
        for item in news_items:
            response_items.append(NewsItemResponse(
                id=item.id,
                title=InputSanitizer.sanitize_html(item.title),
                titleEn=translator.translate_to_english(item.title),
                content=InputSanitizer.sanitize_html(item.content, allow_html=True),
                contentEn=translator.translate_to_english(item.content),
                summary=InputSanitizer.sanitize_html(item.summary) if item.summary else None,
                summaryEn=translator.translate_to_english(item.summary) if item.summary else None,
                url=InputSanitizer.sanitize_url(item.url),
                source=InputSanitizer.sanitize_html(item.source),
                category=item.category,
                publishedAt=item.published_at.isoformat(),
                importanceScore=item.importance_score,
                isUrgent=item.is_urgent,
                marketImpact=item.market_impact,
                sentimentScore=item.sentiment_score,
                keyTokens=safe_json_loads(item.key_tokens),
                keyPrices=safe_json_loads(item.key_prices),
                createdAt=item.created_at.isoformat()
            ))
        
        return response_items
        
    except Exception as e:
        from app.core.security_headers import security_logger
        security_logger.log_security_event(
            "news_listing_error",
            {"error": str(e), "params": params.dict()},
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch news items"
        )

@router.post("/broadcast")
@limiter.limit("10/minute")  # Restrictive rate limit for broadcasting
@rate_limit(RateLimitType.BROADCAST)
async def broadcast_news_item(
    request: Request,
    broadcast_req: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Require authentication
):
    """
    Broadcast news item via WebSocket with authentication
    
    Requires user authentication and has strict rate limiting
    """
    try:
        result = await db.execute(select(NewsItem).where(NewsItem.id == broadcast_req.news_id))
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="News item not found"
            )

        # Create sanitized payload
        payload = NewsItemResponse(
            id=item.id,
            title=InputSanitizer.sanitize_html(item.title),
            titleEn=translator.translate_to_english(item.title),
            content=InputSanitizer.sanitize_html(item.content, allow_html=True),
            contentEn=translator.translate_to_english(item.content),
            summary=InputSanitizer.sanitize_html(item.summary) if item.summary else None,
            summaryEn=translator.translate_to_english(item.summary) if item.summary else None,
            url=InputSanitizer.sanitize_url(item.url),
            source=InputSanitizer.sanitize_html(item.source),
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

        # Broadcast based on urgency
        if item.is_urgent:
            await broadcast_urgent(payload)
            broadcast_type = "urgent_news"
        else:
            await broadcast_news(payload)
            broadcast_type = "new_news"

        # Log broadcast activity
        from app.core.logging import main_logger
        main_logger.info(
            f"News broadcast initiated",
            news_id=item.id,
            broadcast_type=broadcast_type,
            user=current_user.username,
            urgent=item.is_urgent
        )

        return {
            "status": "success",
            "broadcasted": broadcast_type,
            "id": item.id,
            "title": item.title[:50] + "..." if len(item.title) > 50 else item.title
        }
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.security_headers import security_logger
        security_logger.log_security_event(
            "broadcast_error",
            {"error": str(e), "news_id": broadcast_req.news_id},
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast news item"
        )

@router.get("/search")
@limiter.limit("30/minute")  # Rate limit search
async def search_news(
    request: Request,
    search_params: SearchQueryModel = Depends(),
    pagination: PaginationModel = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Search news with enhanced security
    
    Includes input sanitization and rate limiting
    """
    try:
        search_term = f"%{search_params.query}%"
        
        query = select(NewsItem).where(
            NewsItem.title.ilike(search_term) | 
            NewsItem.content.ilike(search_term) |
            NewsItem.summary.ilike(search_term)
        ).order_by(desc(NewsItem.published_at))
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.size
        query = query.offset(offset).limit(pagination.size)
        
        result = await db.execute(query)
        news_items = result.scalars().all()
        
        return {
            "items": [
                NewsItemResponse(
                    id=item.id,
                    title=InputSanitizer.sanitize_html(item.title),
                    titleEn=translator.translate_to_english(item.title),
                    content=InputSanitizer.sanitize_html(item.content, allow_html=True),
                    contentEn=translator.translate_to_english(item.content),
                    summary=InputSanitizer.sanitize_html(item.summary) if item.summary else None,
                    summaryEn=translator.translate_to_english(item.summary) if item.summary else None,
                    url=InputSanitizer.sanitize_url(item.url),
                    source=InputSanitizer.sanitize_html(item.source),
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
            ],
            "pagination": {
                "page": pagination.page,
                "size": pagination.size,
                "total_items": len(news_items)
            },
            "search_query": search_params.query
        }
        
    except Exception as e:
        from app.core.security_headers import security_logger
        security_logger.log_security_event(
            "news_search_error",
            {"error": str(e), "query": search_params.query},
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )

@router.get("/{news_id}", response_model=NewsItemResponse)
@limiter.limit("100/minute")  # Higher rate limit for individual item access
async def get_news_item(
    request: Request,
    news_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get single news item with security enhancements
    
    Includes input validation and XSS protection
    """
    # Validate news_id
    if news_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid news ID"
        )
    
    try:
        result = await db.execute(select(NewsItem).where(NewsItem.id == news_id))
        item = result.scalar_one_or_none()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="News item not found"
            )
        
        return NewsItemResponse(
            id=item.id,
            title=InputSanitizer.sanitize_html(item.title),
            titleEn=translator.translate_to_english(item.title),
            content=InputSanitizer.sanitize_html(item.content, allow_html=True),
            contentEn=translator.translate_to_english(item.content),
            summary=InputSanitizer.sanitize_html(item.summary) if item.summary else None,
            summaryEn=translator.translate_to_english(item.summary) if item.summary else None,
            url=InputSanitizer.sanitize_url(item.url),
            source=InputSanitizer.sanitize_html(item.source),
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
        
    except HTTPException:
        raise
    except Exception as e:
        from app.core.security_headers import security_logger
        security_logger.log_security_event(
            "news_item_error",
            {"error": str(e), "news_id": news_id},
            request=request
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch news item"
        )