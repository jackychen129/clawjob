-- MCP tool marketplace (Phase 5 Step B)
CREATE TABLE IF NOT EXISTS mcp_tools (
    id SERIAL PRIMARY KEY,
    tool_slug VARCHAR(128) NOT NULL UNIQUE,
    name VARCHAR(256) NOT NULL,
    description TEXT,
    category VARCHAR(64) NOT NULL DEFAULT 'general',
    parameters JSON,
    return_type VARCHAR(64) NOT NULL DEFAULT 'object',
    requires_auth BOOLEAN NOT NULL DEFAULT FALSE,
    rate_limit INTEGER NOT NULL DEFAULT 100,
    author_user_id INTEGER REFERENCES users(id),
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    version_tag VARCHAR(64) NOT NULL DEFAULT 'v1',
    pricing_model VARCHAR(16) NOT NULL DEFAULT 'free',
    price_per_unit INTEGER NOT NULL DEFAULT 0,
    revenue_share_bp INTEGER NOT NULL DEFAULT 7000,
    mcp_config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_author_user_id ON mcp_tools(author_user_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tools_category ON mcp_tools(category);
