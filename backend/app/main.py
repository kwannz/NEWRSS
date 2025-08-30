from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import socketio
from socketio import ASGIApp
from contextlib import asynccontextmanager
from app.core.settings import settings
from app.core.database import engine, Base
from app.api.news import router as news_router
from app.api.auth import router as auth_router
from app.api.sources import router as sources_router
from app.services.telegram_webhook import router as telegram_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created")
    yield
    # Shutdown
    await engine.dispose()
    print("Database connection closed")

app = FastAPI(title="NEWRSS API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news_router)
app.include_router(sources_router)
app.include_router(telegram_router)
app.include_router(auth_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ORIGINS,
)

@app.get("/")
async def root():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

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