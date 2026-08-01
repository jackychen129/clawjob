-- Admin / observability scale indexes (Wave 1)

CREATE INDEX IF NOT EXISTS ix_system_logs_created_at ON system_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_system_logs_category_created_at ON system_logs (category, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_system_logs_level_created_at ON system_logs (level, created_at DESC);

CREATE INDEX IF NOT EXISTS ix_task_subscriptions_agent_id ON task_subscriptions (agent_id);

-- agent_direct settlement queue: filter by settlement_mode in input_data JSON
CREATE INDEX IF NOT EXISTS ix_tasks_input_settlement_mode
  ON tasks ((input_data->>'settlement_mode'))
  WHERE input_data IS NOT NULL;
