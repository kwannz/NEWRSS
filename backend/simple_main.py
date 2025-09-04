#!/usr/bin/env python3
"""
Simple NEWRSS backend for development - minimal middleware setup
"""
from fastapi import FastAPI, Form, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import os
import json

# Set environment variables for development
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./newrss.db'
os.environ['REDIS_URL'] = ''
os.environ['SECRET_KEY'] = 'newrss-local-production-secret-key-change-me-2024'
os.environ['ENV'] = 'development'
os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://127.0.0.1:3000'
os.environ['TELEGRAM_BOT_TOKEN'] = ''
os.environ['OPENAI_API_KEY'] = ''

app = FastAPI(title="NEWRSS API", version="1.0.0")

# Basic CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "newrss-api"}

@app.get("/news")
async def get_news():
    return [
        {
            "id": 1,
            "title": "比特币价格突破新高，市场情绪乐观",
            "titleEn": "Bitcoin price breaks new high, market sentiment optimistic",
            "content": "比特币价格在今日早盘突破历史新高，达到65000美元，市场分析师认为这是机构投资者大量入场的结果。",
            "contentEn": "Bitcoin price broke historical high in early trading today, reaching $65,000, market analysts believe this is the result of large-scale institutional investor entry.",
            "summary": "比特币创新高，机构资金涌入",
            "summaryEn": "Bitcoin hits new high, institutional funds flow in",
            "url": "https://example.com/bitcoin-news-1",
            "source": "CryptoNews",
            "category": "market",
            "publishedAt": "2025-09-02T10:00:00Z",
            "importanceScore": 5,
            "isUrgent": True,
            "marketImpact": 5,
            "sentimentScore": 0.8,
            "keyTokens": ["BTC", "Bitcoin"],
            "keyPrices": ["$65,000"],
            "createdAt": "2025-09-02T10:00:00Z"
        },
        {
            "id": 2,
            "title": "以太坊Layer2扩容方案取得重大进展",
            "titleEn": "Ethereum Layer2 scaling solution achieves major breakthrough",
            "content": "多个以太坊Layer2解决方案在过去一周内处理交易量创下新纪录，显示出以太坊生态系统的强劲发展势头。",
            "contentEn": "Multiple Ethereum Layer2 solutions set new transaction volume records in the past week, showing strong momentum in the Ethereum ecosystem.",
            "summary": "Layer2扩容显著提升，生态发展强劲",
            "summaryEn": "Layer2 scaling significantly improved, ecosystem developing strongly",
            "url": "https://example.com/ethereum-layer2-news",
            "source": "EthereumNews",
            "category": "technology",
            "publishedAt": "2025-09-02T09:30:00Z",
            "importanceScore": 4,
            "isUrgent": False,
            "marketImpact": 4,
            "sentimentScore": 0.6,
            "keyTokens": ["ETH", "Ethereum", "Layer2"],
            "keyPrices": [],
            "createdAt": "2025-09-02T09:30:00Z"
        },
        {
            "id": 3,
            "title": "去中心化金融(DeFi)协议TVL达到新里程碑",
            "titleEn": "Decentralized Finance (DeFi) protocol TVL reaches new milestone",
            "content": "去中心化金融协议的总锁仓价值(TVL)今日突破1500亿美元，创下历史新高，反映出DeFi生态系统的持续增长。",
            "contentEn": "Total Value Locked (TVL) in decentralized finance protocols broke through $150 billion today, setting a new historical high, reflecting continued growth in the DeFi ecosystem.",
            "summary": "DeFi TVL突破1500亿美元创历史新高",
            "summaryEn": "DeFi TVL breaks through $150 billion, setting new record",
            "url": "https://example.com/defi-tvl-milestone",
            "source": "DeFiPulse",
            "category": "defi",
            "publishedAt": "2025-09-02T08:45:00Z",
            "importanceScore": 4,
            "isUrgent": False,
            "marketImpact": 4,
            "sentimentScore": 0.7,
            "keyTokens": ["DeFi", "TVL"],
            "keyPrices": ["$150 billion"],
            "createdAt": "2025-09-02T08:45:00Z"
        }
    ]

@app.get("/api/news")
async def get_news_legacy():
    return {"news": [], "message": "Backend is running - database connection needed for news"}

@app.get("/news/{news_id}")
async def get_news_item(news_id: int):
    if news_id == 1:
        return {
            "id": 1,
            "title": "比特币价格突破新高，市场情绪乐观",
            "titleEn": "Bitcoin price breaks new high, market sentiment optimistic",
            "content": "比特币价格在今日早盘突破历史新高，达到65000美元，市场分析师认为这是机构投资者大量入场的结果。技术分析显示，比特币的上涨趋势仍将持续，多个技术指标都显示出强烈的买入信号。",
            "contentEn": "Bitcoin price broke historical high in early trading today, reaching $65,000, market analysts believe this is the result of large-scale institutional investor entry. Technical analysis shows Bitcoin's upward trend will continue, with multiple technical indicators showing strong buy signals.",
            "summary": "比特币创新高，机构资金涌入",
            "summaryEn": "Bitcoin hits new high, institutional funds flow in",
            "url": "https://example.com/bitcoin-news-1",
            "source": "CryptoNews",
            "category": "market",
            "publishedAt": "2025-09-02T10:00:00Z",
            "importanceScore": 5,
            "isUrgent": True,
            "marketImpact": 5,
            "sentimentScore": 0.8,
            "keyTokens": ["BTC", "Bitcoin"],
            "keyPrices": ["$65,000"],
            "createdAt": "2025-09-02T10:00:00Z"
        }
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="News item not found")

# Simple authentication for development
user_preferences = {
    "urgent_notifications": True,
    "daily_digest": False,
    "min_importance_score": 3,
    "max_daily_notifications": 10,
    "categories": ["market", "technology", "defi"]
}

# User state for development
current_user = {
    "id": 1,
    "username": "admin",
    "email": "admin@newrss.com",
    "is_active": True,
    "telegram_id": None
}

@app.post("/auth/token")
async def login(username: str = Form(...), password: str = Form(...)):
    # Development credentials
    if username == "admin" and password == "admin123":
        return {
            "access_token": "dev-admin-token",
            "refresh_token": "dev-admin-refresh",
            "token_type": "bearer",
            "user": {
                "id": 1,
                "username": "admin",
                "email": "admin@newrss.com",
                "is_active": True,
                "telegram_id": None
            }
        }
    elif username == "demo" and password == "demo123":
        return {
            "access_token": "dev-demo-token", 
            "refresh_token": "dev-demo-refresh",
            "token_type": "bearer",
            "user": {
                "id": 2,
                "username": "demo",
                "email": "demo@newrss.com", 
                "is_active": True,
                "telegram_id": "123456"  # Demo user has Telegram connected
            }
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

@app.post("/auth/register")
async def register(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    return {
        "message": "Registration successful - using development mode",
        "user": {
            "id": 999,
            "username": username,
            "email": email,
            "is_active": True,
            "telegram_id": None
        }
    }

@app.get("/auth/me")
async def get_current_user():
    return current_user

@app.get("/auth/me/preferences")
async def get_user_preferences():
    """获取用户偏好设置"""
    return user_preferences

@app.patch("/auth/me/preferences")
async def update_user_preferences(request: Request):
    """更新用户偏好设置"""
    try:
        data = await request.json()
        user_preferences.update(data)
        return {
            "message": "Preferences updated successfully",
            "preferences": user_preferences
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update preferences: {str(e)}"
        )

# Telegram Bot Integration
telegram_users = {}  # Simple in-memory storage for development

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """简单的 Telegram webhook 处理器"""
    try:
        data = await request.json()
        update = data
        
        # 处理消息
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            user = message.get("from", {})
            text = message.get("text", "")
            
            # 存储用户信息
            telegram_users[chat_id] = {
                "id": user.get("id"),
                "username": user.get("username"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "subscribed": telegram_users.get(chat_id, {}).get("subscribed", False)
            }
            
            # 处理命令
            if text.startswith("/start"):
                response_text = (
                    f"🚀 欢迎使用 NEWRSS 加密货币新闻推送，{user.get('first_name', 'Friend')}！\n\n"
                    "📰 实时获取最新的加密货币新闻\n"
                    "⚡ 毫秒级紧急新闻推送\n"
                    "🎯 个性化订阅设置\n\n"
                    "使用命令：\n"
                    "/subscribe - 订阅新闻推送\n"
                    "/unsubscribe - 取消订阅\n"
                    "/status - 查看订阅状态\n"
                    "/help - 查看帮助"
                )
                return {
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": response_text
                }
            elif text.startswith("/subscribe"):
                telegram_users[chat_id]["subscribed"] = True
                return {
                    "method": "sendMessage", 
                    "chat_id": chat_id,
                    "text": "✅ 订阅成功！您将收到最新的加密货币新闻推送。"
                }
            elif text.startswith("/unsubscribe"):
                telegram_users[chat_id]["subscribed"] = False
                return {
                    "method": "sendMessage",
                    "chat_id": chat_id, 
                    "text": "❌ 已取消订阅。您将不再收到新闻推送。"
                }
            elif text.startswith("/status"):
                subscribed = telegram_users.get(chat_id, {}).get("subscribed", False)
                status_text = f"📊 订阅状态：{'✅ 已订阅' if subscribed else '❌ 未订阅'}"
                return {
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": status_text
                }
            elif text.startswith("/help"):
                help_text = (
                    "🤖 NEWRSS Telegram Bot 帮助\n\n"
                    "/start - 开始使用\n"
                    "/subscribe - 订阅新闻推送\n"
                    "/unsubscribe - 取消订阅\n"
                    "/status - 查看订阅状态\n"
                    "/help - 显示此帮助信息\n\n"
                    "📱 访问 http://localhost:3000 使用完整功能"
                )
                return {
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": help_text
                }
            else:
                return {
                    "method": "sendMessage",
                    "chat_id": chat_id,
                    "text": "❓ 未知命令。使用 /help 查看可用命令。"
                }
        
        return {"ok": True}
        
    except Exception as e:
        print(f"Telegram webhook error: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/telegram/users")
async def get_telegram_users():
    """获取 Telegram 用户列表（开发用）"""
    return {
        "users": telegram_users,
        "total_users": len(telegram_users),
        "subscribed_users": sum(1 for user in telegram_users.values() if user.get("subscribed", False))
    }

@app.post("/telegram/connect")
async def connect_telegram(telegram_id: str = Form(...)):
    """连接Telegram账户"""
    try:
        # Update user with telegram_id (simulated for development)
        current_user["telegram_id"] = telegram_id
        return {
            "message": "Telegram连接成功",
            "telegram_id": telegram_id,
            "user": current_user
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"连接Telegram失败: {str(e)}"
        )

@app.post("/telegram/disconnect")
async def disconnect_telegram():
    """断开Telegram连接"""
    current_user["telegram_id"] = None
    return {
        "message": "Telegram连接已断开",
        "user": current_user
    }

@app.post("/telegram/broadcast")
async def telegram_broadcast(message: str = Form(...)):
    """向所有订阅用户广播消息（开发用）"""
    subscribed_users = [chat_id for chat_id, user in telegram_users.items() if user.get("subscribed", False)]
    
    if not subscribed_users:
        return {
            "status": "no_subscribers",
            "message": "没有订阅用户"
        }
    
    return {
        "status": "broadcast_simulated", 
        "message": f"模拟向 {len(subscribed_users)} 个用户发送消息: {message}",
        "subscriber_count": len(subscribed_users)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)