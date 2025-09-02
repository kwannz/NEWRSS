# NEWRSS - Code Quality and Development Makefile
# Provides unified commands for backend and frontend quality checks

.PHONY: help install-backend install-frontend install-all
.PHONY: lint-backend lint-frontend lint-all
.PHONY: format-backend format-frontend format-all
.PHONY: type-check-backend type-check-frontend type-check-all
.PHONY: test-backend test-frontend test-all
.PHONY: quality-backend quality-frontend quality-all
.PHONY: setup-backend setup-frontend setup-all
.PHONY: clean-backend clean-frontend clean-all

# Default target
help:
	@echo "NEWRSS Production Deployment System"
	@echo "==================================="
	@echo ""
	@echo "🚀 Production Deployment:"
	@echo "  prod-deploy      Deploy to production (with checks)"
	@echo "  prod-build       Build production Docker images"
	@echo "  prod-stop        Stop production services"
	@echo "  prod-restart     Restart production services"
	@echo "  prod-status      Check production service status"
	@echo "  prod-logs        View production logs"
	@echo ""
	@echo "💾 Backup & Recovery:"
	@echo "  backup-create    Create production backup"
	@echo "  backup-restore   Restore from backup"
	@echo "  backup-verify    Verify backup integrity"
	@echo ""
	@echo "📊 Monitoring & Maintenance:"
	@echo "  monitor-metrics  View performance metrics"
	@echo "  monitor-logs     Check log files"
	@echo "  maintenance-cleanup  Run maintenance cleanup"
	@echo "  maintenance-health   Run comprehensive health check"
	@echo ""
	@echo "🔒 Security:"
	@echo "  security-scan    Run vulnerability scan"
	@echo "  security-update  Update base images"
	@echo "  ssl-renew        Renew SSL certificates"
	@echo "  ssl-check        Check SSL certificate status"
	@echo ""
	@echo "🗄️  Database Management:"
	@echo "  db-migrate       Run database migrations"
	@echo "  db-backup        Create manual database backup"
	@echo "  db-console       Open database console"
	@echo ""
	@echo "⚡ Performance Testing:"
	@echo "  perf-test        Run Apache Bench performance test"
	@echo "  load-test        Run wrk load test"
	@echo ""
	@echo "🏗️  Development Environment:"
	@echo "  dev-start        Start development environment"
	@echo "  dev-stop         Stop development environment"
	@echo "  dev-reset        Reset development environment"
	@echo ""
	@echo "🧪 Code Quality:"
	@echo "  quality-all      Run all quality checks (lint + type-check + format)"
	@echo "  test-all         Run all tests"
	@echo "  ci-all           Run all CI checks"
	@echo ""
	@echo "📦 Installation:"
	@echo "  install-all      Install all dependencies (backend + frontend)"
	@echo "  setup-all        Setup complete development environment"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  clean-all        Clean all build artifacts and caches"

# =============================================================================
# Installation Commands
# =============================================================================

install-backend:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "✅ Backend dependencies installed"

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Frontend dependencies installed"

install-all: install-backend install-frontend
	@echo "✅ All dependencies installed"

# =============================================================================
# Backend Quality Commands
# =============================================================================

lint-backend:
	@echo "Running backend linting with ruff..."
	cd backend && ruff check app/ --fix
	@echo "✅ Backend linting completed"

format-backend:
	@echo "Formatting backend code..."
	cd backend && ruff format app/
	cd backend && isort app/
	@echo "✅ Backend formatting completed"

type-check-backend:
	@echo "Running backend type checking with mypy..."
	cd backend && mypy app/
	@echo "✅ Backend type checking completed"

test-backend:
	@echo "Running backend tests..."
	cd backend && pytest --cov=app --cov-report=term-missing
	@echo "✅ Backend tests completed"

quality-backend: lint-backend type-check-backend format-backend
	@echo "✅ Backend quality checks completed"

# =============================================================================
# Frontend Quality Commands  
# =============================================================================

lint-frontend:
	@echo "Running frontend linting with ESLint..."
	cd frontend && npm run lint
	@echo "✅ Frontend linting completed"

format-frontend:
	@echo "Formatting frontend code with Prettier..."
	cd frontend && npm run format
	@echo "✅ Frontend formatting completed"

type-check-frontend:
	@echo "Running frontend type checking..."
	cd frontend && npm run type-check
	@echo "✅ Frontend type checking completed"

test-frontend:
	@echo "Running frontend tests..."
	cd frontend && npm run test:coverage
	@echo "✅ Frontend tests completed"

quality-frontend: lint-frontend type-check-frontend format-frontend
	@echo "✅ Frontend quality checks completed"

# =============================================================================
# Combined Commands
# =============================================================================

lint-all: lint-backend lint-frontend
	@echo "✅ All linting completed"

format-all: format-backend format-frontend
	@echo "✅ All formatting completed"

type-check-all: type-check-backend type-check-frontend
	@echo "✅ All type checking completed"

test-all: test-backend test-frontend
	@echo "✅ All tests completed"

quality-all: quality-backend quality-frontend
	@echo "✅ All quality checks completed"

# =============================================================================
# Development Setup Commands
# =============================================================================

setup-backend: install-backend
	@echo "Setting up backend development environment..."
	cd backend && pre-commit install
	@echo "✅ Backend development environment ready"

setup-frontend: install-frontend
	@echo "Setting up frontend development environment..."
	@echo "✅ Frontend development environment ready"

setup-all: install-all
	@echo "Setting up complete development environment..."
	pre-commit install
	@echo "✅ Development environment ready"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make quality-all    # Run all quality checks"
	@echo "  make test-all       # Run all tests"
	@echo ""
	@echo "💡 Tip: Use 'make help' to see all available commands"

# =============================================================================
# Cleanup Commands
# =============================================================================

clean-backend:
	@echo "Cleaning backend artifacts..."
	cd backend && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	cd backend && find . -type f -name "*.pyc" -delete 2>/dev/null || true
	cd backend && rm -rf .pytest_cache htmlcov .coverage .mypy_cache .ruff_cache 2>/dev/null || true
	@echo "✅ Backend cleanup completed"

clean-frontend:
	@echo "Cleaning frontend artifacts..."
	cd frontend && rm -rf .next build dist coverage 2>/dev/null || true
	cd frontend && rm -rf node_modules/.cache 2>/dev/null || true
	@echo "✅ Frontend cleanup completed"

clean-all: clean-backend clean-frontend
	@echo "✅ All cleanup completed"

# =============================================================================
# Docker Commands (Optional)
# =============================================================================

docker-build:
	@echo "Building Docker containers..."
	docker-compose build
	@echo "✅ Docker build completed"

docker-up:
	@echo "Starting Docker containers..."
	docker-compose up -d
	@echo "✅ Docker containers started"

docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down
	@echo "✅ Docker containers stopped"

# =============================================================================
# Production Deployment Commands
# =============================================================================

prod-check: quality-all test-all
	@echo "Running production readiness checks..."
	@echo "✅ Production readiness verified"

prod-build:
	@echo "Building production Docker images..."
	docker-compose -f docker-compose.prod.yml build
	@echo "✅ Production images built"

prod-deploy: prod-check prod-build
	@echo "Deploying to production..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production deployment completed"

prod-stop:
	@echo "Stopping production services..."
	docker-compose -f docker-compose.prod.yml down
	@echo "✅ Production services stopped"

prod-restart: prod-stop prod-deploy
	@echo "✅ Production services restarted"

prod-logs:
	@echo "Viewing production logs..."
	docker-compose -f docker-compose.prod.yml logs -f

prod-status:
	@echo "Production service status:"
	docker-compose -f docker-compose.prod.yml ps
	@echo ""
	@echo "Health checks:"
	@curl -s http://localhost/health | jq '.' || echo "Health check failed"

# =============================================================================
# Backup and Recovery Commands
# =============================================================================

backup-create:
	@echo "Creating production backup..."
	./scripts/backup.sh
	@echo "✅ Backup created"

backup-restore:
	@echo "Restoring from backup..."
	@read -p "Enter backup date (YYYY-MM-DD): " date; \
	./scripts/restore.sh --date $$date --type full
	@echo "✅ Restore completed"

backup-verify:
	@echo "Verifying latest backup..."
	@read -p "Enter backup date (YYYY-MM-DD): " date; \
	./scripts/restore.sh --date $$date --type database --dry-run
	@echo "✅ Backup verification completed"

# =============================================================================
# Monitoring and Maintenance Commands
# =============================================================================

monitor-metrics:
	@echo "Collecting performance metrics..."
	docker-compose -f docker-compose.prod.yml exec redis redis-cli keys "metrics:*" | head -20
	@echo "Use 'docker-compose -f docker-compose.prod.yml exec redis redis-cli' for detailed metrics"

monitor-logs:
	@echo "Checking log files..."
	@ls -la /var/log/newrss/ 2>/dev/null || echo "Log directory not found"
	docker-compose -f docker-compose.prod.yml logs --tail=50

maintenance-cleanup:
	@echo "Running maintenance cleanup..."
	docker-compose -f docker-compose.prod.yml exec backend python -c "
	import asyncio
	from app.tasks.maintenance import _cleanup_old_news_items_async, _cleanup_redis_cache_async
	asyncio.run(_cleanup_old_news_items_async(30))
	asyncio.run(_cleanup_redis_cache_async(256))
	"
	@echo "✅ Maintenance cleanup completed"

maintenance-health:
	@echo "Running comprehensive health check..."
	docker-compose -f docker-compose.prod.yml exec backend python -c "
	import asyncio
	from app.tasks.maintenance import _perform_health_checks_async
	import json
	result = asyncio.run(_perform_health_checks_async())
	print(json.dumps(result, indent=2))
	"

# =============================================================================
# Security Commands  
# =============================================================================

security-scan:
	@echo "Running security vulnerability scan..."
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v $(PWD):/tmp/app \
		aquasec/trivy fs --severity HIGH,CRITICAL /tmp/app

security-update:
	@echo "Updating base images for security..."
	docker-compose -f docker-compose.prod.yml pull
	docker system prune -f
	@echo "✅ Security updates completed"

# =============================================================================
# Database Management Commands
# =============================================================================

db-migrate:
	@echo "Running database migrations..."
	docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
	@echo "✅ Database migrations completed"

db-backup:
	@echo "Creating database backup..."
	docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
		-U newrss_prod -d newrss_prod -f /tmp/manual_backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created"

db-console:
	@echo "Opening database console..."
	docker-compose -f docker-compose.prod.yml exec postgres psql -U newrss_prod -d newrss_prod

# =============================================================================
# SSL Certificate Management
# =============================================================================

ssl-renew:
	@echo "Renewing SSL certificates..."
	sudo certbot renew --nginx
	sudo systemctl reload nginx
	@echo "✅ SSL certificates renewed"

ssl-check:
	@echo "Checking SSL certificate status..."
	@openssl x509 -in nginx/ssl/cert.pem -text -noout | grep -E "(Subject:|Not Before|Not After)" || echo "Certificate file not found"

# =============================================================================
# Performance Testing
# =============================================================================

perf-test:
	@echo "Running performance tests..."
	@if command -v ab >/dev/null 2>&1; then \
		echo "Running Apache Bench test..."; \
		ab -n 1000 -c 10 http://localhost/health; \
	else \
		echo "Apache Bench (ab) not installed. Install with: sudo apt install apache2-utils"; \
	fi

load-test:
	@echo "Running load test..."
	@if command -v wrk >/dev/null 2>&1; then \
		echo "Running wrk load test..."; \
		wrk -t12 -c400 -d30s http://localhost/; \
	else \
		echo "wrk not installed. Install with: sudo apt install wrk"; \
	fi

# =============================================================================
# CI/CD Integration
# =============================================================================

ci-backend: lint-backend type-check-backend test-backend
	@echo "✅ Backend CI checks passed"

ci-frontend: lint-frontend type-check-frontend test-frontend  
	@echo "✅ Frontend CI checks passed"

ci-all: ci-backend ci-frontend
	@echo "✅ All CI checks passed"

# =============================================================================  
# Development Environment
# =============================================================================

dev-start:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "✅ Development environment started"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"

dev-stop:
	@echo "Stopping development environment..."
	docker-compose down
	@echo "✅ Development environment stopped"

dev-reset: dev-stop clean-all
	@echo "Resetting development environment..."
	docker system prune -f --volumes
	$(MAKE) dev-start
	@echo "✅ Development environment reset"