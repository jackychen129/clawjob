-- NOTE: translated comment in English.
-- NOTE: translated comment in English.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completion_webhook_url TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_deadline_at TIMESTAMP;
