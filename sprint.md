# NEWRSS 项目 Sprint 开发计划

## 项目概述

基于 Python 后端 + Next.js + TypeScript 前端的加密货币新闻聚合平台，实现类似方程式新闻的毫秒级新闻推送、多源聚合和 AI 智能分析功能，支持 Telegram 实时推送。

## 技术架构

### 前端技术栈
- **框架**: Next.js 15 + TypeScript
- **UI 库**: Tailwind CSS + Shadcn/ui
- **状态管理**: Zustand
- **实时通信**: Socket.io-client
- **数据获取**: 服务器端 fetch + Server Actions；客户端 SWR/React Query（Axios 可选）
- **构建工具**: Turbopack（开发）；生产使用 Next.js 默认构建
- **运行时**: Node.js 20 LTS（满足 Next.js 15 要求）

### 后端技术栈
- **主服务**: Python 3.12 + FastAPI
- **数据抓取**: Python + aiohttp + asyncio
- **消息队列**: Redis + Celery
- **调度**: Celery Beat（用于 30s 级轮询与定时任务）
- **数据库**: PostgreSQL + SQLAlchemy 2.x（AsyncSession + asyncpg）
- **缓存**: Redis
- **WebSocket**: python-socketio v5（兼容 Socket.IO v4）
- **推送服务**: Telegram Bot API

### 基础设施
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack
- **配置与安全**: .env 管理密钥、CORS 白名单、最小权限访问控制

## Sprint 开发计划

### Sprint 1: 项目基础架构 (2 周)

#### 目标
搭建完整的开发环境和基础架构

#### 任务清单

**后端开发 (Python)**
- [ ] 初始化 FastAPI 项目结构
- [ ] 配置 PostgreSQL 数据库连接
- [ ] 设计核心数据模型 (用户、新闻源、文章、订阅)
- [ ] 实现用户认证系统 (JWT)
- [ ] 配置 Redis 缓存和消息队列
- [ ] 创建基础 API 路由结构

**前端开发 (Next.js + TypeScript)**
- [ ] 初始化 Next.js 项目 (App Router)
- [ ] 配置 TypeScript 和 ESLint
- [ ] 集成 Tailwind CSS 和 Shadcn/ui
- [ ] 实现基础布局组件
- [ ] 创建用户认证页面 (登录/注册)
- [ ] 配置 Zustand 状态管理

**DevOps**
- [ ] 编写 Docker 配置文件
- [ ] 配置 docker-compose.yml
- [ ] 设置开发环境脚本
- [ ] 配置 GitHub Actions CI/CD

#### 技术实现示例

```python
# backend/app/models/news.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class NewsItem(Base):
    __tablename__ = "news_items"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    url = Column(String, unique=True, index=True)
    source = Column(String, index=True)
    category = Column(String, index=True)
    published_at = Column(DateTime)
    importance_score = Column(Integer, default=0)
    is_urgent = Column(Boolean, default=False)
    created_at = Column(DateTime)
```

```typescript
// frontend/types/news.ts
export interface NewsItem {
  id: number;
  title: string;
  content: string;
  url: string;
  source: string;
  category: string;
  publishedAt: string;
  importanceScore: number;
  isUrgent: boolean;
  createdAt: string;
}

export interface NewsFilter {
  category?: string;
  source?: string;
  timeRange?: 'hour' | 'day' | 'week';
  importance?: number;
}
```

### Sprint 2: 数据抓取与聚合系统 (3 周)

#### 目标
实现高频数据抓取和多源新闻聚合

#### 任务清单

**数据抓取服务**
- [ ] 实现 RSS 解析器 (支持 RSS 2.0, Atom)
- [ ] 开发交易所 API 监控 (币安、OKX、Coinbase)
- [ ] 集成 X（Twitter）API 监控（注意付费/权限限制）
- [ ] 实现 Telegram 频道监控
- [ ] 构建网页爬虫 (BeautifulSoup + Selenium)
- [ ] 设计数据去重算法

**实时处理系统**
- [ ] 配置 Celery 异步任务队列
- [ ] 实现高频抓取调度 (每 30 秒)
- [ ] 构建内容分类算法
- [ ] 开发关键词检测系统
- [ ] 实现紧急新闻优先级处理

**API 开发**
- [ ] 新闻列表 API (分页、过滤、排序)
- [ ] 实时新闻推送 API
- [ ] 新闻源管理 API
- [ ] 用户订阅管理 API

#### 技术实现示例

```python
# backend/app/services/rss_fetcher.py
import aiohttp
import asyncio
from typing import List
import feedparser
from datetime import datetime

class RSSFetcher:
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def fetch_feed(self, url: str) -> List[dict]:
        try:
            async with self.session.get(url, timeout=10) as response:
                content = await response.text()
                feed = feedparser.parse(content)
                
                items = []
                for entry in feed.entries:
                    items.append({
                        'title': entry.title,
                        'content': entry.summary,
                        'url': entry.link,
                        'published_at': datetime(*entry.published_parsed[:6]),
                        'source': feed.feed.title
                    })
                return items
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return []
    
    async def fetch_multiple_feeds(self, urls: List[str]) -> List[dict]:
        tasks = [self.fetch_feed(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)
        
        return all_items
```

```python
# backend/app/tasks/news_crawler.py
import asyncio
from celery import Celery
from app.services.rss_fetcher import RSSFetcher
from app.services.telegram_notifier import TelegramNotifier

celery_app = Celery('newrss')

async def _crawl_news_sources_async():
    """异步抓取新闻源（由 Celery 同步任务驱动）"""
    sources = [
        'https://cointelegraph.com/rss',
        'https://decrypt.co/feed',
        'https://www.coindesk.com/arc/outboundfeeds/rss/',
        # 更多新闻源...
    ]
    async with RSSFetcher() as fetcher:
        news_items = await fetcher.fetch_multiple_feeds(sources)
        notifier = TelegramNotifier()
        for item in news_items:
            # TODO: 保存到数据库
            if is_urgent_news(item):  # 伪代码：根据规则判定紧急
                # 这里演示调用异步通知
                await notifier.notify_urgent_news(item)

@celery_app.task
def crawl_news_sources():
    """定时抓取新闻源（Celery 同步任务包装异步逻辑）"""
    asyncio.run(_crawl_news_sources_async())

async def _monitor_exchange_announcements_async():
    """异步监控交易所公告（示例占位）"""
    # 实现交易所 API 监控逻辑
    return

@celery_app.task
def monitor_exchange_announcements():
    """监控交易所公告（Celery 同步任务包装异步逻辑）"""
    asyncio.run(_monitor_exchange_announcements_async())
```

### Sprint 3: 前端界面与实时功能 (2 周)

#### 目标
构建现代化用户界面和实时新闻推送

#### 任务清单

**核心页面开发**
- [ ] 新闻首页 (瀑布流布局)
- [ ] 新闻详情页
- [ ] 用户仪表板
- [ ] 订阅源管理页面
- [ ] 设置页面

**实时功能**
- [ ] WebSocket 连接管理
- [ ] 实时新闻推送
- [ ] 新闻更新通知
- [ ] 在线用户状态

**用户体验优化**
- [ ] 响应式设计 (移动端适配)
- [ ] 加载状态管理
- [ ] 错误边界处理
- [ ] 无限滚动加载
- [ ] 搜索功能

#### 技术实现示例

```typescript
// frontend/components/NewsCard.tsx
import { NewsItem } from '@/types/news';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface NewsCardProps {
  news: NewsItem;
  onRead: (id: number) => void;
}

export function NewsCard({ news, onRead }: NewsCardProps) {
  return (
    <Card className="hover:shadow-lg transition-shadow cursor-pointer" 
          onClick={() => onRead(news.id)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Badge variant={news.isUrgent ? "destructive" : "secondary"}>
            {news.source}
          </Badge>
          <span className="text-sm text-muted-foreground">
            {new Date(news.publishedAt).toLocaleTimeString()}
          </span>
        </div>
        <h3 className="font-semibold line-clamp-2">{news.title}</h3>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3">
          {news.content}
        </p>
        <div className="mt-2 flex items-center justify-between">
          <Badge variant="outline">{news.category}</Badge>
          <div className="flex items-center space-x-1">
            <span className="text-xs">重要度:</span>
            <div className="flex">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full mr-1 ${
                    i < news.importanceScore ? 'bg-red-500' : 'bg-gray-200'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

```typescript
// frontend/hooks/useRealTimeNews.ts
import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { NewsItem } from '@/types/news';

export function useRealTimeNews() {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const socketInstance = io(process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000');
    
    socketInstance.on('connect', () => {
      setIsConnected(true);
    });
    
    socketInstance.on('disconnect', () => {
      setIsConnected(false);
    });
    
    socketInstance.on('new_news', (newsItem: NewsItem) => {
      setNews(prev => [newsItem, ...prev]);
    });
    
    socketInstance.on('urgent_news', (newsItem: NewsItem) => {
      // 显示紧急新闻通知
      if (Notification.permission === 'granted') {
        new Notification(newsItem.title, {
          body: newsItem.content.substring(0, 100) + '...',
          icon: '/favicon.ico'
        });
      }
      setNews(prev => [newsItem, ...prev]);
    });
    
    setSocket(socketInstance);
    
    return () => socketInstance.close();
  }, []);

  return { socket, news, isConnected };
}
```

### Sprint 4: Telegram 推送系统 (2 周)

#### 目标
实现完整的 Telegram Bot 推送功能

#### 任务清单

**Telegram Bot 开发**
- [ ] 创建 Telegram Bot 并获取 Token
- [ ] 实现 Bot 命令处理 (/start, /subscribe, /unsubscribe)
- [ ] 开发用户订阅管理
- [ ] 实现新闻推送格式化
- [ ] 添加内联键盘交互

**推送策略**
- [ ] 紧急新闻即时推送
- [ ] 定时新闻摘要推送
- [ ] 个性化推送设置
- [ ] 推送频率限制
- [ ] 用户偏好管理

**管理功能**
- [ ] 推送统计分析
- [ ] 用户行为追踪
- [ ] 推送效果监控
- [ ] 错误处理和重试机制

#### 技术实现示例

```python
# backend/app/services/telegram_bot.py
import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from app.models.user import User
from app.services.news_service import NewsService

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.bot = Bot(token)
        self.app = Application.builder().token(token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.app.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.app.add_handler(CommandHandler("settings", self.settings_command))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context):
        """处理 /start 命令"""
        user_id = update.effective_user.id
        username = update.effective_user.username
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
                print(f"Failed to send message to {user_id}: {e}")
    
    def format_news_message(self, news_item: dict) -> str:
        urgency_emoji = "🚨" if news_item.get('is_urgent') else "📰"
        importance_stars = "⭐" * news_item.get('importance_score', 1)
        return (
            f"{urgency_emoji} <b>{news_item['title']}</b>\n\n"
            f"📊 重要度: {importance_stars}\n"
            f"🏷️ 分类: {news_item['category']}\n"
            f"📡 来源: {news_item['source']}\n"
            f"⏰ 时间: {news_item['published_at']}\n\n"
            f"{news_item['content'][:200]}...\n\n"
            f"🔗 <a href=\"{news_item['url']}\">阅读全文</a>"
        )

# 推送任务（Celery 同步任务包装异步逻辑）
@celery_app.task
def send_urgent_news_alert(news_item_id: int):
    async def _send():
        news_item = await NewsService.get_news_by_id(news_item_id)
        subscribed_users = await User.get_subscribed_users()
        user_ids = [user.telegram_id for user in subscribed_users]
        bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
        await bot.send_news_alert(user_ids, news_item)
    asyncio.run(_send())
```

```python
# backend/app/services/telegram_notifier.py
from typing import List
from app.services.telegram_bot import TelegramBot
from app.models.user import User
from app.models.news import NewsItem

class TelegramNotifier:
    def __init__(self):
        self.bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
    
    async def notify_urgent_news(self, news_item: NewsItem):
        """推送紧急新闻"""
        users = await User.get_users_with_urgent_notifications()
        user_ids = [user.telegram_id for user in users if user.telegram_id]
        
        if user_ids:
            await self.bot.send_news_alert(user_ids, news_item.to_dict())
    
    async def send_daily_digest(self):
        """发送每日新闻摘要"""
        users = await User.get_users_with_daily_digest()
        
        for user in users:
            if user.telegram_id:
                # 获取用户个性化新闻
                news_items = await NewsService.get_personalized_news(
                    user_id=user.id,
                    limit=10
                )
                
                digest_message = self.format_daily_digest(news_items)
                await self.bot.bot.send_message(
                    chat_id=user.telegram_id,
                    text=digest_message,
                    parse_mode='HTML'
                )
    
    def format_daily_digest(self, news_items: List[NewsItem]) -> str:
        """格式化每日摘要"""
        message = "📊 <b>今日加密货币新闻摘要</b>\n\n"
        
        for i, item in enumerate(news_items, 1):
            message += f"{i}. <b>{item.title}</b>\n"
            message += f"   📡 {item.source} | ⭐ {item.importance_score}\n"
            message += f"   🔗 <a href='{item.url}'>阅读</a>\n\n"
        
        return message
```

### Sprint 5: AI 智能分析功能 (3 周)

#### 目标
集成 AI 功能进行新闻分析和智能推荐

#### 任务清单

**AI 服务集成**
- [ ] 集成 OpenAI API 进行新闻摘要
- [ ] 实现多语言翻译 (中英文)
- [ ] 开发市场影响评分算法
- [ ] 构建关键信息提取 (价格、代币、时间)
- [ ] 实现情感分析

**智能推荐系统**
- [ ] 用户行为数据收集
- [ ] 个性化推荐算法
- [ ] 热度算法实现
- [ ] 相关新闻推荐
- [ ] 智能分类优化

#### 技术实现示例

```python
# backend/app/services/ai_analyzer.py
from openai import AsyncOpenAI
from typing import Dict, List
import re

class AINewsAnalyzer:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def analyze_news(self, news_item: dict) -> dict:
        analysis = {}
        analysis['summary'] = await self.generate_summary(news_item['content'])
        analysis['market_impact'] = await self.calculate_market_impact(news_item)
        analysis['sentiment'] = await self.analyze_sentiment(news_item['content'])
        analysis['key_info'] = await self.extract_key_information(news_item['content'])
        return analysis
    
    async def generate_summary(self, content: str) -> str:
        try:
            resp = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一个专业的加密货币新闻分析师。请生成简洁中文摘要，突出关键信息。"},
                    {"role": "user", "content": f"请为以下新闻生成摘要（50字以内）：\n\n{content}"}
                ],
                max_tokens=100,
                temperature=0.3
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return "摘要生成失败"
    
    async def calculate_market_impact(self, news_item: dict) -> int:
        content = news_item['content'].lower()
        title = news_item['title'].lower()
        high_impact_keywords = [
            'regulation', 'ban', 'approval', 'etf', 'sec', 'fed',
            '监管', '禁止', '批准', '央行', '政策'
        ]
        medium_impact_keywords = [
            'partnership', 'adoption', 'launch', 'upgrade',
            '合作', '采用', '发布', '升级'
        ]
        score = 1
        text = f"{title} {content}"
        for keyword in high_impact_keywords:
            if keyword in text:
                score += 2
        for keyword in medium_impact_keywords:
            if keyword in text:
                score += 1
        if news_item['source'] in ['SEC', 'Federal Reserve', '央行', '证监会']:
            score += 2
        return min(score, 5)
    
    async def extract_key_information(self, content: str) -> dict:
        key_info = {'tokens': [], 'prices': [], 'dates': [], 'exchanges': []}
        token_pattern = r'\b[A-Z]{2,6}\b'
        tokens = re.findall(token_pattern, content)
        key_info['tokens'] = list(set(tokens))
        price_pattern = r'\$[\d,]+\.?\d*'
        prices = re.findall(price_pattern, content)
        key_info['prices'] = prices
        exchanges = ['Binance', 'Coinbase', 'OKX', 'Kraken', 'Huobi']
        for exchange in exchanges:
            if exchange.lower() in content.lower():
                key_info['exchanges'].append(exchange)
        return key_info
```

### Sprint 6: 性能优化与部署 (2 周)

#### 目标
优化系统性能并完成生产环境部署

#### 任务清单

**性能优化**
- [ ] 数据库查询优化和索引
- [ ] Redis 缓存策略优化
- [ ] API 响应时间优化
- [ ] 前端代码分割和懒加载
- [ ] 图片压缩和 CDN 配置

**监控和日志**
- [ ] 配置 Prometheus 监控
- [ ] 设置 Grafana 仪表板
- [ ] 实现错误报告系统
- [ ] 配置日志聚合
- [ ] 性能指标追踪

**部署配置**
- [ ] 生产环境 Docker 配置
- [ ] Kubernetes 部署文件
- [ ] CI/CD 流水线配置
- [ ] 域名和 SSL 证书配置
- [ ] 备份和恢复策略

## 项目文件结构

```
NEWRSS/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   ├── api/               # API 路由
│   │   ├── tasks/             # Celery 任务
│   │   └── utils/             # 工具函数
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic/               # 数据库迁移
├── frontend/                   # Next.js 前端
│   ├── app/                   # App Router
│   ├── components/            # React 组件
│   ├── hooks/                 # 自定义 Hooks
│   ├── lib/                   # 工具库
│   ├── types/                 # TypeScript 类型
│   ├── package.json
│   ├── next.config.js
│   └── Dockerfile
├── docker-compose.yml         # 开发环境配置
├── docker-compose.prod.yml    # 生产环境配置
├── nginx/                     # Nginx 配置
├── monitoring/                # 监控配置
└── docs/                      # 项目文档
```

## 实现细节补充

### FastAPI 配置：环境变量与 CORS

```python
# backend/app/core/settings.py
from pydantic_settings import BaseSettings
from pydantic import AnyUrl
from typing import List

class Settings(BaseSettings):
    ENV: str = "dev"
    DATABASE_URL: AnyUrl
    REDIS_URL: AnyUrl = "redis://redis:6379/0"
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_URL: str | None = None
    TELEGRAM_SECRET_TOKEN: str | None = None
    OPENAI_API_KEY: str | None = None
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.settings import settings

app = FastAPI(title="NEWRSS API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 API 路由...
```

### Socket.IO（python-socketio）与 FastAPI 的 ASGI 集成

```python
# backend/app/main.py （续）
import socketio

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=["*"],  # 生产环境建议精确白名单
)

@sio.event
async def connect(sid, environ):
    print("Socket connected", sid)

@sio.event
async def disconnect(sid):
    print("Socket disconnected", sid)

# 将 FastAPI 与 Socket.IO 组合为单个 ASGI 应用
from socketio import ASGIApp
asgi_app = ASGIApp(sio, other_asgi_app=app)

# 示例：在业务逻辑中广播新闻
async def broadcast_news(news_item: dict):
    await sio.emit('new_news', news_item)

async def broadcast_urgent(news_item: dict):
    await sio.emit('urgent_news', news_item)
```

运行示例（开发）：

```bash
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload
```

### Telegram Webhook 与 FastAPI 集成

```python
# backend/app/services/telegram_webhook.py
from fastapi import APIRouter, Request, Header, HTTPException
from telegram import Update
from telegram.ext import Application
from app.core.settings import settings
from app.services.telegram_bot import TelegramBot

router = APIRouter()

# 复用 TelegramBot 中的 Application 实例
bot = TelegramBot(settings.TELEGRAM_BOT_TOKEN)
application: Application = bot.app

@router.on_event("startup")
async def _startup():
    await application.initialize()
    await application.start()
    if settings.TELEGRAM_WEBHOOK_URL:
        await application.bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_SECRET_TOKEN,
            drop_pending_updates=True,
        )

@router.on_event("shutdown")
async def _shutdown():
    await application.stop()
    await application.shutdown()

@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # 验证 Telegram Secret Token（可选但强烈推荐）
    if settings.TELEGRAM_SECRET_TOKEN and (
        x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET_TOKEN
    ):
        raise HTTPException(status_code=401, detail="Invalid secret token")

    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}
```

在 `backend/app/main.py` 中注册路由：

```python
from app.services.telegram_webhook import router as telegram_router
app.include_router(telegram_router)
```

### docker-compose（开发环境）

```yaml
# docker-compose.yml
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: newrss
      POSTGRES_USER: newrss
      POSTGRES_PASSWORD: newrss
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    command: uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: postgresql+asyncpg://newrss:newrss@postgres:5432/newrss
      REDIS_URL: redis://redis:6379/0
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      TELEGRAM_WEBHOOK_URL: ${TELEGRAM_WEBHOOK_URL:-}
      TELEGRAM_SECRET_TOKEN: ${TELEGRAM_SECRET_TOKEN:-}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      CORS_ORIGINS: http://localhost:3000
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app

  celery-worker:
    build: ./backend
    command: celery -A app.tasks.news_crawler.celery_app worker -l INFO
    environment:
      DATABASE_URL: postgresql+asyncpg://newrss:newrss@postgres:5432/newrss
      REDIS_URL: redis://redis:6379/0
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    depends_on:
      - backend
      - redis
      - postgres
    volumes:
      - ./backend:/app

  celery-beat:
    build: ./backend
    command: celery -A app.tasks.news_crawler.celery_app beat -l INFO
    environment:
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    command: npm run dev
    environment:
      NEXT_PUBLIC_WS_URL: http://localhost:8000
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    depends_on:
      - backend

volumes:
  pg_data:
```

注意：生产环境请单独提供 `docker-compose.prod.yml`，并使用 Webhook 而非轮询，精确配置 CORS、Secret、CDN 与反向代理（Nginx）。

## 关键技术决策

### 为什么选择 Python + FastAPI?
- **高性能**: FastAPI 基于 Starlette 和 Pydantic，性能接近 Node.js
- **异步支持**: 原生支持 async/await，适合高并发数据抓取
- **生态丰富**: 丰富的数据处理和机器学习库
- **开发效率**: 自动生成 API 文档，类型提示支持

### 为什么选择 Next.js + TypeScript?
- **全栈能力**: API Routes 可以处理简单的后端逻辑
- **SEO 友好**: SSR/SSG 支持，有利于搜索引擎优化
- **开发体验**: 热重载、TypeScript 支持、丰富的生态
- **性能优化**: 自动代码分割、图片优化等

### Telegram 推送的优势
- **即时性**: 推送延迟低，适合紧急新闻通知
- **用户基数**: 加密货币社区广泛使用 Telegram
- **交互性**: 支持内联键盘、命令等丰富交互
- **免费**: 无需额外的推送服务费用

## 部署和运维

### 开发环境启动
```bash
# 克隆项目
git clone <repository-url>
cd NEWRSS

# 启动开发环境
docker-compose up -d

# 安装前端依赖
cd frontend && npm install

# 启动前端开发服务器
npm run dev
```

### 生产环境部署
```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 运行数据库迁移
docker-compose exec backend alembic upgrade head
```

## 成功指标

### 技术指标
- **响应时间**: API 响应时间 < 200ms
- **推送延迟**: 新闻推送延迟 < 5 秒
- **系统可用性**: 99.9% 正常运行时间
- **并发处理**: 支持 1000+ 并发用户

### 业务指标
- **新闻覆盖**: 每日聚合 500+ 新闻
- **用户增长**: 月活跃用户增长 20%
- **推送效果**: 推送点击率 > 15%
- **用户满意度**: 用户评分 > 4.5/5

## 风险评估与应对

### 技术风险
- **API 限制**: 各平台 API 调用限制 → 实现多账号轮换和缓存策略
- **数据质量**: 爬虫数据不准确 → 多源验证和人工审核机制
- **系统负载**: 高并发导致系统崩溃 → 负载均衡和自动扩缩容

### 业务风险
- **法律合规**: 数据抓取的法律风险 → 遵守 robots.txt 和服务条款
- **竞争压力**: 市场竞争激烈 → 专注差异化功能和用户体验
- **用户流失**: 推送频率过高导致用户取消订阅 → 智能推送策略

## 后续发展规划

### 短期目标 (3-6 个月)
- 完成核心功能开发和测试
- 获得 1000+ 活跃用户
- 建立稳定的数据源和推送机制

### 中期目标 (6-12 个月)
- 集成更多数据源和 AI 功能
- 开发移动端应用
- 实现用户付费订阅模式

### 长期目标 (1-2 年)
- 成为加密货币新闻聚合领域的领导者
- 开放 API 服务，建立开发者生态
- 探索区块链和 Web3 集成机会

---

**项目负责人**: 开发团队  
**预计完成时间**: 14-16 周  
**技术栈**: Python + FastAPI + Next.js + TypeScript + PostgreSQL + Redis + Telegram Bot API  
**部署方式**: Docker + Kubernetes + CI/CD
