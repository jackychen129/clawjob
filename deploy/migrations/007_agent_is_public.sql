-- Materialized public listing flag for O(1) counts and SQL pagination (10k+ agents)

ALTER TABLE agents ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_agents_is_public ON agents (is_public) WHERE is_public = true;
CREATE INDEX IF NOT EXISTS ix_agents_public_created_at ON agents (created_at DESC) WHERE is_public = true;
