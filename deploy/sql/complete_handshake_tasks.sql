-- 一次性：将 Skill 注册握手任务未完成的行标记为 completed（无 Python 时在 postgres 容器内执行）
-- docker exec -i clawjob-postgres psql -U agentarena -d agentarena -f -

UPDATE tasks
SET
  status = 'completed',
  completed_at = COALESCE(completed_at, NOW()),
  submitted_at = COALESCE(submitted_at, NOW())
WHERE status IS DISTINCT FROM 'completed'
  AND (
    title ILIKE '%handshake%'
    OR title ILIKE '%握手%'
    OR description ILIKE '%握手任务%'
  );

-- 查看结果
SELECT id, title, status, completed_at
FROM tasks
WHERE title ILIKE '%handshake%' OR title ILIKE '%握手%' OR description ILIKE '%握手任务%'
ORDER BY id DESC
LIMIT 20;
