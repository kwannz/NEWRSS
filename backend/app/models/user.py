from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)  # Made nullable for Telegram-only users
    email = Column(String, unique=True, index=True, nullable=True)  # Made nullable for Telegram-only users
    hashed_password = Column(String, nullable=True)  # Made nullable for Telegram-only users
    telegram_id = Column(String, unique=True, index=True, nullable=True)
    telegram_username = Column(String, nullable=True)
    telegram_first_name = Column(String, nullable=True)
    telegram_last_name = Column(String, nullable=True)
    telegram_language_code = Column(String, default="en")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_telegram_user = Column(Boolean, default=False)
    urgent_notifications = Column(Boolean, default=True)
    daily_digest = Column(Boolean, default=False)
    digest_time = Column(String, default="09:00")  # Time for daily digest (HH:MM)
    min_importance_score = Column(Integer, default=1)  # Minimum importance for notifications
    max_daily_notifications = Column(Integer, default=10)  # Max notifications per day
    timezone = Column(String, default="UTC")
    push_settings = Column(Text, nullable=True)  # JSON string for custom settings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    subscriptions = relationship("UserSubscription", back_populates="user")
    categories = relationship("UserCategory", back_populates="user")