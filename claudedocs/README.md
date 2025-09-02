# 📚 NEWRSS Documentation Index

Welcome to the comprehensive documentation for the NEWRSS cryptocurrency news aggregation platform.

---

## 🗂️ Documentation Navigation

### 📋 Project Overview
- **[Main README](../README.md)** - Project overview and quick start guide
- **[CLAUDE.md](../CLAUDE.md)** - Claude Code development guidance
- **[Project Structure](./project_structure.md)** - Detailed codebase architecture

### 🔧 Development Guides
- **[Development Workflows](./development_workflows.md)** - Complete development lifecycle
- **[API Documentation](./api_documentation.md)** - REST API and WebSocket reference

### 📊 Analysis Reports
- **[Code Analysis Report](./analysis_report.md)** - Quality, security, and performance assessment

---

## 🎯 Quick Reference

### Essential Commands
```bash
# Start development environment
docker-compose up -d

# Run backend tests
cd backend && pytest

# Run frontend tests  
cd frontend && npm test

# Type checking
cd frontend && npm run type-check
```

### Key Endpoints
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Architecture Components
- **Backend**: FastAPI + SQLAlchemy 2.x + PostgreSQL + Redis + Celery
- **Frontend**: Next.js 15 + TypeScript + Tailwind CSS + Socket.io
- **Real-time**: WebSocket news broadcasts with urgency classification
- **AI**: OpenAI integration for news analysis and sentiment scoring

---

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   External      │
│   (Next.js 15)  │◄──►│   (FastAPI)     │◄──►│   (RSS/APIs)    │
│                 │    │                 │    │                 │
│ • TypeScript    │    │ • AsyncIO       │    │ • RSS Feeds     │
│ • Socket.io     │    │ • PostgreSQL    │    │ • OpenAI API    │
│ • Zustand       │    │ • Redis         │    │ • Telegram API  │
│ • Tailwind CSS  │    │ • Celery        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 📖 Development Topics

### 🐍 Backend Development
- **[API Routes](./api_documentation.md#authentication-endpoints)** - REST API endpoints
- **[Database Models](./project_structure.md#data-models-models)** - SQLAlchemy model definitions
- **[Background Tasks](./project_structure.md#background-tasks-tasks)** - Celery task processing
- **[Services Layer](./project_structure.md#business-services-services)** - Business logic components

### ⚛️ Frontend Development
- **[Components](./project_structure.md#react-components-components)** - UI component library
- **[Hooks](./project_structure.md#custom-hooks-hooks)** - React custom hooks
- **[State Management](./project_structure.md#state-management)** - Zustand integration
- **[Real-time Updates](./development_workflows.md#real-time-system-debugging)** - WebSocket integration

### 🔄 Integration Patterns
- **[Real-time Pipeline](./project_structure.md#real-time-news-pipeline)** - News processing flow
- **[Service Dependencies](./project_structure.md#service-dependencies)** - Component relationships
- **[API Integration](./project_structure.md#api--frontend-integration)** - Frontend ↔ Backend communication

---

## 🛠️ Maintenance Guides

### Quality Assurance
- **[Code Quality](./analysis_report.md#code-quality-analysis)** - Quality metrics and standards
- **[Security Assessment](./analysis_report.md#security-assessment)** - Security review and recommendations
- **[Performance Analysis](./analysis_report.md#performance-analysis)** - Performance optimization guide

### Operational Tasks
- **[Database Management](./development_workflows.md#database-workflows)** - Migration and data management
- **[Task Monitoring](./development_workflows.md#background-task-management)** - Celery task supervision
- **[Deployment](./development_workflows.md#deployment-workflows)** - Production deployment guide

---

## 🔍 Code Navigation

### Key Files Reference
| Component | File Path | Description |
|-----------|-----------|-------------|
| **Main Backend** | `backend/app/main.py:25` | FastAPI application setup |
| **News API** | `backend/app/api/news.py:53` | News endpoints |
| **RSS Crawler** | `backend/app/tasks/news_crawler.py:26` | Background RSS processing |
| **WebSocket** | `backend/app/main.py:56` | Socket.io event handlers |
| **Frontend Page** | `frontend/app/page.tsx` | Main dashboard |
| **Real-time Hook** | `frontend/hooks/useRealTimeNews.ts:6` | WebSocket integration |

### Configuration Files
| Purpose | File | Key Settings |
|---------|------|-------------|
| **Backend Config** | `backend/app/core/settings.py:5` | Environment variables |
| **Database** | `backend/app/core/database.py:5` | Async SQLAlchemy setup |
| **Frontend Config** | `frontend/next.config.js:2` | Next.js configuration |
| **Testing** | `backend/pytest.ini:1` | Test configuration |

---

## 🚨 Important Notes

### Security Considerations
- **Production Secrets**: Update `SECRET_KEY` and API tokens in production
- **CORS Origins**: Restrict CORS origins for production deployment
- **Rate Limiting**: Implement API rate limiting before production

### Performance Optimization
- **Database Indexing**: News queries use proper indexes
- **Caching Strategy**: Redis available for caching implementation  
- **Connection Pooling**: SQLAlchemy async session management
- **Background Processing**: Celery handles RSS processing efficiently

### Development Best Practices
- **100% Test Coverage**: Required for backend code
- **Type Safety**: Full TypeScript coverage for frontend
- **Error Handling**: Specific exception handling, no bare except blocks
- **Structured Logging**: Replace print statements with proper logging

---

## 📞 Support and Resources

### External Documentation
- **FastAPI**: https://fastapi.tiangolo.com/
- **Next.js 15**: https://nextjs.org/docs
- **SQLAlchemy 2.x**: https://docs.sqlalchemy.org/en/20/
- **Celery**: https://docs.celeryq.dev/
- **Socket.io**: https://socket.io/docs/

### Project-Specific Resources
- **API Documentation**: http://localhost:8000/docs (when running)
- **ReDoc**: http://localhost:8000/redoc (alternative API docs)
- **Coverage Reports**: `backend/htmlcov/index.html` (after running tests)

---

*Comprehensive documentation index for NEWRSS platform | Generated: 2025-09-01*