"""
Exchange API endpoints for cryptocurrency exchange data and price information.

Provides endpoints for:
- Exchange announcements
- Real-time price data
- Market impact analysis
- Price alerts management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.exchange import (
    ExchangeAnnouncement,
    PriceData,
    MarketImpactAnalysis,
    PriceAlert
)
from app.models.user import User
from app.services.exchange_api_service import ExchangeAPIService, PriceDataService
from app.core.logging import get_service_logger
from pydantic import BaseModel

router = APIRouter()
logger = get_service_logger("exchange_api")


# Pydantic models for request/response
class ExchangeAnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    url: str
    exchange: str
    category: Optional[str]
    published_at: datetime
    importance_score: int
    announcement_type: Optional[str]
    affected_tokens: Optional[List[str]]
    market_impact_level: Optional[str]
    sentiment_indicator: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PriceDataResponse(BaseModel):
    id: int
    symbol: str
    price_usd: float
    change_24h: float
    change_percent_24h: float
    volume_24h: float
    exchange: str
    price_timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class MarketImpactResponse(BaseModel):
    id: int
    impact_score: float
    confidence_level: float
    affected_token_count: int
    high_volatility_tokens: Optional[List[str]]
    recommended_alert_level: str
    sentiment_score: Optional[float]
    analyzed_at: datetime

    class Config:
        from_attributes = True


class PriceAlertCreate(BaseModel):
    token_symbol: str
    alert_type: str  # price_above, price_below, percent_change
    threshold_value: float
    notification_method: str = "telegram"


class PriceAlertResponse(BaseModel):
    id: int
    token_symbol: str
    alert_type: str
    threshold_value: float
    is_active: bool
    notification_method: str
    last_triggered: Optional[datetime]
    trigger_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# Exchange Announcements Endpoints

@router.get("/announcements", response_model=List[ExchangeAnnouncementResponse])
async def get_exchange_announcements(
    exchange: Optional[str] = Query(None, description="Filter by exchange (Binance, Coinbase, OKX)"),
    limit: int = Query(50, le=200, description="Number of announcements to return"),
    offset: int = Query(0, ge=0, description="Number of announcements to skip"),
    importance_min: int = Query(1, ge=1, le=5, description="Minimum importance score"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get exchange announcements with optional filtering.
    
    - **exchange**: Filter by specific exchange
    - **limit**: Maximum number of results
    - **offset**: Skip this many results (for pagination)
    - **importance_min**: Minimum importance score (1-5)
    """
    try:
        # Build query with filters
        query = select(ExchangeAnnouncement).filter(
            ExchangeAnnouncement.importance_score >= importance_min
        )
        
        if exchange:
            query = query.filter(ExchangeAnnouncement.exchange == exchange)
        
        # Order by publication date (newest first) and apply pagination
        query = query.order_by(desc(ExchangeAnnouncement.published_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        announcements = result.scalars().all()
        
        logger.info(
            "Exchange announcements retrieved",
            count=len(announcements),
            exchange=exchange,
            importance_min=importance_min
        )
        
        return announcements
        
    except Exception as e:
        logger.error(
            "Error retrieving exchange announcements",
            error=str(e),
            exchange=exchange,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve announcements")


@router.get("/announcements/{announcement_id}", response_model=ExchangeAnnouncementResponse)
async def get_exchange_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific exchange announcement by ID."""
    try:
        result = await db.execute(
            select(ExchangeAnnouncement).filter(ExchangeAnnouncement.id == announcement_id)
        )
        announcement = result.scalar_one_or_none()
        
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        return announcement
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error retrieving exchange announcement",
            announcement_id=announcement_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve announcement")


@router.post("/announcements/refresh")
async def refresh_exchange_announcements():
    """
    Manually trigger refresh of exchange announcements.
    This endpoint triggers the same process as the scheduled task.
    """
    try:
        from app.tasks.news_crawler import _monitor_exchange_announcements_async
        
        logger.info("Manual exchange announcements refresh triggered")
        result = await _monitor_exchange_announcements_async()
        
        return {
            "status": "success",
            "message": "Exchange announcements refreshed",
            "data": result
        }
        
    except Exception as e:
        logger.error(
            "Error in manual exchange refresh",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to refresh announcements")


# Price Data Endpoints

@router.get("/prices", response_model=List[PriceDataResponse])
async def get_price_data(
    symbols: Optional[str] = Query(None, description="Comma-separated token symbols (e.g., BTC,ETH,ADA)"),
    limit: int = Query(50, le=200, description="Number of price records to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest price data for cryptocurrencies.
    
    - **symbols**: Comma-separated list of token symbols to filter by
    - **limit**: Maximum number of results
    """
    try:
        # Build base query for latest prices
        subquery = select(
            PriceData.symbol,
            func.max(PriceData.price_timestamp).label('latest_timestamp')
        ).group_by(PriceData.symbol).subquery()
        
        query = select(PriceData).join(
            subquery,
            and_(
                PriceData.symbol == subquery.c.symbol,
                PriceData.price_timestamp == subquery.c.latest_timestamp
            )
        )
        
        # Filter by symbols if provided
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(',')]
            query = query.filter(PriceData.symbol.in_(symbol_list))
        
        # Apply limit and order by symbol
        query = query.order_by(PriceData.symbol).limit(limit)
        
        result = await db.execute(query)
        price_data = result.scalars().all()
        
        logger.info(
            "Price data retrieved",
            count=len(price_data),
            symbols=symbols
        )
        
        return price_data
        
    except Exception as e:
        logger.error(
            "Error retrieving price data",
            symbols=symbols,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve price data")


@router.post("/prices/refresh")
async def refresh_price_data(
    symbols: Optional[List[str]] = None
):
    """
    Manually refresh price data for specified symbols.
    If no symbols provided, refreshes top cryptocurrencies.
    """
    try:
        # Default symbols if none provided
        if not symbols:
            symbols = ['bitcoin', 'ethereum', 'cardano', 'polkadot', 'chainlink', 'litecoin']
        
        async with PriceDataService() as price_service:
            price_data = await price_service.fetch_token_prices(symbols)
        
        # Save to database
        from app.core.database import get_db
        from app.models.exchange import PriceData as PriceDataModel
        
        saved_count = 0
        async for session in get_db():
            try:
                for price in price_data:
                    db_price = PriceDataModel(
                        symbol=price.symbol,
                        price_usd=price.price,
                        change_24h=price.change_24h,
                        change_percent_24h=price.change_percent_24h,
                        volume_24h=price.volume_24h,
                        exchange=price.exchange,
                        data_source="api",
                        price_timestamp=price.last_updated
                    )
                    session.add(db_price)
                    saved_count += 1
                
                await session.commit()
                break
                
            except Exception as e:
                logger.error(
                    "Database error saving price data",
                    error=str(e),
                    exc_info=True
                )
                await session.rollback()
                raise
        
        logger.info(
            "Price data refreshed manually",
            symbols=symbols,
            saved_count=saved_count
        )
        
        return {
            "status": "success",
            "message": f"Price data refreshed for {len(symbols)} symbols",
            "saved_count": saved_count,
            "symbols": symbols
        }
        
    except Exception as e:
        logger.error(
            "Error in manual price refresh",
            symbols=symbols,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to refresh price data")


# Market Impact Analysis Endpoints

@router.get("/market-impact", response_model=List[MarketImpactResponse])
async def get_market_impact_analyses(
    limit: int = Query(50, le=200, description="Number of analyses to return"),
    alert_level: Optional[str] = Query(None, description="Filter by alert level (low, medium, high, critical)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get market impact analyses with optional filtering.
    
    - **limit**: Maximum number of results
    - **alert_level**: Filter by recommended alert level
    """
    try:
        query = select(MarketImpactAnalysis)
        
        if alert_level:
            query = query.filter(MarketImpactAnalysis.recommended_alert_level == alert_level)
        
        query = query.order_by(desc(MarketImpactAnalysis.analyzed_at)).limit(limit)
        
        result = await db.execute(query)
        analyses = result.scalars().all()
        
        logger.info(
            "Market impact analyses retrieved",
            count=len(analyses),
            alert_level=alert_level
        )
        
        return analyses
        
    except Exception as e:
        logger.error(
            "Error retrieving market impact analyses",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve market impact analyses")


# Price Alerts Management

@router.post("/price-alerts", response_model=PriceAlertResponse)
async def create_price_alert(
    alert: PriceAlertCreate,
    user_id: int,  # In production, this would come from JWT token
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new price alert for a user.
    
    - **token_symbol**: Symbol to monitor (e.g., BTC, ETH)
    - **alert_type**: Type of alert (price_above, price_below, percent_change)
    - **threshold_value**: Threshold value for the alert
    - **notification_method**: How to notify (telegram, websocket, both)
    """
    try:
        # Check if user exists
        user_result = await db.execute(select(User).filter(User.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create new price alert
        new_alert = PriceAlert(
            user_id=user_id,
            token_symbol=alert.token_symbol.upper(),
            alert_type=alert.alert_type,
            threshold_value=alert.threshold_value,
            notification_method=alert.notification_method,
            is_active=True
        )
        
        db.add(new_alert)
        await db.commit()
        await db.refresh(new_alert)
        
        logger.info(
            "Price alert created",
            user_id=user_id,
            token_symbol=alert.token_symbol,
            alert_type=alert.alert_type,
            threshold=alert.threshold_value
        )
        
        return new_alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error creating price alert",
            user_id=user_id,
            token_symbol=alert.token_symbol,
            error=str(e),
            exc_info=True
        )
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create price alert")


@router.get("/price-alerts", response_model=List[PriceAlertResponse])
async def get_user_price_alerts(
    user_id: int,  # In production, this would come from JWT token
    active_only: bool = Query(True, description="Only return active alerts"),
    db: AsyncSession = Depends(get_db)
):
    """Get all price alerts for a user."""
    try:
        query = select(PriceAlert).filter(PriceAlert.user_id == user_id)
        
        if active_only:
            query = query.filter(PriceAlert.is_active == True)
        
        query = query.order_by(desc(PriceAlert.created_at))
        
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        return alerts
        
    except Exception as e:
        logger.error(
            "Error retrieving user price alerts",
            user_id=user_id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve price alerts")


@router.delete("/price-alerts/{alert_id}")
async def delete_price_alert(
    alert_id: int,
    user_id: int,  # In production, this would come from JWT token
    db: AsyncSession = Depends(get_db)
):
    """Delete a price alert."""
    try:
        # Find the alert and verify ownership
        result = await db.execute(
            select(PriceAlert).filter(
                and_(
                    PriceAlert.id == alert_id,
                    PriceAlert.user_id == user_id
                )
            )
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Price alert not found")
        
        await db.delete(alert)
        await db.commit()
        
        logger.info(
            "Price alert deleted",
            alert_id=alert_id,
            user_id=user_id,
            token_symbol=alert.token_symbol
        )
        
        return {"status": "success", "message": "Price alert deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting price alert",
            alert_id=alert_id,
            user_id=user_id,
            error=str(e),
            exc_info=True
        )
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete price alert")


# Statistics and Summary Endpoints

@router.get("/stats/summary")
async def get_exchange_stats_summary(
    days: int = Query(7, ge=1, le=30, description="Number of days to include in statistics"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics for exchange data.
    
    Returns counts and metrics for the specified time period.
    """
    try:
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Exchange announcements count
        announcements_result = await db.execute(
            select(func.count(ExchangeAnnouncement.id)).filter(
                ExchangeAnnouncement.created_at >= since_date
            )
        )
        announcements_count = announcements_result.scalar()
        
        # Price data points count
        price_data_result = await db.execute(
            select(func.count(PriceData.id)).filter(
                PriceData.created_at >= since_date
            )
        )
        price_data_count = price_data_result.scalar()
        
        # Market impact analyses count
        analyses_result = await db.execute(
            select(func.count(MarketImpactAnalysis.id)).filter(
                MarketImpactAnalysis.analyzed_at >= since_date
            )
        )
        analyses_count = analyses_result.scalar()
        
        # Active price alerts count
        alerts_result = await db.execute(
            select(func.count(PriceAlert.id)).filter(
                PriceAlert.is_active == True
            )
        )
        alerts_count = alerts_result.scalar()
        
        # High importance announcements
        high_importance_result = await db.execute(
            select(func.count(ExchangeAnnouncement.id)).filter(
                and_(
                    ExchangeAnnouncement.created_at >= since_date,
                    ExchangeAnnouncement.importance_score >= 4
                )
            )
        )
        high_importance_count = high_importance_result.scalar()
        
        summary = {
            "period_days": days,
            "since_date": since_date.isoformat(),
            "announcements_total": announcements_count,
            "announcements_high_importance": high_importance_count,
            "price_data_points": price_data_count,
            "market_analyses": analyses_count,
            "active_price_alerts": alerts_count,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "Exchange stats summary generated",
            days=days,
            **summary
        )
        
        return summary
        
    except Exception as e:
        logger.error(
            "Error generating exchange stats summary",
            days=days,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to generate statistics summary")