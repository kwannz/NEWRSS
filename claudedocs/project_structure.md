# 🏗️ Project Structure Documentation

## 📂 Directory Overview

```
NEWRSS/
├── backend/                    # Python FastAPI Backend
│   ├── app/                   # Application code
│   │   ├── api/              # API route handlers
│   │   ├── core/             # Core configurations
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic services
│   │   ├── tasks/            # Celery background tasks
│   │   └── main.py          # FastAPI application entry
│   ├── alembic/              # Database migrations
│   ├── tests/                # Test suite (76 files)
│   ├── static/               # Static HTML files
│   └── requirements.txt      # Python dependencies
├── frontend/                  # Next.js 15 Frontend
│   ├── app/                  # Next.js App Router
│   ├── components/           # React components
│   ├── hooks/                # Custom React hooks
│   ├── types/                # TypeScript definitions
│   ├── tests/                # Frontend test suite
│   └── package.json          # Node dependencies
├── claudedocs/               # Generated documentation
├── .claude/                  # SuperClaude framework
├── docker-compose.yml        # Development environment
├── docker-compose.prod.yml   # Production environment
└── README.md                 # Project overview
```

---

## 🐍 Backend Architecture

### Core Application (`backend/app/`)

#### API Layer (`api/`)
- **`auth.py`** (102 lines): User authentication, JWT token management
  - Routes: `/auth/register`, `/auth/token`, `/auth/me`
  - Features: User registration, login, current user retrieval
  
- **`news.py`** (177 lines): News content management  
  - Routes: `/news/`, `/news/{id}`, `/news/broadcast`
  - Features: News listing, filtering, WebSocket broadcasting
  
- **`sources.py`** (267 lines): RSS source management
  - Routes: `/sources/`, `/sources/categories`, `/sources/stats`, CRUD operations
  - Features: Source CRUD, statistics, category management

#### Core Infrastructure (`core/`)
- **`settings.py`** (20 lines): Environment configuration via Pydantic
- **`database.py`** (24 lines): Async SQLAlchemy setup with session management
- **`auth.py`** (40 lines): JWT utilities for token creation/verification
- **`redis.py`**: Redis connection management

#### Data Models (`models/`)
- **`news.py`** (39 lines): NewsItem and NewsSource models
  - `NewsItem`: 18 fields including AI analysis results
  - `NewsSource`: 11 fields for RSS feed configuration
  
- **`user.py`**: User authentication model
- **`subscription.py`**: User subscription preferences

#### Business Services (`services/`)
- **`rss_fetcher.py`** (94 lines): RSS feed parsing and content hashing
- **`ai_analyzer.py`** (86 lines): OpenAI integration for news analysis
- **`telegram_bot.py`** (98 lines): Telegram bot command handlers
- **`telegram_notifier.py`** (28 lines): Urgent news notifications
- **`telegram_webhook.py`** (66 lines): Webhook endpoint management
- **`translator.py`** (170 lines): Multi-language translation system

#### Background Tasks (`tasks/`)
- **`news_crawler.py`** (130 lines): Celery scheduler for RSS polling
  - 30-second news crawling
  - Exchange announcement monitoring
  - Urgency detection and importance scoring
  
- **`ai_analyzer.py`** (53 lines): Async AI analysis tasks
- **`news_aggregator.py`** (69 lines): Daily digest generation
- **`crawler.py`** (115 lines): Alternative crawler implementation

### Database Layer
- **`alembic/`**: Database migration management
- **SQLAlchemy 2.x**: Async ORM with PostgreSQL support
- **Redis**: Caching and Celery message broker

### Testing Infrastructure (`tests/`)
- **76 test files** with 100% coverage requirement
- **Async testing**: pytest-asyncio for async code testing
- **Test categories**: unit, integration, slow test markers
- **Mock services**: Comprehensive mocking for external APIs

---

## ⚛️ Frontend Architecture

### Next.js 15 Application (`frontend/`)

#### App Router (`app/`)
- **`page.tsx`** (55 lines): Main news dashboard
- **`layout.tsx`** (22 lines): Root layout with metadata
- **`globals.css`**: Tailwind CSS global styles

#### React Components (`components/`)
- **`NewsCard.tsx`** (62 lines): News item display component
- **`ui/`**: Shadcn/ui component library
  - `card.tsx`, `badge.tsx`: Base UI primitives

#### Custom Hooks (`hooks/`)
- **`useRealTimeNews.ts`** (59 lines): Socket.io WebSocket integration
  - Real-time news updates
  - Browser notification support
  - Connection state management

#### Type Definitions (`types/`)
- **`news.ts`** (50 lines): TypeScript interfaces
  - `NewsItem`, `NewsFilter`, `NewsSource`, `User`
  - Complete type safety for API interactions

### State Management
- **Zustand**: Lightweight state management (referenced in useRealTimeNews)
- **Socket.io Client**: Real-time communication with backend
- **SWR**: Data fetching and caching (in package.json)

---

## 🚀 Infrastructure Components

### Containerization
- **`Dockerfile`**: Multi-stage builds for both backend/frontend
- **`docker-compose.yml`**: Development environment orchestration
  - PostgreSQL database
  - Redis cache/broker
  - Backend API service
  - Frontend Next.js service
  - Celery worker/beat services

### Development Tools
- **`nginx/`**: Reverse proxy configuration
- **`.playwright-mcp/`**: Browser testing setup
- **`.github/workflows/`**: CI/CD pipeline configuration

---

## 🔄 Data Flow Architecture

### Real-time News Pipeline
```
RSS Sources → Celery Worker → Content Processing → Database Storage
     ↓              ↓               ↓                    ↓
AI Analysis → Urgency Detection → WebSocket Broadcast → Frontend Updates
     ↓              ↓               ↓                    ↓  
Telegram Bot → Push Notifications → User Engagement → Feedback Loop
```

### Service Dependencies
```
Frontend (port 3000)
    ↓
Backend API (port 8000)
    ↓
┌─ PostgreSQL (port 5432)
├─ Redis (port 6379)
├─ Celery Worker
├─ Celery Beat
└─ External APIs (OpenAI, Telegram)
```

---

## 📊 Component Metrics

### Backend Components
| Component | Files | Lines | Purpose |
|-----------|-------|-------|---------|
| API Routes | 3 | 546 | HTTP endpoint handlers |
| Services | 6 | 541 | Business logic layer |
| Models | 3 | 89 | Data structure definitions |
| Tasks | 4 | 367 | Background processing |
| Core | 4 | 84 | Infrastructure setup |
| Tests | 76 | ~8000+ | Quality assurance |

### Frontend Components
| Component | Files | Lines | Purpose |
|-----------|-------|-------|---------|
| Pages | 2 | 77 | Next.js App Router |
| Components | 4 | ~200 | UI component library |
| Hooks | 1 | 59 | Custom React hooks |
| Types | 1 | 50 | TypeScript definitions |
| Tests | 2 | ~100 | Component testing |

---

## 🔗 Cross-References

### API ↔ Frontend Integration
- **News API** → `useRealTimeNews` hook → Live updates
- **Authentication** → JWT tokens → Protected routes
- **WebSocket** → Socket.io client → Real-time notifications

### Backend Service Integration
- **RSS Fetcher** → **AI Analyzer** → **Telegram Notifier**
- **News Crawler** → **Database Models** → **API Routes**
- **Settings** → **All Services** → Environment configuration

### External Integrations
- **OpenAI API** (`ai_analyzer.py:9`) → News analysis
- **Telegram API** (`telegram_bot.py`) → User notifications  
- **RSS Feeds** (`news_crawler.py:28-54`) → Content sources

---

## 🛠️ Development Patterns

### Backend Patterns
- **Async/Await**: All database operations use async patterns
- **Dependency Injection**: FastAPI's Depends() for service injection
- **Repository Pattern**: Database access through SQLAlchemy models
- **Service Layer**: Business logic separated from API routes

### Frontend Patterns
- **App Router**: Next.js 15 file-based routing
- **Component Composition**: Shadcn/ui + custom components
- **Custom Hooks**: Encapsulated state and side effects
- **TypeScript**: Full type safety with interface definitions

---

*Documentation generated from code analysis | Last updated: 2025-09-01*