-- Scale indexes for 10k+ agents (idempotent)
CREATE INDEX IF NOT EXISTS ix_agents_owner_id ON agents(owner_id);
CREATE INDEX IF NOT EXISTS ix_agents_is_active ON agents(is_active);
CREATE INDEX IF NOT EXISTS ix_agents_created_at ON agents(created_at);
CREATE INDEX IF NOT EXISTS ix_agents_owner_active ON agents(owner_id, is_active);

CREATE INDEX IF NOT EXISTS ix_tasks_agent_id ON tasks(agent_id);
CREATE INDEX IF NOT EXISTS ix_tasks_agent_status ON tasks(agent_id, status);
CREATE INDEX IF NOT EXISTS ix_tasks_creator_agent_id ON tasks(creator_agent_id);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS ix_tasks_status_completed_at ON tasks(status, completed_at);
