-- PostgreSQL Initialization Script for ResuBoost AI
-- This script runs once when the PostgreSQL container is first created
--
-- Note: Schema is managed by Alembic migrations. This script only sets up
-- database-level configurations and extensions.

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Trigram matching for search
CREATE EXTENSION IF NOT EXISTS "unaccent";       -- Accent-insensitive search

-- Create application schema (optional, for organization)
-- CREATE SCHEMA IF NOT EXISTS resuboost;

-- Set default timezone
SET timezone = 'UTC';

-- Create read-only user for analytics/reporting (optional)
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'resuboost_readonly') THEN
--         CREATE ROLE resuboost_readonly WITH LOGIN PASSWORD 'readonly_password';
--     END IF;
-- END
-- $$;

-- Grant read-only access to analytics user (run after migrations)
-- GRANT USAGE ON SCHEMA public TO resuboost_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO resuboost_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO resuboost_readonly;

-- Performance tuning for production (adjust based on container resources)
-- These are suggestions - actual values depend on your deployment

-- Increase shared_buffers (25% of RAM, max ~8GB)
-- ALTER SYSTEM SET shared_buffers = '256MB';

-- Increase effective_cache_size (50-75% of RAM)
-- ALTER SYSTEM SET effective_cache_size = '512MB';

-- Increase work_mem for complex queries
-- ALTER SYSTEM SET work_mem = '16MB';

-- Log slow queries (useful for optimization)
-- ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s

-- Note: Run 'SELECT pg_reload_conf();' after ALTER SYSTEM commands
-- or restart PostgreSQL for changes to take effect.

-- Verify setup
SELECT 'PostgreSQL initialized successfully for ResuBoost AI' AS status;
