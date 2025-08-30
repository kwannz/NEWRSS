from fastapi import APIRouter, Request, Header, HTTPException
from telegram import Update
from telegram.ext import Application
from app.core.settings import settings
from app.services.telegram_bot import TelegramBot

router = APIRouter()

# Initialize Telegram bot instance
bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
application: Application = bot.app

@router.on_event("startup")
async def startup():
    """Initialize Telegram bot on startup"""
    await application.initialize()
    await application.start()
    
    if settings.TELEGRAM_WEBHOOK_URL:
        await application.bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_SECRET_TOKEN,
            drop_pending_updates=True,
        )
        print(f"Telegram webhook set to: {settings.TELEGRAM_WEBHOOK_URL}")

@router.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await application.stop()
    await application.shutdown()

@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Handle Telegram webhook updates"""
    # Verify secret token if configured
    if settings.TELEGRAM_SECRET_TOKEN and (
        x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN
    ):
        raise HTTPException(status_code=401, detail="Invalid secret token")

    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"ok": True}
    except Exception as e:
        print(f"Error processing Telegram update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")