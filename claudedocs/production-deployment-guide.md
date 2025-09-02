# NEWRSS Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying NEWRSS to production with zero-downtime deployment, comprehensive monitoring, and disaster recovery capabilities.

## Prerequisites

### System Requirements

**Server Specifications (Minimum)**:
- **CPU**: 4 cores (8 cores recommended)
- **Memory**: 8GB RAM (16GB recommended)
- **Storage**: 100GB SSD (500GB recommended)
- **Network**: 1Gbps connection
- **OS**: Ubuntu 20.04+ or RHEL 8+

**Dependencies**:
- Docker Engine 24.0+
- Docker Compose 2.20+
- Git 2.30+
- SSL Certificate (Let's Encrypt or commercial)

### Environment Setup

1. **Create production user**:
```bash
sudo useradd -m -s /bin/bash -G docker newrss
sudo mkdir -p /home/newrss/.ssh
# Add SSH keys for deployment
```

2. **Install required packages**:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker newrss

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional tools
sudo apt update
sudo apt install -y postgresql-client-16 redis-tools nginx-extras
```

## Production Deployment Steps

### 1. Clone and Configure Repository

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/your-org/newrss.git
sudo chown -R newrss:newrss /opt/newrss
cd /opt/newrss

# Switch to production user
sudo su - newrss
cd /opt/newrss

# Checkout main branch
git checkout main
git pull origin main
```

### 2. Environment Configuration

```bash
# Copy production environment template
cp .env.production .env

# Edit production configuration
nano .env
```

**Required Environment Variables**:
```bash
# Database Configuration
POSTGRES_DB=newrss_prod
POSTGRES_USER=newrss_prod
POSTGRES_PASSWORD=SECURE_PASSWORD_HERE
DATABASE_URL=postgresql+asyncpg://newrss_prod:SECURE_PASSWORD_HERE@postgres:5432/newrss_prod

# Security Configuration
SECRET_KEY=GENERATE_SECURE_KEY_WITH_OPENSSL_RAND_HEX_32
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Domain Configuration
DOMAIN=yourdomain.com
SUBDOMAIN=www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# API URLs
NEXT_PUBLIC_API_URL=https://yourdomain.com/api
NEXT_PUBLIC_WS_URL=https://yourdomain.com

# External Services
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/telegram/webhook
TELEGRAM_SECRET_TOKEN=secure_webhook_secret
OPENAI_API_KEY=your_openai_api_key
```

### 3. SSL Certificate Setup

**Option A: Let's Encrypt (Recommended)**
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificates
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Copy certificates to project directory
sudo mkdir -p /opt/newrss/nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/newrss/nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/newrss/nginx/ssl/key.pem
sudo chown -R newrss:newrss /opt/newrss/nginx/ssl
```

**Option B: Commercial Certificate**
```bash
# Copy your certificates
mkdir -p /opt/newrss/nginx/ssl
cp your-certificate.pem /opt/newrss/nginx/ssl/cert.pem
cp your-private-key.pem /opt/newrss/nginx/ssl/key.pem
chmod 600 /opt/newrss/nginx/ssl/*
```

### 4. Database Initialization

```bash
# Start database service
docker-compose -f docker-compose.prod.yml up -d postgres redis

# Wait for database to be ready
sleep 30

# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify database
docker-compose -f docker-compose.prod.yml exec postgres psql -U newrss_prod -d newrss_prod -c "SELECT COUNT(*) FROM alembic_version;"
```

### 5. Production Deployment

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs --tail=50
```

### 6. Health Check Verification

```bash
# Wait for services to start
sleep 60

# Check application health
curl -f https://yourdomain.com/health
curl -f https://yourdomain.com/api/health

# Check database connectivity
docker-compose -f docker-compose.prod.yml exec backend python -c "
import asyncio
from app.core.database import get_db

async def test():
    async with get_db() as db:
        result = await db.execute('SELECT 1')
        print('Database OK')

asyncio.run(test())
"

# Check Redis connectivity
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Check Celery workers
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A app.tasks.news_crawler.celery_app inspect ping
```

## Monitoring Setup

### 1. Application Metrics

The application automatically collects metrics in Redis. Access them via:

```bash
# View request metrics
docker-compose -f docker-compose.prod.yml exec redis redis-cli keys "metrics:*"

# Health check endpoint
curl -s https://yourdomain.com/health/detailed | jq '.'
```

### 2. Log Management

Logs are automatically structured and rotated:

```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f backend

# View nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx

# Check log files
ls -la /var/log/newrss/
```

### 3. Performance Monitoring

Monitor key metrics:

- **Request Rate**: `metrics:requests:total:*`
- **Response Times**: `metrics:response_times:*`
- **Error Rates**: `metrics:errors:*`
- **Business Metrics**: `metrics:business:*`

## Backup and Recovery

### 1. Automated Backups

Backups run automatically via the backup script:

```bash
# Manual backup execution
/opt/newrss/scripts/backup.sh

# Check backup status
ls -la /var/backups/newrss/

# Verify backup integrity
/opt/newrss/scripts/restore.sh --date $(date +%Y-%m-%d) --type database --dry-run
```

### 2. Disaster Recovery

**Full System Recovery**:
```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Restore from backup
/opt/newrss/scripts/restore.sh --date YYYY-MM-DD --type full --force

# Verify restoration
curl -f https://yourdomain.com/health
```

**Database-Only Recovery**:
```bash
# Restore database only
/opt/newrss/scripts/restore.sh --date YYYY-MM-DD --type database

# Restart services
docker-compose -f docker-compose.prod.yml restart backend celery-worker
```

## Zero-Downtime Updates

### 1. Blue-Green Deployment Process

```bash
# 1. Pull latest changes
git pull origin main

# 2. Build new images
docker-compose -f docker-compose.prod.yml build

# 3. Start green environment
cp docker-compose.prod.yml docker-compose.green.yml
# Edit docker-compose.green.yml to use different service names
docker-compose -f docker-compose.green.yml up -d

# 4. Health check green environment
curl -f https://green.yourdomain.com/health

# 5. Switch traffic (update nginx configuration)
# Update nginx upstream configuration to point to green services

# 6. Stop blue environment
docker-compose -f docker-compose.blue.yml down
```

### 2. Database Migrations

```bash
# Run migrations in green environment
docker-compose -f docker-compose.green.yml exec backend alembic upgrade head

# Verify migration
docker-compose -f docker-compose.green.yml exec backend alembic current
```

## Troubleshooting

### Common Issues

**1. SSL Certificate Issues**
```bash
# Check certificate validity
openssl x509 -in /opt/newrss/nginx/ssl/cert.pem -text -noout

# Renew Let's Encrypt certificate
sudo certbot renew --nginx
```

**2. Database Connection Issues**
```bash
# Check database logs
docker-compose -f docker-compose.prod.yml logs postgres

# Test connection
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U newrss_prod
```

**3. High Memory Usage**
```bash
# Check container memory usage
docker stats

# Restart services to free memory
docker-compose -f docker-compose.prod.yml restart
```

**4. Celery Worker Issues**
```bash
# Check worker status
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A app.tasks.news_crawler.celery_app inspect active

# Restart workers
docker-compose -f docker-compose.prod.yml restart celery-worker celery-beat
```

### Emergency Procedures

**1. Emergency Rollback**
```bash
# Quick rollback to previous version
git checkout HEAD~1
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build

# Or use restore script
/opt/newrss/scripts/restore.sh --date PREVIOUS_DATE --type full --force
```

**2. Service Recovery**
```bash
# Restart specific service
docker-compose -f docker-compose.prod.yml restart SERVICE_NAME

# Full system restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## Maintenance Tasks

### Daily Tasks
- Monitor error rates and performance metrics
- Check disk space and log file sizes
- Verify backup completion
- Review security alerts

### Weekly Tasks
- Update system packages
- Review and rotate SSL certificates
- Analyze performance trends
- Update dependencies (if needed)

### Monthly Tasks
- Full disaster recovery test
- Security vulnerability assessment
- Performance optimization review
- Capacity planning evaluation

## Security Considerations

### 1. Network Security
- Use VPC/private networks
- Configure firewall rules (ports 80, 443, 22 only)
- Enable fail2ban for SSH protection
- Regular security updates

### 2. Application Security
- Keep Docker images updated
- Use non-root containers
- Implement rate limiting
- Regular dependency updates

### 3. Data Security
- Encrypt database connections
- Secure backup storage
- Regular security audits
- Access logging and monitoring

## Performance Optimization

### 1. Database Optimization
```bash
# Monitor database performance
docker-compose -f docker-compose.prod.yml exec postgres psql -U newrss_prod -d newrss_prod -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"
```

### 2. Cache Optimization
```bash
# Monitor Redis memory usage
docker-compose -f docker-compose.prod.yml exec redis redis-cli info memory

# Optimize cache settings
docker-compose -f docker-compose.prod.yml exec redis redis-cli config set maxmemory-policy allkeys-lru
```

### 3. Application Optimization
- Monitor request response times
- Optimize slow endpoints
- Implement caching strategies
- Scale horizontally when needed

## Support and Contact Information

For production support issues:
- **Emergency**: [Your emergency contact]
- **Email**: [Your support email]
- **Documentation**: [Your documentation URL]
- **Monitoring**: [Your monitoring dashboard URL]

## Appendix

### A. Environment Variables Reference
[Complete list of all environment variables and their purposes]

### B. API Endpoints Reference
[List of all API endpoints for health checks and monitoring]

### C. Database Schema
[Current database schema and migration information]

### D. Security Policies
[Security policies and compliance requirements]