# NEWRSS - 加密货币新闻聚合平台

基于 Python 后端 + Next.js + TypeScript 前端的加密货币新闻聚合平台，实现类似方程式新闻的毫秒级新闻推送、多源聚合和 AI 智能分析功能，支持 Telegram 实时推送。

## 技术栈

### 后端
- **框架**: Python 3.12 + FastAPI
- **数据库**: PostgreSQL + SQLAlchemy 2.x (AsyncSession)
- **缓存**: Redis
- **消息队列**: Celery + Redis
- **实时通信**: python-socketio v5
- **推送服务**: Telegram Bot API
- **AI 分析**: OpenAI API

### 前端
- **框架**: Next.js 15 + TypeScript
- **UI 库**: Tailwind CSS + Shadcn/ui
- **状态管理**: Zustand
- **实时通信**: Socket.io-client
- **构建工具**: Turbopack

## 快速开始

### 环境准备

1. 复制环境变量文件：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入必要的配置：
   - `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
   - `OPENAI_API_KEY`: OpenAI API Key (可选)
   - `SECRET_KEY`: JWT 密钥

### 使用 Docker 启动

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 手动启动开发环境

#### 后端

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动 API 服务
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload

# 启动 Celery Worker (新终端)
celery -A app.tasks.news_crawler.celery_app worker --loglevel=info

# 启动 Celery Beat (新终端)
celery -A app.tasks.news_crawler.celery_app beat --loglevel=info
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 功能特性

- ⚡ **毫秒级推送**: 高频数据抓取，30秒轮询多个新闻源
- 🤖 **AI 智能分析**: 自动摘要、情感分析、市场影响评分
- 📱 **Telegram 推送**: 紧急新闻即时推送，支持个性化订阅
- 🔄 **实时更新**: WebSocket 实时新闻推送
- 🎯 **智能过滤**: 基于重要性、分类、关键词的个性化过滤
- 📊 **数据聚合**: 多源新闻聚合，自动去重

## API 文档

启动后端服务后，访问以下地址查看 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
NEWRSS/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── core/              # 核心配置
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务逻辑
│   │   ├── tasks/             # Celery 任务
│   │   └── utils/             # 工具函数
│   ├── alembic/               # 数据库迁移
│   └── requirements.txt
├── frontend/                   # Next.js 前端
│   ├── app/                   # App Router
│   ├── components/            # React 组件
│   ├── hooks/                 # 自定义 Hooks
│   ├── lib/                   # 工具库
│   ├── types/                 # TypeScript 类型
│   └── package.json
├── docker-compose.yml         # 开发环境
└── .env.example              # 环境变量示例
```

## 开发指南

### 添加新的新闻源

在 `backend/app/tasks/news_crawler.py` 中的 `sources` 列表添加新的 RSS 源：

```python
sources = [
    {
        "url": "https://example.com/rss",
        "name": "Example News",
        "category": "news"
    }
]
```

### 自定义 AI 分析

在 `backend/app/services/ai_analyzer.py` 中自定义分析逻辑。

### 添加新的 Telegram 命令

在 `backend/app/services/telegram_bot.py` 中添加新的命令处理器。

## 生产部署

参考 `docker-compose.prod.yml` 进行生产环境部署，确保：
- 使用 HTTPS 和域名
- 配置 Nginx 反向代理
- 设置 Telegram Webhook
- 启用监控和日志系统