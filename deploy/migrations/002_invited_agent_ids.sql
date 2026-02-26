-- 任务可指定仅部分 Agent 可接取（候选者）
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS invited_agent_ids JSONB;
