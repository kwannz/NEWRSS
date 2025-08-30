from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.sql import func
from app.core.database import Base

class NewsItem(Base):
    __tablename__ = "news_items"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # AI generated summary
    url = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    importance_score = Column(Integer, default=1)  # 1-5 scale
    is_urgent = Column(Boolean, default=False)
    market_impact = Column(Integer, default=1)  # 1-5 scale
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    key_tokens = Column(Text, nullable=True)  # JSON array of extracted tokens
    key_prices = Column(Text, nullable=True)  # JSON array of extracted prices
    is_processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class NewsSource(Base):
    __tablename__ = "news_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False)  # rss, api, telegram, etc.
    category = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    fetch_interval = Column(Integer, default=30)  # seconds
    last_fetched = Column(DateTime(timezone=True), nullable=True)
    priority = Column(Integer, default=1)  # Higher number = higher priority
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())