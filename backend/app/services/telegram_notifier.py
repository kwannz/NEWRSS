from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.services.telegram_bot import TelegramBot
from app.models.user import User
from app.models.news import NewsItem
from app.core.settings import settings
from app.core.logging import get_service_logger
from app.core.database import SessionLocal
from app.repositories.user_repository import UserRepository
from sqlalchemy import select, and_
import openai
import json
import re

class TelegramNotifier:
    def __init__(self):
        self.bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
        self.logger = get_service_logger("telegram_notifier")
    
    async def notify_urgent_news(self, news_item_dict: dict):
        """推送紧急新闻"""
        try:
            importance_score = news_item_dict.get('importance_score', 3)
            category = news_item_dict.get('category')
            
            # Get users who should receive this notification
            user_ids = await self.get_users_for_notification(
                importance_score=importance_score,
                category=category,
                urgent_only=True
            )
            
            if user_ids:
                self.logger.info(
                    "Sending urgent news notification",
                    news_title=news_item_dict.get('title'),
                    subscriber_count=len(user_ids),
                    urgency_level="urgent",
                    importance_score=importance_score,
                    category=category
                )
                await self.bot.send_news_alert(user_ids, news_item_dict)
            else:
                self.logger.warning(
                    "No subscribed users found for urgent news notification",
                    news_title=news_item_dict.get('title'),
                    importance_score=importance_score,
                    category=category
                )
        except Exception as e:
            self.logger.error(
                "Error sending urgent news notification",
                news_title=news_item_dict.get('title'),
                error=str(e),
                exc_info=True
            )
    
    async def send_daily_digest(self, target_time: str = None):
        """发送每日新闻摘要"""
        try:
            self.logger.info(
                "Preparing daily digest",
                action="daily_digest_start",
                target_time=target_time
            )
            
            # Get digest subscribers
            digest_users = await self.get_digest_subscribers(target_time)
            
            if not digest_users:
                self.logger.info("No digest subscribers found")
                return
            
            # Get yesterday's news for digest
            yesterday = datetime.now() - timedelta(days=1)
            news_items = await self.get_daily_news(yesterday.date())
            
            if not news_items:
                self.logger.info("No news items found for daily digest")
                return
            
            # Send digest to each user
            successful_sends = 0
            for user_info in digest_users:
                try:
                    # Filter news based on user preferences
                    filtered_news = self.filter_news_for_user(
                        news_items,
                        user_info['min_importance_score']
                    )
                    
                    if filtered_news:
                        # Generate AI-powered digest with market analysis
                        digest_message = await self.generate_ai_digest(
                            filtered_news,
                            user_info.get('telegram_username')
                        )
                        
                        await self.bot.bot.send_message(
                            chat_id=user_info['telegram_id'],
                            text=digest_message,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                        successful_sends += 1
                        
                except Exception as e:
                    self.logger.error(
                        "Failed to send digest to user",
                        user_id=user_info['telegram_id'],
                        error=str(e)
                    )
            
            self.logger.info(
                "Daily digest sending completed",
                total_subscribers=len(digest_users),
                successful_sends=successful_sends,
                news_count=len(news_items)
            )
            
        except Exception as e:
            self.logger.error(
                "Error in daily digest process",
                error=str(e),
                exc_info=True
            )
    
    async def get_subscribed_user_ids(self, urgent_only: bool = False) -> List[str]:
        """获取订阅用户的 Telegram ID"""
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                user_ids = await user_repo.get_subscribed_user_ids(urgent_only)
                
                self.logger.debug(
                    "Fetched subscribed user IDs from database",
                    user_count=len(user_ids),
                    urgent_only=urgent_only
                )
                return user_ids
        except Exception as e:
            self.logger.error(
                "Error fetching subscribed user IDs",
                error=str(e),
                exc_info=True
            )
            return []
    
    def format_daily_digest(self, news_items: List[dict], username: str = None) -> str:
        """格式化每日摘要"""
        greeting = f"🌅 早上好{', ' + username if username else ''}！\n\n"
        message = greeting + "📊 <b>今日加密货币新闻摘要</b>\n\n"
        
        if not news_items:
            message += "😴 今天暂无重要新闻更新。"
            return message
        
        # Group news by category
        categorized_news = {}
        for item in news_items:
            category = item.get('category', 'general')
            if category not in categorized_news:
                categorized_news[category] = []
            categorized_news[category].append(item)
        
        category_emojis = {
            'bitcoin': '🪙',
            'ethereum': '🔷',
            'defi': '🏦',
            'nft': '🎨',
            'trading': '📹',
            'regulation': '📄',
            'technology': '🔧',
            'market_analysis': '📊',
            'altcoins': '🪙',
            'general': '📰'
        }
        
        total_items = 0
        for category, items in categorized_news.items():
            if not items:
                continue
                
            emoji = category_emojis.get(category, '📰')
            category_name = {
                'bitcoin': '比特币',
                'ethereum': '以太坊',
                'defi': 'DeFi',
                'nft': 'NFT',
                'trading': '交易',
                'regulation': '监管',
                'technology': '技术',
                'market_analysis': '市场分析',
                'altcoins': '山寨币',
                'general': '综合'
            }.get(category, category.title())
            
            message += f"{emoji} <b>{category_name}</b>\n"
            
            for item in items[:5]:  # Limit to 5 items per category
                total_items += 1
                importance_stars = "⭐" * item.get('importance_score', 1)
                message += f"  • <a href='{item['url']}'>{item['title'][:60]}{'...' if len(item['title']) > 60 else ''}</a>\n"
                message += f"    📡 {item.get('source', 'Unknown')} | {importance_stars}\n"
                
            message += "\n"
            
        message += f"📊 总计 {total_items} 条新闻\n"
        message += f"⏰ 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        message += "🚀 使用 /settings 调整推送设置"
        
        return message

    async def get_users_for_notification(self, importance_score: int, category: str = None, urgent_only: bool = False) -> List[str]:
        """Get users who should receive a notification based on criteria"""
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                user_ids = await user_repo.get_users_for_news_notification(
                    importance_score=importance_score,
                    category=category
                )
                
                self.logger.debug(
                    "Found users for notification",
                    user_count=len(user_ids),
                    importance_score=importance_score,
                    category=category,
                    urgent_only=urgent_only
                )
                
                return user_ids
        except Exception as e:
            self.logger.error(
                "Error getting users for notification",
                importance_score=importance_score,
                category=category,
                error=str(e),
                exc_info=True
            )
            return []

    async def get_digest_subscribers(self, target_time: str = None) -> List[Dict[str, Any]]:
        """Get users subscribed to daily digest"""
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                digest_users = await user_repo.get_digest_subscribers()
                
                # Filter by time if specified
                if target_time:
                    digest_users = [
                        user for user in digest_users
                        if user.get('digest_time') == target_time
                    ]
                
                self.logger.debug(
                    "Found digest subscribers",
                    user_count=len(digest_users),
                    target_time=target_time
                )
                
                return digest_users
        except Exception as e:
            self.logger.error(
                "Error getting digest subscribers",
                target_time=target_time,
                error=str(e),
                exc_info=True
            )
            return []

    async def get_daily_news(self, date) -> List[Dict[str, Any]]:
        """Get news items for a specific date"""
        try:
            async with SessionLocal() as db:
                # Get news items from the specified date
                stmt = select(NewsItem).where(
                    and_(
                        NewsItem.published_at >= date,
                        NewsItem.published_at < date + timedelta(days=1),
                        NewsItem.importance_score >= 2  # Only include somewhat important news
                    )
                ).order_by(NewsItem.importance_score.desc(), NewsItem.published_at.desc())
                
                result = await db.execute(stmt)
                news_items = result.scalars().all()
                
                # Convert to dict format
                news_dicts = []
                for item in news_items:
                    news_dicts.append({
                        'title': item.title,
                        'content': item.content,
                        'url': item.url,
                        'source': item.source.name if item.source else 'Unknown',
                        'category': item.category,
                        'importance_score': item.importance_score,
                        'published_at': item.published_at.strftime('%Y-%m-%d %H:%M'),
                        'is_urgent': item.is_urgent
                    })
                
                self.logger.debug(
                    "Retrieved daily news items",
                    date=str(date),
                    news_count=len(news_dicts)
                )
                
                return news_dicts
        except Exception as e:
            self.logger.error(
                "Error getting daily news",
                date=str(date),
                error=str(e),
                exc_info=True
            )
            return []

    def filter_news_for_user(self, news_items: List[Dict[str, Any]], min_importance: int) -> List[Dict[str, Any]]:
        """Filter news items based on user preferences"""
        try:
            filtered_items = [
                item for item in news_items
                if item.get('importance_score', 1) >= min_importance
            ]
            
            # Sort by importance score (descending) and limit to top 15 items
            filtered_items.sort(key=lambda x: x.get('importance_score', 1), reverse=True)
            filtered_items = filtered_items[:15]
            
            self.logger.debug(
                "Filtered news for user",
                original_count=len(news_items),
                filtered_count=len(filtered_items),
                min_importance=min_importance
            )
            
            return filtered_items
        except Exception as e:
            self.logger.error(
                "Error filtering news for user",
                min_importance=min_importance,
                error=str(e)
            )
            return news_items  # Return original list if filtering fails

    async def generate_ai_digest(self, news_items: List[Dict[str, Any]], username: str = None) -> str:
        """
        Generate AI-powered daily digest with market analysis and trend insights
        Falls back to standard format if AI is unavailable
        """
        try:
            # Check if OpenAI is configured
            if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
                self.logger.debug("OpenAI not configured, using standard digest format")
                return self.format_daily_digest(news_items, username)
            
            # Prepare news data for AI analysis
            news_summary = self._prepare_news_for_ai(news_items)
            
            if not news_summary:
                return self.format_daily_digest(news_items, username)
            
            # Generate AI summary
            ai_summary = await self._call_openai_for_digest(news_summary)
            
            if ai_summary:
                # Format AI-generated digest
                return self._format_ai_digest(ai_summary, news_items, username)
            else:
                # Fallback to standard format
                return self.format_daily_digest(news_items, username)
                
        except Exception as e:
            self.logger.error(
                "Error generating AI digest, falling back to standard format",
                error=str(e),
                news_count=len(news_items)
            )
            return self.format_daily_digest(news_items, username)

    def _prepare_news_for_ai(self, news_items: List[Dict[str, Any]]) -> str:
        """Prepare news items for AI analysis"""
        try:
            # Limit to top 10 most important news items
            sorted_news = sorted(
                news_items, 
                key=lambda x: x.get('importance_score', 1), 
                reverse=True
            )[:10]
            
            news_text = "Today's cryptocurrency news:\n\n"
            for i, item in enumerate(sorted_news, 1):
                news_text += f"{i}. Title: {item['title']}\n"
                news_text += f"   Category: {item.get('category', 'general')}\n"
                news_text += f"   Importance: {item.get('importance_score', 1)}/5\n"
                news_text += f"   Source: {item.get('source', 'Unknown')}\n"
                
                # Limit content to first 200 characters
                content = item.get('content', '')[:200]
                if len(content) == 200:
                    content += "..."
                news_text += f"   Summary: {content}\n\n"
            
            return news_text
            
        except Exception as e:
            self.logger.error("Error preparing news for AI", error=str(e))
            return ""

    async def _call_openai_for_digest(self, news_summary: str) -> Optional[str]:
        """Call OpenAI API to generate digest summary"""
        try:
            # Set up OpenAI client
            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompt = f"""
            Analyze the following cryptocurrency news and create a concise daily digest in Chinese.
            Focus on market trends, major developments, and key insights.
            
            {news_summary}
            
            Please provide:
            1. 🔥 Top 3 most important stories (brief summary)
            2. 📊 Market trend analysis
            3. 🎯 Key takeaways for investors
            4. 💡 What to watch for tomorrow
            
            Keep the response under 1000 characters and use emojis. Format for Telegram HTML.
            """
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a cryptocurrency market analyst providing daily insights in Chinese."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content.strip()
            
            return None
            
        except Exception as e:
            self.logger.error("Error calling OpenAI API for digest", error=str(e))
            return None

    def _format_ai_digest(self, ai_summary: str, news_items: List[Dict[str, Any]], username: str = None) -> str:
        """Format AI-generated digest with header and footer"""
        try:
            greeting = f"🌅 早上好{', ' + username if username else ''}！\n\n"
            header = "🤖 <b>AI智能摘要</b>\n\n"
            
            # Clean up AI response
            ai_content = self._clean_ai_response(ai_summary)
            
            footer = f"\n\n📊 基于 {len(news_items)} 条新闻生成\n"
            footer += f"⏰ 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            footer += "🔧 使用 /settings 调整推送设置"
            
            return greeting + header + ai_content + footer
            
        except Exception as e:
            self.logger.error("Error formatting AI digest", error=str(e))
            return self.format_daily_digest(news_items, username)

    def _clean_ai_response(self, ai_text: str) -> str:
        """Clean and format AI response for Telegram"""
        try:
            # Remove any potential problematic characters
            cleaned = re.sub(r'[^\w\s\U00010000-\U0010ffff\u4e00-\u9fff🔥📊🎯💡⚡📰🌅☀️⏰🤖🔧]', '', ai_text)
            
            # Ensure it's not too long
            if len(cleaned) > 1200:
                cleaned = cleaned[:1200] + "..."
            
            return cleaned
            
        except Exception as e:
            self.logger.error("Error cleaning AI response", error=str(e))
            return ai_text[:1000]  # Safe fallback

    async def send_regular_news_notification(self, news_item_dict: dict):
        """Send regular (non-urgent) news notification"""
        try:
            importance_score = news_item_dict.get('importance_score', 2)
            category = news_item_dict.get('category')
            
            # Only send if importance score is 3 or higher for regular notifications
            if importance_score < 3:
                self.logger.debug(
                    "Skipping regular notification for low importance news",
                    news_title=news_item_dict.get('title'),
                    importance_score=importance_score
                )
                return
            
            # Get users who should receive this notification
            user_ids = await self.get_users_for_notification(
                importance_score=importance_score,
                category=category,
                urgent_only=False
            )
            
            if user_ids:
                self.logger.info(
                    "Sending regular news notification",
                    news_title=news_item_dict.get('title'),
                    subscriber_count=len(user_ids),
                    importance_score=importance_score,
                    category=category
                )
                await self.bot.send_news_alert(user_ids, news_item_dict)
            else:
                self.logger.debug(
                    "No subscribers found for regular news notification",
                    news_title=news_item_dict.get('title'),
                    importance_score=importance_score,
                    category=category
                )
                
        except Exception as e:
            self.logger.error(
                "Error sending regular news notification",
                news_title=news_item_dict.get('title'),
                error=str(e),
                exc_info=True
            )