"""
Database models for exchange API integration and price data.

Models:
- ExchangeAnnouncement: Store exchange-specific announcements
- PriceData: Real-time cryptocurrency price information
- MarketImpactAnalysis: Analysis results for news-price correlation
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExchangeAnnouncement(Base):
    """Exchange-specific announcement data"""
    __tablename__ = "exchange_announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    url = Column(String, unique=True, index=True, nullable=False)
    exchange = Column(String, index=True, nullable=False)  # Binance, Coinbase, OKX
    category = Column(String, index=True, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    importance_score = Column(Integer, default=1)  # 1-5 scale
    is_processed = Column(Boolean, default=False)
    announcement_type = Column(String, nullable=True)  # blog_post, exchange_announcement, etc.
    
    # Market impact fields
    affected_tokens = Column(JSON, nullable=True)  # Array of token symbols
    market_impact_level = Column(String, nullable=True)  # low, medium, high, critical
    sentiment_indicator = Column(String, nullable=True)  # positive, negative, neutral
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    market_analyses = relationship("MarketImpactAnalysis", back_populates="announcement")


class PriceData(Base):
    """Real-time cryptocurrency price data"""
    __tablename__ = "price_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)  # BTC, ETH, etc.
    price_usd = Column(Float, nullable=False)
    change_24h = Column(Float, default=0.0)
    change_percent_24h = Column(Float, default=0.0)
    volume_24h = Column(Float, default=0.0)
    market_cap = Column(Float, nullable=True)
    
    # Data source information
    exchange = Column(String, nullable=False)  # coingecko, binance, etc.
    data_source = Column(String, nullable=False)  # api, websocket
    
    # Timestamps
    price_timestamp = Column(DateTime(timezone=True), nullable=False)  # When price was recorded
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Index for efficient queries
    __table_args__ = (
        {'mysql_charset': 'utf8mb4'},
    )


class MarketImpactAnalysis(Base):
    """Analysis of market impact from news/announcements"""
    __tablename__ = "market_impact_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    announcement_id = Column(Integer, ForeignKey("exchange_announcements.id"), nullable=True)
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=True)
    
    # Analysis results
    impact_score = Column(Float, default=0.0)  # 0.0 to 1.0
    confidence_level = Column(Float, default=0.0)  # 0.0 to 1.0
    affected_token_count = Column(Integer, default=0)
    high_volatility_tokens = Column(JSON, nullable=True)  # Array of volatile tokens
    
    # Market metrics
    price_change_correlation = Column(Float, nullable=True)  # -1.0 to 1.0
    volume_spike_detected = Column(Boolean, default=False)
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    
    # Alert recommendations
    recommended_alert_level = Column(String, default="low")  # low, medium, high, critical
    alert_reasoning = Column(Text, nullable=True)
    
    # Analysis metadata
    analysis_version = Column(String, default="1.0")
    processing_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    announcement = relationship("ExchangeAnnouncement", back_populates="market_analyses")


class PriceAlert(Base):
    """User-configured price alerts for tokens"""
    __tablename__ = "price_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_symbol = Column(String, nullable=False, index=True)
    
    # Alert conditions
    alert_type = Column(String, nullable=False)  # price_above, price_below, percent_change
    threshold_value = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Alert settings
    notification_method = Column(String, default="telegram")  # telegram, websocket, both
    cooldown_minutes = Column(Integer, default=60)  # Minimum time between alerts
    
    # Tracking
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ExchangeAPIMetrics(Base):
    """Track exchange API performance and rate limiting"""
    __tablename__ = "exchange_api_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String, nullable=False, index=True)
    endpoint = Column(String, nullable=False)
    
    # Performance metrics
    response_time_ms = Column(Integer, nullable=False)
    success = Column(Boolean, nullable=False)
    http_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Rate limiting info
    rate_limit_remaining = Column(Integer, nullable=True)
    rate_limit_reset = Column(DateTime(timezone=True), nullable=True)
    
    # Data quality
    records_fetched = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    duplicates_found = Column(Integer, default=0)
    
    # Timestamp
    requested_at = Column(DateTime(timezone=True), server_default=func.now())