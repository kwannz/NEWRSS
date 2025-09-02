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
	@echo "NEWRSS Code Quality Commands"
	@echo "============================"
	@echo ""
	@echo "Installation:"
	@echo "  install-all       Install all dependencies (backend + frontend)"
	@echo "  install-backend   Install backend Python dependencies"
	@echo "  install-frontend  Install frontend Node.js dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  quality-all       Run all quality checks (lint + type-check + format)"
	@echo "  quality-backend   Run backend quality checks"
	@echo "  quality-frontend  Run frontend quality checks"
	@echo ""
	@echo "Linting:"
	@echo "  lint-all         Run linting on all code"
	@echo "  lint-backend     Run ruff linting on Python code"
	@echo "  lint-frontend    Run ESLint on TypeScript/JavaScript code"
	@echo ""
	@echo "Formatting:"
	@echo "  format-all       Format all code"
	@echo "  format-backend   Format Python code with ruff and black"
	@echo "  format-frontend  Format frontend code with Prettier"
	@echo ""
	@echo "Type Checking:"
	@echo "  type-check-all      Run type checking on all code"
	@echo "  type-check-backend  Run mypy on Python code"
	@echo "  type-check-frontend Run TypeScript compiler checks"
	@echo ""
	@echo "Testing:"
	@echo "  test-all         Run all tests"
	@echo "  test-backend     Run backend tests with pytest"
	@echo "  test-frontend    Run frontend tests with Jest"
	@echo ""
	@echo "Setup:"
	@echo "  setup-all        Setup development environment (install + pre-commit)"
	@echo "  setup-backend    Setup backend development environment"
	@echo "  setup-frontend   Setup frontend development environment"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean-all        Clean all build artifacts and caches"
	@echo "  clean-backend    Clean Python caches and build files"
	@echo "  clean-frontend   Clean Node.js build files and caches"

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
# Production Commands
# =============================================================================

prod-check: quality-all test-all
	@echo "Running production readiness checks..."
	@echo "✅ Production readiness verified"

# =============================================================================
# CI/CD Integration
# =============================================================================

ci-backend: lint-backend type-check-backend test-backend
	@echo "✅ Backend CI checks passed"

ci-frontend: lint-frontend type-check-frontend test-frontend  
	@echo "✅ Frontend CI checks passed"

ci-all: ci-backend ci-frontend
	@echo "✅ All CI checks passed"