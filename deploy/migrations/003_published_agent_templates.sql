-- NOTE: translated comment in English.
CREATE TABLE IF NOT EXISTS published_agent_templates (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    download_agent_url TEXT,
    download_skill_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_published_agent_templates_agent_id ON published_agent_templates(agent_id);
