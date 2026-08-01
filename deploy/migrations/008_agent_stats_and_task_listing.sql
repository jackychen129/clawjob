-- Pre-aggregated agent metrics + materialized public task listing flag

CREATE TABLE IF NOT EXISTS agent_stats (
    agent_id INTEGER PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
    completed_count INTEGER NOT NULL DEFAULT 0,
    earned_points INTEGER NOT NULL DEFAULT 0,
    published_count INTEGER NOT NULL DEFAULT 0,
    assigned_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_stats_earned_points ON agent_stats (earned_points DESC);
CREATE INDEX IF NOT EXISTS ix_agent_stats_completed_count ON agent_stats (completed_count DESC);

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_public_listing BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_tasks_public_listing_status
    ON tasks (status, is_public_listing)
    WHERE is_public_listing = true;

-- Backfill agent_stats from existing tasks
INSERT INTO agent_stats (agent_id, completed_count, earned_points, published_count, assigned_count, updated_at)
SELECT
    a.id,
    COALESCE(c.completed_count, 0),
    COALESCE(c.earned_points, 0),
    COALESCE(p.published_count, 0),
    COALESCE(asg.assigned_count, 0),
    NOW()
FROM agents a
LEFT JOIN (
    SELECT agent_id, COUNT(*) AS completed_count, COALESCE(SUM(reward_points), 0) AS earned_points
    FROM tasks
    WHERE status = 'completed' AND agent_id IS NOT NULL
    GROUP BY agent_id
) c ON c.agent_id = a.id
LEFT JOIN (
    SELECT creator_agent_id AS agent_id, COUNT(*) AS published_count
    FROM tasks
    WHERE creator_agent_id IS NOT NULL
    GROUP BY creator_agent_id
) p ON p.agent_id = a.id
LEFT JOIN (
    SELECT agent_id, COUNT(*) AS assigned_count
    FROM tasks
    WHERE agent_id IS NOT NULL
    GROUP BY agent_id
) asg ON asg.agent_id = a.id
WHERE COALESCE(c.completed_count, 0) > 0
   OR COALESCE(p.published_count, 0) > 0
   OR COALESCE(asg.assigned_count, 0) > 0
ON CONFLICT (agent_id) DO UPDATE SET
    completed_count = EXCLUDED.completed_count,
    earned_points = EXCLUDED.earned_points,
    published_count = EXCLUDED.published_count,
    assigned_count = EXCLUDED.assigned_count,
    updated_at = NOW();
