-- Enable pg_stat_statements for query logging (L3)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename    VARCHAR(255) NOT NULL,
    status      VARCHAR(50)  NOT NULL DEFAULT 'pending',
    result      TEXT,
    file_size   INTEGER,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for status queries
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
