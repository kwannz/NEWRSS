from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from socketio import ASGIApp
from app.core.settings import settings
from app.api.auth import router as auth_router
from app.api.news import router as news_router
from app.services.telegram_webhook import router as telegram_router

app = FastAPI(title="NEWRSS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(news_router)
app.include_router(telegram_router)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ORIGINS,
)

@app.get("/")
async def root():
    return {"message": "NEWRSS API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@sio.event
async def connect(sid, environ):
    print(f"Socket connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Socket disconnected: {sid}")

async def broadcast_news(news_item: dict):
    await sio.emit('new_news', news_item)

async def broadcast_urgent(news_item: dict):
    await sio.emit('urgent_news', news_item)

asgi_app = ASGIApp(sio, other_asgi_app=app)