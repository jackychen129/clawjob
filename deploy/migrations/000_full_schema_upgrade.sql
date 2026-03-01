-- ClawJob 完整 schema 升级：信用点、任务奖励、验收、支付方式、流水
-- 对已存在的表仅添加缺失列；新建缺失表

-- users
ALTER TABLE users ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 0;

-- tasks
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reward_points INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completion_webhook_url TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_deadline_at TIMESTAMP;
ALTER TABLE tasks ALTER COLUMN agent_id DROP NOT NULL;

-- payment_methods（若表不存在则需手动建表，见下）
CREATE TABLE IF NOT EXISTS payment_methods (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type VARCHAR NOT NULL,
    masked_info VARCHAR NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- credit_transactions
CREATE TABLE IF NOT EXISTS credit_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount INTEGER NOT NULL,
    type VARCHAR NOT NULL,
    ref_id INTEGER,
    remark VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
