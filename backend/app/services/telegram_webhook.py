from fastapi import APIRouter, Request, Header, HTTPException
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application
from typing import Optional
from app.core.settings import settings
from app.services.telegram_bot import TelegramBot

# Global variable to store the Telegram application
telegram_app: Application = None

@asynccontextmanager
async def telegram_lifespan():
    """Lifespan context manager for Telegram bot"""
    global telegram_app
    
    try:
        if settings.TELEGRAM_BOT_TOKEN:
            bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
            telegram_app = bot.app
            
            await telegram_app.initialize()
            await telegram_app.start()
            
            if settings.TELEGRAM_WEBHOOK_URL:
                await telegram_app.bot.set_webhook(
                    url=settings.TELEGRAM_WEBHOOK_URL,
                    secret_token=settings.TELEGRAM_SECRET_TOKEN,
                    drop_pending_updates=True,
                )
                print(f"Telegram webhook set to: {settings.TELEGRAM_WEBHOOK_URL}")
        
        yield
        
    finally:
        if telegram_app:
            await telegram_app.stop()
            await telegram_app.shutdown()

router = APIRouter()

@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """Handle Telegram webhook updates"""
    # Verify secret token if configured
    if settings.TELEGRAM_SECRET_TOKEN and (
        x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN
    ):
        raise HTTPException(status_code=401, detail="Invalid secret token")

    try:
        if not telegram_app:
            raise HTTPException(status_code=503, detail="Telegram bot not initialized")
        
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        print(f"Error processing Telegram update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")