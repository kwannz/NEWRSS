import asyncio
from typing import Dict, List, Any
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.settings import settings
from app.core.logging import get_service_logger
from app.core.database import SessionLocal
from app.repositories.user_repository import UserRepository

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
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("urgent_on", self.urgent_on_command))
        self.app.add_handler(CommandHandler("urgent_off", self.urgent_off_command))
        self.app.add_handler(CommandHandler("categories", self.categories_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /status 命令"""
        fake_query = type('FakeQuery', (), {
            'from_user': update.effective_user,
            'edit_message_text': update.message.reply_text
        })()
        await self._handle_status_callback(fake_query, context)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        user = update.effective_user
        
        try:
            # Register user to database
            db_user = await self.register_user({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code
            })
            
            if db_user:
                welcome_text = (
                    f"🚀 欢迎使用 NEWRSS 加密货币新闻推送，{user.first_name}！\n\n"
                    "📰 实时获取最新的加密货币新闻\n"
                    "⚡ 毫秒级紧急新闻推送\n"
                    "🎯 个性化订阅设置\n"
                    "📊 每日新闻摘要\n\n"
                    "使用命令：\n"
                    "/subscribe - 订阅新闻推送\n"
                    "/unsubscribe - 取消订阅\n"
                    "/settings - 推送设置\n"
                    "/status - 查看订阅状态\n"
                    "/urgent_on - 开启紧急推送\n"
                    "/urgent_off - 关闭紧急推送\n"
                    "/categories - 分类订阅管理\n"
                    "/help - 查看帮助"
                )
            else:
                welcome_text = "❌ 注册失败，请稍后重试。"
            
            keyboard = [
                [InlineKeyboardButton("📰 订阅新闻", callback_data="subscribe")],
                [InlineKeyboardButton("⚙️ 设置", callback_data="settings")],
                [InlineKeyboardButton("📊 订阅状态", callback_data="status")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            
        except Exception as e:
            self.logger.error(
                "Error in start command",
                user_id=user.id,
                error=str(e),
                exc_info=True
            )
            await update.message.reply_text("❌ 服务暂时不可用，请稍后重试。")
    
    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /subscribe 命令"""
        user_id = update.effective_user.id
        telegram_id = str(user_id)
        
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                success = await user_repo.update_user_subscription_status(telegram_id, True)
                
                if success:
                    await user_repo.update_user_activity(user_id)
                    self.logger.info("User subscribed to news alerts", user_id=user_id)
                    
                    keyboard = [
                        [InlineKeyboardButton("📊 每日摘要", callback_data="enable_digest")],
                        [InlineKeyboardButton("⚙️ 设置", callback_data="settings")],
                        [InlineKeyboardButton("📰 分类订阅", callback_data="categories")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        "✅ 已订阅新闻推送！您将收到重要的加密货币新闻更新。\n\n"
                        "💡 提示：您可以设置接收每日摘要和调整重要度过滤。",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text("❌ 订阅失败，请先使用 /start 命令注册。")
                    
        except Exception as e:
            self.logger.error(
                "Error in subscribe command",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await update.message.reply_text("❌ 订阅失败，请稍后重试。")
    
    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /unsubscribe 命令"""
        user_id = update.effective_user.id
        telegram_id = str(user_id)
        
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                success = await user_repo.update_user_subscription_status(telegram_id, False)
                
                if success:
                    await user_repo.update_user_activity(user_id)
                    self.logger.info("User unsubscribed from news alerts", user_id=user_id)
                    
                    keyboard = [
                        [InlineKeyboardButton("📰 重新订阅", callback_data="subscribe")],
                        [InlineKeyboardButton("⚙️ 设置", callback_data="settings")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        "❌ 已取消订阅。您将不再收到新闻推送。\n\n"
                        "💡 您可以随时重新订阅。",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text("❌ 取消订阅失败，请先使用 /start 命令注册。")
                    
        except Exception as e:
            self.logger.error(
                "Error in unsubscribe command",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await update.message.reply_text("❌ 操作失败，请稍后重试。")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /settings 命令"""
        user_id = update.effective_user.id
        telegram_id = str(user_id)
        
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                settings = await user_repo.get_user_settings(telegram_id)
                
                if not settings:
                    await update.message.reply_text("❌ 请先使用 /start 命令注册。")
                    return
                
                # Create enhanced settings display text
                urgent_status = "✅ 开启" if settings["urgent_notifications"] else "❌ 关闭"
                digest_status = "✅ 开启" if settings["daily_digest"] else "❌ 关闭"
                importance_level = settings["min_importance_score"]
                digest_time = settings["digest_time"]
                max_notifications = settings["max_daily_notifications"]
                timezone = settings.get("timezone", "UTC")
                
                # Get time emoji
                time_emojis = {
                    "08:00": "🌅", "09:00": "☀️", "10:00": "🌤️",
                    "18:00": "🌆", "20:00": "🌙"
                }
                time_emoji = time_emojis.get(digest_time, "⏰")
                
                # Format limit display
                limit_display = "无限制" if max_notifications >= 999 else f"{max_notifications}条/天"
                
                settings_text = (
                    f"⚙️ <b>推送设置中心</b>\n\n"
                    f"📋 <b>基本设置</b>\n"
                    f"🚨 紧急推送: {urgent_status}\n"
                    f"📊 每日摘要: {digest_status}\n"
                    f"⏰ 摘要时间: {time_emoji} {digest_time}\n"
                    f"🌍 时区: {timezone}\n\n"
                    f"🎯 <b>过滤设置</b>\n"
                    f"⭐ 最低重要度: {'⭐' * importance_level} ({importance_level}/5)\n"
                    f"📱 每日限制: {limit_display}\n\n"
                    f"💡 <b>提示</b>: 紧急新闻不受推送限制影响\n"
                    f"🔧 点击下方按钮修改设置:"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton(f"🚨 紧急推送", callback_data="toggle_urgent"),
                        InlineKeyboardButton(f"📊 每日摘要", callback_data="toggle_digest")
                    ],
                    [
                        InlineKeyboardButton(f"🎯 重要度 ({importance_level})", callback_data="importance_settings"),
                        InlineKeyboardButton(f"⏰ 摘要时间", callback_data="digest_time")
                    ],
                    [
                        InlineKeyboardButton("📱 推送限制", callback_data="notification_limit"),
                        InlineKeyboardButton("📰 分类订阅", callback_data="categories")
                    ],
                    [InlineKeyboardButton("📊 查看订阅状态", callback_data="status")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='HTML')
                
        except Exception as e:
            self.logger.error(
                "Error in settings command",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await update.message.reply_text("❌ 获取设置失败，请稍后重试。")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理内联键盘回调"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        try:
            if query.data == "subscribe":
                await self._handle_subscribe_callback(query, context)
            elif query.data == "settings":
                await self._handle_settings_callback(query, context)
            elif query.data == "status":
                await self._handle_status_callback(query, context)
            elif query.data == "toggle_urgent":
                await self._handle_toggle_urgent(query, context)
            elif query.data == "toggle_digest":
                await self._handle_toggle_digest(query, context)
            elif query.data == "enable_digest":
                await self._handle_enable_digest(query, context)
            elif query.data == "importance_settings":
                await self._handle_importance_settings(query, context)
            elif query.data.startswith("importance_"):
                level = int(query.data.split("_")[1])
                await self._handle_set_importance(query, context, level)
            elif query.data == "categories":
                await self._handle_categories(query, context)
            elif query.data.startswith("category_"):
                category = query.data.split("_", 1)[1]
                await self._handle_category_toggle(query, context, category)
            elif query.data == "start":
                # Handle start callback from help or other messages
                fake_update = type('FakeUpdate', (), {
                    'effective_user': query.from_user,
                    'message': type('FakeMessage', (), {'reply_text': query.edit_message_text})()
                })()
                await self.start_command(fake_update, context)
            elif query.data == "digest_time":
                await self._handle_digest_time_settings(query, context)
            elif query.data.startswith("digest_time_"):
                time_slot = query.data.split("_", 2)[2]
                await self._handle_set_digest_time(query, context, time_slot)
            elif query.data == "notification_limit":
                await self._handle_notification_limit_settings(query, context)
            elif query.data.startswith("limit_"):
                limit = int(query.data.split("_")[1])
                await self._handle_set_notification_limit(query, context, limit)
            else:
                self.logger.debug("Unhandled callback query", callback_data=query.data, user_id=user_id)
                await query.edit_message_text("❌ 未知操作，请重新选择。")
                
        except Exception as e:
            self.logger.error(
                "Error in button callback",
                callback_data=query.data,
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await query.edit_message_text("❌ 操作失败，请稍后重试。")

    async def urgent_on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /urgent_on 命令 - 快速开启紧急推送"""
        user_id = update.effective_user.id
        telegram_id = str(user_id)
        
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                user = await user_repo.get_user_by_telegram_id(telegram_id)
                
                if not user:
                    await update.message.reply_text(
                        "❌ 请先使用 /start 命令注册。",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🚀 开始注册", callback_data="start")]
                        ])
                    )
                    return
                
                # Enable urgent notifications
                await user_repo.update_user_settings(telegram_id, {"urgent_notifications": True})
                
                self.logger.info("User enabled urgent notifications via command", user_id=user_id)
                
                await update.message.reply_text(
                    "✅ 紧急推送已开启！\n\n"
                    "🚨 您将收到重要度4级及以上的紧急新闻推送\n"
                    "⚙️ 可使用 /settings 调整重要度阈值",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ 推送设置", callback_data="settings")],
                        [InlineKeyboardButton("📊 订阅状态", callback_data="status")]
                    ])
                )
                
        except Exception as e:
            self.logger.error(
                "Error in urgent_on command",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await update.message.reply_text("❌ 操作失败，请稍后重试。")

    async def urgent_off_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /urgent_off 命令 - 快速关闭紧急推送"""
        user_id = update.effective_user.id
        telegram_id = str(user_id)
        
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                user = await user_repo.get_user_by_telegram_id(telegram_id)
                
                if not user:
                    await update.message.reply_text(
                        "❌ 请先使用 /start 命令注册。",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🚀 开始注册", callback_data="start")]
                        ])
                    )
                    return
                
                # Disable urgent notifications
                await user_repo.update_user_settings(telegram_id, {"urgent_notifications": False})
                
                self.logger.info("User disabled urgent notifications via command", user_id=user_id)
                
                await update.message.reply_text(
                    "❌ 紧急推送已关闭\n\n"
                    "📰 您仍会收到每日摘要（如已开启）\n"
                    "🔄 使用 /urgent_on 可重新开启",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚨 重新开启", callback_data="toggle_urgent")],
                        [InlineKeyboardButton("⚙️ 推送设置", callback_data="settings")]
                    ])
                )
                
        except Exception as e:
            self.logger.error(
                "Error in urgent_off command",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await update.message.reply_text("❌ 操作失败，请稍后重试。")

    async def categories_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /categories 命令 - 直接显示分类管理"""
        fake_query = type('FakeQuery', (), {
            'from_user': update.effective_user,
            'edit_message_text': update.message.reply_text,
            'answer': lambda: None
        })()
        
        await self._handle_categories(fake_query, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令 - 显示帮助信息"""
        help_text = (
            "🤖 <b>NEWRSS 帮助中心</b>\n\n"
            "📋 <b>主要命令：</b>\n"
            "/start - 注册并开始使用\n"
            "/subscribe - 订阅新闻推送\n"
            "/unsubscribe - 取消订阅\n"
            "/status - 查看订阅状态\n\n"
            
            "⚙️ <b>设置命令：</b>\n"
            "/settings - 打开设置面板\n"
            "/urgent_on - 快速开启紧急推送\n"
            "/urgent_off - 快速关闭紧急推送\n"
            "/categories - 管理分类订阅\n\n"
            
            "📊 <b>功能说明：</b>\n"
            "🚨 <b>紧急推送</b> - 重要新闻实时通知\n"
            "📰 <b>每日摘要</b> - 定时发送新闻汇总\n"
            "🎯 <b>重要度筛选</b> - 1-5级重要度过滤\n"
            "📂 <b>分类订阅</b> - 按类别订阅感兴趣的新闻\n\n"
            
            "🔧 <b>高级设置：</b>\n"
            "• 自定义重要度阈值\n"
            "• 设置每日摘要时间\n"
            "• 限制每日推送数量\n"
            "• 按分类设置不同筛选条件\n\n"
            
            "❓ 如有问题，请联系管理员。"
        )
        
        keyboard = [
            [InlineKeyboardButton("🚀 开始使用", callback_data="start")],
            [InlineKeyboardButton("⚙️ 推送设置", callback_data="settings")],
            [InlineKeyboardButton("📊 订阅状态", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='HTML')
    
    async def register_user(self, user_data: Dict[str, Any]) -> Any:
        """注册 Telegram 用户"""
        telegram_id = str(user_data["id"])
        
        try:
            async with SessionLocal() as db:
                user_repo = UserRepository(db)
                
                # Check if user already exists
                existing_user = await user_repo.get_user_by_telegram_id(telegram_id)
                if existing_user:
                    self.logger.info(
                        "User already registered",
                        telegram_id=telegram_id,
                        username=user_data.get("username"),
                        action="user_login"
                    )
                    # Update activity
                    await user_repo.update_user_activity(existing_user.id)
                    return existing_user
                
                # Create new user
                user = await user_repo.create_telegram_user(user_data)
                self.logger.info(
                    "Registered new Telegram user",
                    telegram_id=telegram_id,
                    username=user_data.get("username"),
                    action="user_registration"
                )
                return user
                
        except Exception as e:
            self.logger.error(
                "Error registering Telegram user",
                telegram_id=telegram_id,
                username=user_data.get("username"),
                error=str(e),
                exc_info=True
            )
            return None

    async def _handle_subscribe_callback(self, query, context):
        """处理订阅回调"""
        # Create a fake update object for subscribe_command
        fake_update = type('FakeUpdate', (), {
            'effective_user': query.from_user,
            'message': type('FakeMessage', (), {'reply_text': query.edit_message_text})()
        })()
        await self.subscribe_command(fake_update, context)

    async def _handle_settings_callback(self, query, context):
        """处理设置回调"""
        # Create a fake update object for settings_command
        fake_update = type('FakeUpdate', (), {
            'effective_user': query.from_user,
            'message': type('FakeMessage', (), {'reply_text': query.edit_message_text})()
        })()
        await self.settings_command(fake_update, context)

    async def _handle_status_callback(self, query, context):
        """处理状态查询回调"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            settings = await user_repo.get_user_settings(telegram_id)
            categories = await user_repo.get_user_categories(telegram_id)
            
            if not settings:
                await query.edit_message_text("❌ 请先使用 /start 命令注册。")
                return
            
            urgent_status = "✅" if settings["urgent_notifications"] else "❌"
            digest_status = "✅" if settings["daily_digest"] else "❌"
            
            # Format subscribed categories
            subscribed_cats = [cat["category"] for cat in categories if cat["is_subscribed"]]
            categories_text = ", ".join(subscribed_cats) if subscribed_cats else "无"
            
            status_text = (
                f"📊 订阅状态\n\n"
                f"🚨 紧急新闻推送: {urgent_status}\n"
                f"📊 每日摘要: {digest_status}\n"
                f"🎯 最低重要度: {settings['min_importance_score']}/5\n"
                f"📱 每日最大推送: {settings['max_daily_notifications']}条\n"
                f"📰 订阅分类: {categories_text}\n"
                f"⏰ 摘要时间: {settings['digest_time']}\n"
                f"🌍 时区: {settings['timezone']}"
            )
            
            keyboard = [
                [InlineKeyboardButton("⚙️ 修改设置", callback_data="settings")],
                [InlineKeyboardButton("📰 分类订阅", callback_data="categories")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(status_text, reply_markup=reply_markup)

    async def _handle_toggle_urgent(self, query, context):
        """切换紧急新闻推送"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            settings = await user_repo.get_user_settings(telegram_id)
            
            if not settings:
                await query.edit_message_text("❌ 请先使用 /start 命令注册。")
                return
            
            new_status = not settings["urgent_notifications"]
            await user_repo.update_user_settings(telegram_id, {"urgent_notifications": new_status})
            
            status_text = "✅ 已开启" if new_status else "❌ 已关闭"
            await query.edit_message_text(
                f"🚨 紧急新闻推送: {status_text}\n\n返回设置菜单:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ 返回设置", callback_data="settings")]
                ])
            )

    async def _handle_toggle_digest(self, query, context):
        """切换每日摘要"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            settings = await user_repo.get_user_settings(telegram_id)
            
            if not settings:
                await query.edit_message_text("❌ 请先使用 /start 命令注册。")
                return
            
            new_status = not settings["daily_digest"]
            await user_repo.update_user_settings(telegram_id, {"daily_digest": new_status})
            
            status_text = "✅ 已开启" if new_status else "❌ 已关闭"
            message = f"📊 每日摘要: {status_text}"
            
            if new_status:
                message += f"\n📅 将在每天 {settings['digest_time']} 发送摘要"
            
            await query.edit_message_text(
                message + "\n\n返回设置菜单:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ 返回设置", callback_data="settings")]
                ])
            )

    async def _handle_enable_digest(self, query, context):
        """直接启用每日摘要"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            await user_repo.update_user_settings(telegram_id, {"daily_digest": True})
            
            await query.edit_message_text(
                "✅ 已开启每日摘要！\n\n"
                "📅 将在每天上午 9:00 发送新闻摘要\n"
                "⚙️ 可在设置中修改时间",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ 设置", callback_data="settings")]
                ])
            )

    async def _handle_importance_settings(self, query, context):
        """重要度设置"""
        keyboard = [
            [InlineKeyboardButton("⭐ 1级 (全部新闻)", callback_data="importance_1")],
            [InlineKeyboardButton("⭐⭐ 2级 (较重要)", callback_data="importance_2")],
            [InlineKeyboardButton("⭐⭐⭐ 3级 (重要)", callback_data="importance_3")],
            [InlineKeyboardButton("⭐⭐⭐⭐ 4级 (很重要)", callback_data="importance_4")],
            [InlineKeyboardButton("⭐⭐⭐⭐⭐ 5级 (极重要)", callback_data="importance_5")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🎯 选择最低重要度级别\n\n"
            "只有达到或超过此级别的新闻才会推送给您：",
            reply_markup=reply_markup
        )

    async def _handle_set_importance(self, query, context, level: int):
        """设置重要度级别"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            await user_repo.update_user_settings(telegram_id, {"min_importance_score": level})
            
            level_text = "⭐" * level
            await query.edit_message_text(
                f"✅ 已设置最低重要度为: {level_text} ({level}级)\n\n"
                "返回设置菜单:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ 返回设置", callback_data="settings")]
                ])
            )

    async def _handle_categories(self, query, context):
        """处理分类订阅"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        # Available categories
        available_categories = [
            "bitcoin", "ethereum", "defi", "nft", "trading", 
            "regulation", "technology", "market_analysis", "altcoins"
        ]
        
        category_names = {
            "bitcoin": "比特币",
            "ethereum": "以太坊", 
            "defi": "DeFi",
            "nft": "NFT",
            "trading": "交易",
            "regulation": "监管",
            "technology": "技术",
            "market_analysis": "市场分析",
            "altcoins": "山寨币"
        }
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            user_categories = await user_repo.get_user_categories(telegram_id)
            
            # Create subscription status map
            subscribed = {cat["category"]: cat["is_subscribed"] for cat in user_categories}
            
            keyboard = []
            for category in available_categories:
                status = "✅" if subscribed.get(category, False) else "❌"
                name = category_names.get(category, category)
                keyboard.append([InlineKeyboardButton(
                    f"{status} {name}", 
                    callback_data=f"category_{category}"
                )])
            
            keyboard.append([InlineKeyboardButton("⬅️ 返回", callback_data="settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📰 分类订阅设置\n\n"
                "点击切换各分类的订阅状态：",
                reply_markup=reply_markup
            )

    async def _handle_category_toggle(self, query, context, category: str):
        """切换分类订阅状态"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        category_names = {
            "bitcoin": "比特币",
            "ethereum": "以太坊", 
            "defi": "DeFi",
            "nft": "NFT",
            "trading": "交易",
            "regulation": "监管",
            "technology": "技术",
            "market_analysis": "市场分析",
            "altcoins": "山寨币"
        }
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            user_categories = await user_repo.get_user_categories(telegram_id)
            
            # Check current status
            current_status = False
            for cat in user_categories:
                if cat["category"] == category:
                    current_status = cat["is_subscribed"]
                    break
            
            new_status = not current_status
            
            if new_status:
                await user_repo.subscribe_to_category(telegram_id, category)
            else:
                await user_repo.unsubscribe_from_category(telegram_id, category)
            
            category_name = category_names.get(category, category)
            status_text = "✅ 已订阅" if new_status else "❌ 已取消"
            
            await query.edit_message_text(
                f"📰 {category_name}: {status_text}\n\n"
                "返回分类设置:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📰 分类设置", callback_data="categories")]
                ])
            )

    async def _handle_digest_time_settings(self, query, context):
        """处理摘要时间设置"""
        keyboard = [
            [InlineKeyboardButton("🌅 08:00 (早间)", callback_data="digest_time_08:00")],
            [InlineKeyboardButton("☀️ 09:00 (上午)", callback_data="digest_time_09:00")],
            [InlineKeyboardButton("🌤️ 10:00 (上午)", callback_data="digest_time_10:00")],
            [InlineKeyboardButton("🌆  18:00 (晚间)", callback_data="digest_time_18:00")],
            [InlineKeyboardButton("🌙 20:00 (夜间)", callback_data="digest_time_20:00")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⏰ 选择每日摘要发送时间\n\n"
            "📅 摘要将包含前一天的重要新闻汇总\n"
            "🌍 时间基于UTC时区，请根据您的时区选择",
            reply_markup=reply_markup
        )

    async def _handle_set_digest_time(self, query, context, time_slot: str):
        """设置摘要时间"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            await user_repo.update_user_settings(telegram_id, {"digest_time": time_slot})
            
            time_emojis = {
                "08:00": "🌅",
                "09:00": "☀️", 
                "10:00": "🌤️",
                "18:00": "🌆",
                "20:00": "🌙"
            }
            
            emoji = time_emojis.get(time_slot, "⏰")
            await query.edit_message_text(
                f"✅ 摘要时间已设置为: {emoji} {time_slot}\n\n"
                "📅 将在每天此时间发送新闻摘要\n"
                "返回设置菜单:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ 返回设置", callback_data="settings")]
                ])
            )

    async def _handle_notification_limit_settings(self, query, context):
        """处理通知限制设置"""
        keyboard = [
            [InlineKeyboardButton("5条/天 (精简)", callback_data="limit_5")],
            [InlineKeyboardButton("10条/天 (标准)", callback_data="limit_10")],
            [InlineKeyboardButton("20条/天 (详细)", callback_data="limit_20")],
            [InlineKeyboardButton("50条/天 (全面)", callback_data="limit_50")],
            [InlineKeyboardButton("无限制", callback_data="limit_999")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📱 设置每日最大推送数量\n\n"
            "⚡ 紧急新闻不受此限制影响\n"
            "📊 每日摘要也不受此限制影响\n"
            "🎯 选择适合您的推送频率:",
            reply_markup=reply_markup
        )

    async def _handle_set_notification_limit(self, query, context, limit: int):
        """设置通知限制"""
        user_id = query.from_user.id
        telegram_id = str(user_id)
        
        async with SessionLocal() as db:
            user_repo = UserRepository(db)
            await user_repo.update_user_settings(telegram_id, {"max_daily_notifications": limit})
            
            limit_text = "无限制" if limit >= 999 else f"{limit}条/天"
            await query.edit_message_text(
                f"✅ 每日推送限制已设置为: {limit_text}\n\n"
                "⚡ 紧急新闻不受限制\n"
                "📊 每日摘要不受限制\n"
                "返回设置菜单:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ 返回设置", callback_data="settings")]
                ])
            )
    
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