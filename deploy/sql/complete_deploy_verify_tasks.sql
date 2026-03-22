-- 将「验证部署」相关自动化测试任务标记为已完成（verify-deployed.py / verify-online-e2e.py）
UPDATE tasks
SET
  status = 'completed',
  completed_at = COALESCE(completed_at, NOW()),
  submitted_at = COALESCE(submitted_at, NOW())
WHERE status IS DISTINCT FROM 'completed'
  AND (
    title ILIKE '%验证部署任务%'
    OR title = 'E2E 验证任务（带地点时长技能）'
    OR (
      title ILIKE 'E2E 验证任务%'
      AND (
        description ILIKE '%自动化%'
        OR description ILIKE '%自动验证%'
      )
    )
  );
