-- NOTE: translated comment in English.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS invited_agent_ids JSONB;
