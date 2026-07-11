"""cleanup_ops_content must never delete platform onboarding quests."""
from __future__ import annotations

import importlib.util
import os
import sys
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(os.path.join(HERE, "..", "scripts", "cleanup_ops_content.py"))


def _load_cleanup_module():
    spec = importlib.util.spec_from_file_location("cleanup_ops_content", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cleanup_ops_content"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_cleanup_preserves_seed_onboarding_source():
    mod = _load_cleanup_module()
    assert "seed_onboarding_quest" not in mod._SEED_TASK_SOURCES


def test_cleanup_does_not_delete_onboarding_flagged_task():
    mod = _load_cleanup_module()
    task = SimpleNamespace(
        title="【新手 Quest 1】阅读 Agent 发现清单",
        description="well-known",
        input_data={"onboarding": True, "source": "seed_onboarding_quest"},
    )
    assert mod._is_onboarding_quest_task(task) is True
    reason = mod._task_delete_reason(task, None, None, set(), set())
    assert reason is None


def test_cleanup_does_not_delete_onboarding_title_without_flag():
    mod = _load_cleanup_module()
    task = SimpleNamespace(
        title="【新手 Quest 2】订阅一条平台开放任务",
        description="",
        input_data={},
    )
    assert mod._is_onboarding_quest_task(task) is True
    reason = mod._task_delete_reason(task, None, None, set(), set())
    assert reason is None


def test_cleanup_still_deletes_demo_seed_source():
    mod = _load_cleanup_module()
    task = SimpleNamespace(
        title="周报数据汇总与图表",
        description="",
        input_data={"source": "seed_demo_data"},
    )
    reason = mod._task_delete_reason(task, None, None, set(), set())
    assert reason == "seed source=seed_demo_data"
