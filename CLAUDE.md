# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Frontend (Next.js 15 + TypeScript)
```bash
cd frontend

# Development
npm run dev           # Start dev server with Turbopack (port 3000)
npm run build         # Production build
npm run start         # Start production server
npm run lint          # ESLint check
npm run type-check    # TypeScript check (no emit)

# Testing
npm test              # Run Jest tests
npm run test:watch    # Watch mode testing
npm run test:coverage # Generate coverage report
```

### Backend (Python 3.12 + FastAPI)
```bash
cd backend

# Development
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload  # API server
alembic upgrade head                                            # Run migrations
celery -A app.tasks.news_crawler.celery_app worker --loglevel=info    # Celery worker
celery -A app.tasks.news_crawler.celery_app beat --loglevel=info      # Celery scheduler

# Testing
pytest                    # Run all tests (requires 100% coverage)
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests
pytest --cov=app         # Coverage report
```

### Full Stack Development
```bash
# Start all services with Docker
docker-compose up -d

# View service status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Architecture Overview

### Real-Time News Aggregation System
This is a cryptocurrency news aggregation platform with millisecond-level news delivery, featuring:

- **Backend**: FastAPI with async SQLAlchemy 2.x, PostgreSQL, Redis, Celery
- **Frontend**: Next.js 15 with App Router, TypeScript, Tailwind CSS, Shadcn/ui
- **Real-time**: Socket.io for WebSocket communications, 30-second RSS polling
- **Intelligence**: OpenAI integration for news analysis, sentiment scoring, importance ranking
- **Notifications**: Telegram Bot API for instant alerts on urgent news

### Key Components

#### Backend Services (app/services/)
- `rss_fetcher.py`: RSS feed parsing with content hashing for deduplication
- `ai_analyzer.py`: OpenAI-powered news analysis and sentiment scoring
- `telegram_bot.py`: Bot command handlers and notification system
- `telegram_notifier.py`: Urgent news push notifications
- `translator.py`: Multi-language support system

#### Frontend Architecture
- **State Management**: Zustand for global state
- **Real-time Updates**: Socket.io client integration via `useRealTimeNews` hook
- **UI Components**: Shadcn/ui + Radix UI primitives
- **Styling**: Tailwind CSS with custom config

#### Data Flow
1. **Collection**: Celery Beat triggers RSS crawling every 30 seconds
2. **Processing**: Content hashing, AI analysis, urgency detection
3. **Storage**: PostgreSQL with SQLAlchemy async sessions
4. **Distribution**: Socket.io broadcasts + Telegram notifications
5. **Display**: Real-time frontend updates via WebSocket

### Environment Configuration
- Database: PostgreSQL (dev: docker, test: sqlite)
- Cache/Queue: Redis for Celery and caching
- External APIs: OpenAI (optional), Telegram Bot API
- CORS: Configured for localhost:3000 frontend

### News Processing Pipeline
1. RSS sources defined in `news_crawler.py:28-54`
2. Content fetched with deduplication via content hashes
3. Urgency classification using keyword detection
4. Importance scoring (1-5 scale) based on source + keywords
5. AI analysis for sentiment and market impact (when OpenAI configured)
6. Real-time broadcast to connected clients

### Testing Strategy
- **Backend**: pytest with 100% coverage requirement, async test support
- **Frontend**: Jest with jsdom, React Testing Library
- **Markers**: unit, integration, slow test categories
- **Coverage**: HTML reports in htmlcov/, XML for CI/CD

## Development Notes

### Adding RSS Sources
Modify the `sources` list in `backend/app/tasks/news_crawler.py:28-54` with new RSS feed configurations.

### Telegram Bot Commands
Extend command handlers in `backend/app/services/telegram_bot.py` for new bot functionality.

### Real-time Features
WebSocket events are handled through Socket.io with `broadcast_news()` and `broadcast_urgent()` functions in `main.py:64-68`.

### Database Schema
Core models: `NewsItem` (with AI analysis fields) and `NewsSource` in `backend/app/models/news.py`.