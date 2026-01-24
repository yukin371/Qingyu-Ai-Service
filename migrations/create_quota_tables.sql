-- Qingyu-Ai-Service/migrations/create_quota_tables.sql

-- 配额消费记录表
CREATE TABLE IF NOT EXISTS quota_consumption_records (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    service_name VARCHAR(50) DEFAULT 'qingyu-ai-service',
    workflow_type VARCHAR(50) NOT NULL,
    tokens_used INTEGER NOT NULL,
    quota_consumed INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    consumed_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT idx_user_time UNIQUE (user_id, consumed_at)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_quota_user_time ON quota_consumption_records(user_id, consumed_at DESC);
CREATE INDEX IF NOT EXISTS idx_quota_workflow ON quota_consumption_records(workflow_type);
CREATE INDEX IF NOT EXISTS idx_quota_date ON quota_consumption_records(DATE(consumed_at));

-- 配额同步状态表
CREATE TABLE IF NOT EXISTS quota_sync_status (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    last_sync_at TIMESTAMP DEFAULT NOW(),
    last_sync_tokens INTEGER DEFAULT 0,
    sync_status VARCHAR(20) DEFAULT 'pending',  -- pending, synced, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_sync_status ON quota_sync_status(sync_status);
CREATE INDEX IF NOT EXISTS idx_sync_updated ON quota_sync_status(updated_at DESC);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_quota_sync_status_updated_at
    BEFORE UPDATE ON quota_sync_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
