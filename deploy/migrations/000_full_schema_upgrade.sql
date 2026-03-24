-- NOTE: translated comment in English.
-- NOTE: translated comment in English.

-- users
ALTER TABLE users ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 0;

-- tasks
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reward_points INTEGER DEFAULT 0;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completion_webhook_url TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_deadline_at TIMESTAMP;
ALTER TABLE tasks ALTER COLUMN agent_id DROP NOT NULL;

-- NOTE: translated comment in English.
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
