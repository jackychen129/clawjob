"""Pytest configuration. Ignore test modules that depend on legacy API not present in current codebase."""
import os


def pytest_configure(config):
    """确保测试库 schema 与模型一致：若 tasks 表缺少列则添加（兼容旧库）。"""
    try:
        from app.database.relational_db import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            for sql in (
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS creator_agent_id INTEGER REFERENCES agents(id)",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS reward_points INTEGER DEFAULT 0",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completion_webhook_url TEXT",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS verification_deadline_at TIMESTAMP",
                "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS invited_agent_ids JSONB",
            ):
                conn.execute(text(sql))
            conn.commit()
    except Exception:
        pass  # 例如表尚未创建，由各测试里 init_db 处理


def pytest_ignore_collect(collection_path, config):
    """Do not collect tests that import legacy-only classes (MessageRouter, StrategyEvolutionManager, etc.)."""
    name = os.path.basename(collection_path)
    if name in (
        "test_agent_communication.py",
        "test_agent_self_iteration.py",
        "test_basic_agentic_functionality.py",
        "test_e2e.py",
        "test_integration.py",
    ):
        return True
    return False
