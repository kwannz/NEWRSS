# 🔄 Development Workflows

## 🚀 Quick Start Workflow

### 1. Environment Setup
```bash
# Clone and configure
cp .env.example .env
# Edit .env with required tokens: TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, SECRET_KEY
```

### 2. Docker Development (Recommended)
```bash
# Start all services
docker-compose up -d

# Monitor services
docker-compose ps
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. Manual Development
```bash
# Backend setup
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:asgi_app --host 0.0.0.0 --port 8000 --reload

# Start background workers (separate terminals)
celery -A app.tasks.news_crawler.celery_app worker --loglevel=info
celery -A app.tasks.news_crawler.celery_app beat --loglevel=info

# Frontend setup (separate terminal)
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing Workflows

### Backend Testing
```bash
cd backend

# Run all tests (100% coverage required)
pytest

# Specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests
pytest -m "not slow"     # Skip slow tests

# Coverage reporting
pytest --cov=app --cov-report=html:htmlcov
```

### Frontend Testing
```bash
cd frontend

# Run tests
npm test                 # Run all tests
npm run test:watch       # Watch mode
npm run test:coverage    # Generate coverage

# Type checking
npm run type-check       # TypeScript validation
npm run lint             # ESLint check
```

---

## 🔄 Development Cycle

### Feature Development Workflow
1. **Branch Creation**: `git checkout -b feature/news-filtering`
2. **Backend Development**:
   - Create/modify models in `app/models/`
   - Implement business logic in `app/services/`
   - Add API endpoints in `app/api/`
   - Write comprehensive tests
3. **Frontend Development**:
   - Update TypeScript types in `types/`
   - Create/modify components
   - Add custom hooks if needed
   - Update pages/layouts
4. **Integration Testing**: Test API + Frontend integration
5. **Quality Checks**: Run linting, type checking, tests
6. **Documentation**: Update relevant docs

### Code Quality Checklist
- [ ] All new code has tests (100% coverage requirement)
- [ ] TypeScript types are properly defined
- [ ] No print statements (use structured logging)
- [ ] No TODO comments in production code
- [ ] Error handling with specific exceptions
- [ ] Environment variables for configuration

---

## 🗄️ Database Workflows

### Migration Management
```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check migration status
alembic current
alembic history
```

### Data Population
```bash
# Populate RSS sources
python populate_rss_sources.py

# Generate test news data
python populate_news.py

# Generate AI summaries
python generate_summaries.py
```

---

## 🔄 Background Task Management

### Celery Operations
```bash
# Start worker (processes RSS feeds)
celery -A app.tasks.news_crawler.celery_app worker --loglevel=info --concurrency=4

# Start scheduler (triggers periodic tasks)
celery -A app.tasks.news_crawler.celery_app beat --loglevel=info

# Monitor tasks
celery -A app.tasks.news_crawler.celery_app flower  # Web UI monitoring

# Inspect tasks
celery -A app.tasks.news_crawler.celery_app inspect active
celery -A app.tasks.news_crawler.celery_app inspect scheduled
```

### Task Schedule
- **News Crawling**: Every 30 seconds (`crawl_news_sources`)
- **Exchange Monitoring**: Every 60 seconds (`monitor_exchange_announcements`)
- **AI Analysis**: Triggered by new news items
- **Daily Digest**: Daily aggregation for Telegram subscribers

---

## 🎯 Feature Development Patterns

### Adding New RSS Sources
1. **Configuration** (`news_crawler.py:28-54`):
```python
sources = [
    {
        "url": "https://example.com/rss",
        "name": "Example News",
        "category": "news"
    }
]
```

2. **Database Registration**: Use `populate_rss_sources.py`
3. **Testing**: Add source to test suite
4. **Monitoring**: Verify in source stats API

### Implementing New API Endpoints
1. **Model Definition**: Add/update in `app/models/`
2. **Service Logic**: Implement in `app/services/`
3. **API Route**: Create in `app/api/`
4. **Response Model**: Define Pydantic models
5. **Frontend Types**: Update TypeScript interfaces
6. **Tests**: Add comprehensive test coverage

### Adding Telegram Commands
1. **Command Handler** (`telegram_bot.py`):
```python
async def handle_new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Implementation
    pass

application.add_handler(CommandHandler("new_command", handle_new_command))
```

2. **Database Integration**: Update user preferences if needed
3. **Testing**: Mock Telegram API responses

---

## 🔍 Debugging Workflows

### Backend Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with reload for development
uvicorn app.main:asgi_app --reload --log-level debug

# Database query debugging (SQLAlchemy echo)
# Set ENV=dev in settings for SQL query logging
```

### Frontend Debugging
```bash
# Next.js debug mode
npm run dev
# Automatic TypeScript checking and hot reload

# WebSocket debugging
# Check browser dev tools Network tab for WebSocket connections
```

### Real-time System Debugging
1. **WebSocket Testing**: Use browser dev tools or Postman
2. **Celery Monitoring**: Check worker logs for RSS processing
3. **Database Queries**: Monitor SQL logs with SQLAlchemy echo
4. **AI Integration**: Test with/without OpenAI API key

---

## 📦 Deployment Workflows

### Production Deployment
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d

# Database migration in production
docker-compose exec backend alembic upgrade head

# Monitor production logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Environment Configuration
- **Development**: `.env` with localhost services
- **Production**: Environment variables with secure secrets
- **Testing**: Temporary databases and mock services

---

## 🔧 Maintenance Workflows

### Regular Maintenance Tasks
```bash
# Update dependencies
cd backend && pip-compile requirements.in
cd frontend && npm update

# Database maintenance
# Backup: pg_dump newrss > backup.sql
# Cleanup old news: Custom script needed

# Log rotation
# Docker handles log rotation automatically
```

### Monitoring and Health Checks
- **Health Endpoint**: `/health` for service status
- **API Documentation**: `/docs` for Swagger UI
- **Database Metrics**: Monitor connection pools
- **Celery Health**: Worker and beat status monitoring

---

## 🚨 Troubleshooting Guide

### Common Issues

#### Backend Issues
- **Database Connection**: Check PostgreSQL service and connection string
- **Celery Not Starting**: Verify Redis connection and worker registration
- **API Errors**: Check logs with `docker-compose logs backend`
- **Migration Errors**: Review migration files and database state

#### Frontend Issues  
- **Build Failures**: Check TypeScript errors with `npm run type-check`
- **WebSocket Connection**: Verify backend Socket.io service
- **Component Errors**: Test isolation with `npm test`

#### Integration Issues
- **CORS Errors**: Verify CORS_ORIGINS in backend settings
- **Authentication**: Check JWT token validity and expiration
- **Real-time Updates**: Verify WebSocket connection and event handlers

### Debugging Commands
```bash
# Check service status
docker-compose ps

# Restart specific service
docker-compose restart backend

# Database access
docker-compose exec postgres psql -U newrss -d newrss

# Redis access  
docker-compose exec redis redis-cli
```

---

*Development workflows optimized for NEWRSS real-time news platform*