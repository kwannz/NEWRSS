# 🚀 NEWRSS Local Production Deployment Guide

## Current Status: Building Containers...

Your NEWRSS platform is currently deploying with Docker Compose. Here's what's happening and what to expect:

## ⏳ Deployment Progress

### Currently Building:
- ✅ **PostgreSQL**: Container ready
- ✅ **Redis**: Container ready  
- ✅ **Backend**: Python dependencies installed
- ✅ **Celery Worker**: Background tasks ready
- ✅ **Celery Beat**: Scheduler ready
- 🔄 **Frontend**: Building Node.js dependencies (this takes 5-10 minutes)

## 📋 What Happens Next

### 1. Container Startup Sequence (2-3 minutes)
```bash
postgres → redis → backend → celery-worker → celery-beat → frontend
```

### 2. Database Initialization (1 minute)
- PostgreSQL starts with newrss database
- Backend connects and runs any pending migrations
- Tables created for users, news, preferences

### 3. Service Health Checks (30 seconds)
- All services report healthy status
- WebSocket connections established
- Background news crawling begins

## 🎯 Access Your Deployed Application

### Once deployment completes, access at:
- **📱 Frontend Dashboard**: http://localhost:3000
- **🔗 API Documentation**: http://localhost:8000/docs
- **⚡ Health Check**: http://localhost:8000/health
- **📊 Admin Interface**: http://localhost:8000/admin

## ✅ Immediate Post-Deployment Tasks

### 1. Verify All Services (2 minutes)
```bash
# Check container status
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000
```

### 2. Configure External APIs (Optional - 5 minutes)
Edit `.env` file to add:
```bash
# For Telegram bot functionality
TELEGRAM_BOT_TOKEN=your_bot_token_from_@BotFather

# For AI-powered daily digest
OPENAI_API_KEY=your_openai_api_key
```

### 3. Test Core Functionality (5 minutes)
- Visit http://localhost:3000
- Register a new user account
- Check real-time news updates
- Test WebSocket connection (news should update automatically)

## 🔧 Configuration Options

### Telegram Bot Setup (Optional)
```bash
# 1. Create bot with @BotFather on Telegram
# 2. Get bot token and add to .env
# 3. Restart backend: docker-compose restart backend
# 4. Test with /start command to your bot
```

### OpenAI Integration (Optional)
```bash
# 1. Get API key from OpenAI platform
# 2. Add to .env file
# 3. Restart services: docker-compose restart
# 4. Daily digest will include AI analysis
```

## 📊 Monitoring Your Deployment

### Real-time Status Checks
```bash
# View live logs
docker-compose logs -f

# Check resource usage
docker stats

# Monitor database
docker-compose exec postgres psql -U newrss -d newrss -c "SELECT COUNT(*) FROM news_items;"

# Check Redis
docker-compose exec redis redis-cli info stats
```

### Performance Monitoring
- **News Processing**: Check logs for RSS crawling activity
- **WebSocket**: Monitor connection count and broadcast events
- **Database**: Track query performance and connection pool usage
- **Memory**: Monitor container memory usage for optimization

## 🚨 Troubleshooting

### Common Issues and Solutions

**Frontend not loading:**
```bash
# Check build completion
docker-compose logs frontend

# Force rebuild if needed
docker-compose build frontend --no-cache
docker-compose up -d frontend
```

**Backend API errors:**
```bash
# Check database connection
docker-compose logs backend | grep -i database

# Check environment variables
docker-compose exec backend env | grep DATABASE_URL
```

**No news appearing:**
```bash
# Check Celery worker
docker-compose logs celery-worker

# Manual news fetch test
docker-compose exec backend python -c "from app.tasks.news_crawler import fetch_news; fetch_news()"
```

## 🎯 Success Indicators

### Your deployment is successful when:
- ✅ All containers show "Up" status in `docker-compose ps`
- ✅ Frontend loads at http://localhost:3000
- ✅ API responds at http://localhost:8000/health
- ✅ Real-time news updates appear automatically
- ✅ User registration and login work correctly
- ✅ WebSocket connection shows "Connected" status

### Expected Timeframe:
- **Container Build**: 5-10 minutes (first time)
- **Service Startup**: 2-3 minutes
- **Total Deployment**: 7-13 minutes

## 📱 Using Your Deployed NEWRSS

### 1. Web Interface
- Visit http://localhost:3000
- Create account or login
- Browse real-time cryptocurrency news
- Configure notification preferences
- Use advanced filtering (categories, importance)

### 2. Telegram Bot (if configured)
- Find your bot on Telegram
- Send `/start` to register
- Use `/settings` to configure preferences
- Receive personalized news notifications
- Get daily AI-powered market digest

### 3. API Access
- Explore API at http://localhost:8000/docs
- Authentication endpoints for user management
- News endpoints with filtering capabilities
- WebSocket events for real-time integration

Your NEWRSS platform will now operate 24/7 on your local machine, continuously monitoring cryptocurrency news sources and delivering personalized updates to users in real-time!