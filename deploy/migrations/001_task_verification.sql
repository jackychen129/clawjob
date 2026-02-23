-- 任务验收机制：完成回调、提交时间、验收截止（6h 自动完成）
-- 已有 tasks 表时执行此脚本以添加新列
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completion_webhook_url TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_deadline_at TIMESTAMP;
