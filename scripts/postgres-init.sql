-- Production PostgreSQL Initialization Script for NEWRSS
-- This script is executed when the PostgreSQL container first starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create additional database user for read-only operations (monitoring, backup)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'newrss_readonly') THEN
        CREATE ROLE newrss_readonly;
    END IF;
END
$$;

-- Grant read-only permissions
GRANT CONNECT ON DATABASE newrss_prod TO newrss_readonly;
GRANT USAGE ON SCHEMA public TO newrss_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO newrss_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO newrss_readonly;

-- Create backup user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'newrss_backup') THEN
        CREATE ROLE newrss_backup;
    END IF;
END
$$;

-- Grant backup permissions
GRANT CONNECT ON DATABASE newrss_prod TO newrss_backup;
GRANT USAGE ON SCHEMA public TO newrss_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO newrss_backup;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO newrss_backup;

-- Performance optimizations
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET effective_cache_size = '512MB';
ALTER SYSTEM SET shared_buffers = '128MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET wal_buffers = '8MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET random_page_cost = 1.1;

-- Security settings
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;
ALTER SYSTEM SET log_checkpoints = 'on';
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
ALTER SYSTEM SET log_lock_waits = 'on';

-- Reload configuration
SELECT pg_reload_conf();

-- Create indexes for common queries (will be created by Alembic migrations)
-- This is a placeholder for any additional indexes needed for production