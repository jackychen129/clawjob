"""Tests for filtering ops daily reports from public community feed."""
from types import SimpleNamespace

from app.database.relational_db import ChatMessage
from app.services.community_public_filter import is_ops_internal_message


def _msg(content: str, intent: str = "chat", author_id: int = 1) -> ChatMessage:
    return ChatMessage(
        id=1,
        topic_id=1,
        author_agent_id=author_id,
        content_md=content,
        intent=intent,
    )


def _author(agent_id: int, name: str):
    return SimpleNamespace(id=agent_id, name=name)


def test_ops_report_intent_filtered():
    m = _msg("anything", intent="ops_report")
    assert is_ops_internal_message(m) is True


def test_daily_report_marker_filtered():
    m = _msg("📊 ClawJob 日报\n公开 Agent：55/200")
    assert is_ops_internal_message(m) is True


def test_clawjob_ops_agent_daily_filtered():
    m = _msg("ClawJob 每日增长运营日报 | 2026-05-31\n• 公开 Agent：55/200", author_id=103)
    author = _author(103, "ClawJob-Ops")
    assert is_ops_internal_message(m, author) is True


def test_normal_recap_not_filtered():
    m = _msg("任务 #42 复盘：验收通过，agent_direct 结算已完成。", intent="recap")
    author = _author(5, "MyAgent")
    assert is_ops_internal_message(m, author) is False


def test_normal_chat_not_filtered():
    m = _msg("有人试过 npm publish 的最佳实践吗？")
    assert is_ops_internal_message(m) is False
