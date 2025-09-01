import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from app.core.settings import settings
from app.core.logging import get_service_logger

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.bot = Bot(token)
        self.app = Application.builder().token(token).build()
        self.logger = get_service_logger("telegram_bot")
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.app.add_handler(CommandHandler("settings", self.settings_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        user_id = update.effective_user.id
        username = update.effective_user.username
        
        # Register user to database
        await self.register_user(user_id, username)
        
        welcome_text = (
            "🚀 欢迎使用 NEWRSS 加密货币新闻推送！\n\n"
            "📰 实时获取最新的加密货币新闻\n"
            "⚡ 毫秒级紧急新闻推送\n"
            "🎯 个性化订阅设置\n\n"
            "使用命令：\n"
            "/subscribe - 订阅新闻推送\n"
            "/unsubscribe - 取消订阅\n"
            "/settings - 推送设置"
        )
        
        keyboard = [
            [InlineKeyboardButton("📰 订阅新闻", callback_data="subscribe")],
            [InlineKeyboardButton("⚙️ 设置", callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /subscribe 命令"""
        user_id = update.effective_user.id
        # Update user subscription status in database
        self.logger.info("User subscribed to news alerts", user_id=user_id)
        await update.message.reply_text("✅ 已订阅新闻推送！您将收到重要的加密货币新闻更新。")
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /unsubscribe 命令"""
        user_id = update.effective_user.id
        # Cancel user subscription in database
        self.logger.info("User unsubscribed from news alerts", user_id=user_id)
        await update.message.reply_text("❌ 已取消订阅。您可以随时使用 /subscribe 重新订阅。")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /settings 命令"""
        keyboard = [
            [InlineKeyboardButton("🚨 紧急新闻", callback_data="toggle_urgent")],
            [InlineKeyboardButton("📊 每日摘要", callback_data="toggle_digest")],
            [InlineKeyboardButton("🎯 重要度设置", callback_data="importance_settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚙️ 推送设置\n\n请选择要配置的选项：",
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理内联键盘回调"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "subscribe":
            await self.subscribe_command(update, context)
        elif query.data == "settings":
            await self.settings_command(update, context)
        # Handle additional callback cases
        self.logger.debug("Unhandled callback query", callback_data=query.data, user_id=query.from_user.id)
    
    async def register_user(self, user_id: int, username: str):
        """注册 Telegram 用户"""
        # Implement database user registration logic
        self.logger.info(
            "Registering Telegram user", 
            user_id=user_id, 
            username=username,
            action="user_registration"
        )
        # NOTE: Database integration pending - user registration will be implemented
        # when user management system is added to the application
    
    async def send_news_alert(self, user_ids: list, news_item: dict):
        """发送新闻推送（异步）"""
        message = self.format_news_message(news_item)
        
        for user_id in user_ids:
            try:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            except Exception as e:
                self.logger.error(
                    "Failed to send Telegram message", 
                    user_id=user_id, 
                    error=str(e),
                    news_title=news_item.get('title', 'Unknown'),
                    exc_info=True
                )
    
    def format_news_message(self, news_item: dict) -> str:
        """格式化新闻消息"""
        urgency_emoji = "🚨" if news_item.get('is_urgent') else "📰"
        importance_stars = "⭐" * news_item.get('importance_score', 1)
        
        return (
            f"{urgency_emoji} <b>{news_item['title']}</b>\n\n"
            f"📊 重要度: {importance_stars}\n"
            f"🏷️ 分类: {news_item.get('category', 'general')}\n"
            f"📡 来源: {news_item['source']}\n"
            f"⏰ 时间: {news_item.get('published_at', '')}\n\n"
            f"{news_item['content'][:200]}...\n\n"
            f"🔗 <a href=\"{news_item['url']}\">阅读全文</a>"
        )