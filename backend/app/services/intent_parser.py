"""Intent-to-Task 解析服务（Phase B-3）。

一句话描述 → 结构化任务草稿（title / description / acceptance_criteria / skill / kind /
category / reward_points / deadline_days）。

设计原则：
1. 默认走纯启发式（零依赖、不花钱），保证即使没有 LLM 也能产出可用草稿。
2. 当环境变量 `OPENAI_API_KEY` 存在并且调用方显式请求 `use_llm=True` 时，尝试 LLM 增强；
   LLM 失败时自动回退到启发式结果。
3. 所有输出都打上 `draft_source="intent"` 作为审计来源（由调用方写入）。
4. 不在此处做限频/鉴权/数据库写入，由调用方（API 层）负责。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# NOTE: 技能 token 关键字（中英文），按顺序命中第一个
_SKILL_RULES: List[Tuple[str, List[str]]] = [
    ("bug_fix", ["bug", "修复", "修 bug", "debug", "报错", "异常", "崩溃", "堆栈"]),
    ("code_review", ["code review", "审阅代码", "代码评审", "review", "pr 评审", "合并请求"]),
    ("data_cleaning", ["数据清洗", "去重", "脏数据", "数据预处理", "etl", "清理数据", "clean data"]),
    ("data_analysis", ["数据分析", "统计", "透视", "分布", "图表", "bi", "dashboard", "报表", "可视化"]),
    ("translation", ["翻译", "translate", "translation", "中译英", "英译中", "localize"]),
    ("copywriting", ["文案", "写作", "撰写", "文章", "博文", "公众号", "copywriting", "blog", "seo 文案"]),
    ("ui_design", ["ui 设计", "界面设计", "设计稿", "原型", "figma", "sketch", "视觉设计", "banner", "logo"]),
    ("research", ["调研", "研究", "文献综述", "research", "benchmark", "竞品分析"]),
    ("scraping", ["爬虫", "抓取", "scrape", "crawl", "采集"]),
    ("automation", ["自动化", "脚本", "script", "automation", "批处理"]),
    ("testing", ["测试", "test case", "qa", "回归", "自动化测试", "e2e"]),
]

# NOTE: 类目映射（coarse）：skill → category
_SKILL_TO_CATEGORY: Dict[str, str] = {
    "bug_fix": "development",
    "code_review": "development",
    "automation": "development",
    "testing": "development",
    "scraping": "development",
    "data_cleaning": "data",
    "data_analysis": "data",
    "translation": "writing",
    "copywriting": "writing",
    "ui_design": "design",
    "research": "research",
}

# NOTE: skill → task_type 默认
_SKILL_TO_KIND: Dict[str, str] = {
    "bug_fix": "coding",
    "code_review": "coding",
    "automation": "coding",
    "testing": "coding",
    "scraping": "coding",
    "data_cleaning": "data",
    "data_analysis": "analysis",
    "translation": "writing",
    "copywriting": "writing",
    "ui_design": "design",
    "research": "research",
}

# NOTE: 难度启发：关键字击中提升/降低
_DIFFICULTY_UP_WORDS = ["紧急", "立刻", "立即", "尽快", "高难度", "复杂", "critical", "urgent", "p0", "sev1"]
_DIFFICULTY_DOWN_WORDS = ["简单", "小", "轻量", "小改", "easy", "trivial"]

# NOTE: 期限启发：匹配「N 天内 / 今天 / 明天 / N hours」
_DEADLINE_PATTERNS = [
    (re.compile(r"(\d+)\s*(?:天|日)(?:内|之内)?"), "days"),
    (re.compile(r"(\d+)\s*(?:小时|h|hour|hours)(?:内|之内)?", re.IGNORECASE), "hours"),
    (re.compile(r"(\d+)\s*(?:周|week|weeks)(?:内|之内)?", re.IGNORECASE), "weeks"),
    (re.compile(r"(?:今天|today)"), "today"),
    (re.compile(r"(?:明天|tomorrow)"), "tomorrow"),
    (re.compile(r"(?:本周|this week)"), "thisweek"),
]

# NOTE: 奖励点关键词：匹配「N 点 / N pts / N 积分 / 预算 N」
_REWARD_PATTERNS = [
    re.compile(r"(\d{1,4})\s*(?:点|积分|pts?|points?)", re.IGNORECASE),
    re.compile(r"预算[:：]?\s*(\d{1,4})"),
    re.compile(r"budget[:：]?\s*(\d{1,4})", re.IGNORECASE),
]


@dataclass
class IntentDraft:
    title: str
    description: str
    acceptance_criteria: List[str] = field(default_factory=list)
    skill: Optional[str] = None
    category: Optional[str] = None
    kind: Optional[str] = None
    difficulty: str = "normal"
    reward_hint: Optional[int] = None
    deadline_days: Optional[int] = None
    source: str = "heuristic"
    raw_intent: str = ""
    confidence: float = 0.6

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "acceptance_criteria": list(self.acceptance_criteria),
            "skill": self.skill,
            "category": self.category,
            "kind": self.kind,
            "difficulty": self.difficulty,
            "reward_hint": self.reward_hint,
            "deadline_days": self.deadline_days,
            "source": self.source,
            "raw_intent": self.raw_intent,
            "confidence": round(self.confidence, 2),
        }


def _detect_skill(text: str) -> Optional[str]:
    low = text.lower()
    for token, keywords in _SKILL_RULES:
        for kw in keywords:
            if kw.lower() in low:
                return token
    return None


def _detect_difficulty(text: str) -> str:
    low = text.lower()
    up = any(w in low for w in _DIFFICULTY_UP_WORDS)
    down = any(w in low for w in _DIFFICULTY_DOWN_WORDS)
    if up and not down:
        return "hard"
    if down and not up:
        return "easy"
    return "normal"


def _detect_deadline_days(text: str) -> Optional[int]:
    low = text.lower()
    for pattern, unit in _DEADLINE_PATTERNS:
        m = pattern.search(low)
        if not m:
            continue
        if unit == "today":
            return 1
        if unit == "tomorrow":
            return 2
        if unit == "thisweek":
            return 7
        try:
            n = int(m.group(1))
        except (IndexError, ValueError):
            continue
        if unit == "days":
            return max(1, min(n, 90))
        if unit == "hours":
            return max(1, min((n + 23) // 24, 90))
        if unit == "weeks":
            return max(1, min(n * 7, 90))
    return None


def _detect_reward_hint(text: str) -> Optional[int]:
    low = text.lower()
    for pattern in _REWARD_PATTERNS:
        m = pattern.search(low)
        if m:
            try:
                val = int(m.group(1))
                if 1 <= val <= 10000:
                    return val
            except (IndexError, ValueError):
                continue
    return None


def _first_sentence(text: str, max_len: int = 60) -> str:
    text = text.strip()
    if not text:
        return ""
    for sep in ["。", "\n", ". ", "! ", "? ", "；", ";", "，"]:
        idx = text.find(sep)
        if 0 < idx < max_len * 2:
            text = text[: idx + len(sep)].strip(" 。.;；!?")
            break
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text


def _title_from_intent(text: str, skill: Optional[str]) -> str:
    first = _first_sentence(text, max_len=40)
    if first:
        return first
    if skill:
        return f"{skill} 任务"
    return "AI Agent 任务"


def _acceptance_default(skill: Optional[str]) -> List[str]:
    base = ["产出可直接交付、语义准确无误", "提供简要说明或运行步骤"]
    if skill == "bug_fix":
        return ["复现并修复报告中的问题", "附带单元测试或最小可复现脚本", "不引入回归"]
    if skill == "code_review":
        return ["对每个改动点提供审阅意见", "至少列出 3 条可执行的改进建议"]
    if skill == "data_cleaning":
        return ["输出清洗后的数据文件（CSV/Parquet）", "列出清洗规则与被过滤的行数", "保留原始列并做可追溯映射"]
    if skill == "data_analysis":
        return ["输出 Notebook 或报告（md/pdf）", "核心结论配图表", "对数据源与假设做说明"]
    if skill == "translation":
        return ["逐段对照翻译", "保留术语一致性", "复核润色一遍"]
    if skill == "copywriting":
        return ["满足给定字数", "分段清晰", "可直接发布（无错别字）"]
    if skill == "ui_design":
        return ["输出设计稿源文件（Figma/Sketch/PSD）", "导出所需尺寸的切图", "包含至少一个交互原型"]
    if skill == "research":
        return ["提供至少 5 个参考来源", "输出综述 md 文档", "标明关键结论与局限"]
    return base


def _description_markdown(intent: str, draft: "IntentDraft") -> str:
    lines: List[str] = []
    lines.append(f"**需求概述**：{intent.strip()}")
    lines.append("")
    if draft.skill:
        lines.append(f"- 推测技能：`{draft.skill}`")
    if draft.category:
        lines.append(f"- 任务类别：{draft.category}")
    if draft.difficulty and draft.difficulty != "normal":
        lines.append(f"- 难度：{draft.difficulty}")
    if draft.deadline_days:
        lines.append(f"- 期望完成时限：{draft.deadline_days} 天")
    if draft.reward_hint:
        lines.append(f"- 发布方预算提示：{draft.reward_hint} 点")
    lines.append("")
    lines.append("**验收标准（初稿）**：")
    for i, crit in enumerate(draft.acceptance_criteria, 1):
        lines.append(f"{i}. {crit}")
    return "\n".join(lines).strip()


def _heuristic_parse(intent: str) -> IntentDraft:
    intent = (intent or "").strip()
    if not intent:
        raise ValueError("intent_empty")

    skill = _detect_skill(intent)
    category = _SKILL_TO_CATEGORY.get(skill) if skill else None
    kind = _SKILL_TO_KIND.get(skill) if skill else None
    difficulty = _detect_difficulty(intent)
    deadline = _detect_deadline_days(intent)
    reward = _detect_reward_hint(intent)

    draft = IntentDraft(
        title=_title_from_intent(intent, skill),
        description="",
        skill=skill,
        category=category,
        kind=kind,
        difficulty=difficulty,
        deadline_days=deadline,
        reward_hint=reward,
        source="heuristic",
        raw_intent=intent,
        confidence=0.5 + (0.2 if skill else 0) + (0.1 if deadline else 0) + (0.1 if reward else 0),
    )
    draft.acceptance_criteria = _acceptance_default(skill)
    draft.description = _description_markdown(intent, draft)
    return draft


def _llm_enhance(draft: IntentDraft, *, timeout_seconds: float = 8.0) -> IntentDraft:
    """可选：调用 OpenAI Chat Completions 对启发式结果做润色与验收标准扩展。

    - 需要环境变量 `OPENAI_API_KEY`（缺失直接返回原 draft）。
    - 失败不抛出异常，返回原 draft 并标记 source='heuristic_fallback'。
    - 模型：默认 `gpt-4o-mini`，可用 `CLAWJOB_INTENT_LLM_MODEL` 覆盖。
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return draft
    try:
        import requests
    except Exception:
        return draft

    model = os.getenv("CLAWJOB_INTENT_LLM_MODEL", "gpt-4o-mini")
    prompt = (
        "你是任务拆解助手。请根据下面的一句话需求与启发式草稿，产出更准确的任务草稿 JSON，"
        "字段包含：title(≤40字)、description(markdown)、acceptance_criteria(string[], 3-5条)、"
        "skill、category、kind、difficulty(easy|normal|hard|expert)、deadline_days(int, 可空)、"
        "reward_hint(int, 可空)。\n\n"
        f"一句话需求：{draft.raw_intent}\n\n"
        f"启发式草稿：{json.dumps(draft.to_dict(), ensure_ascii=False)}\n\n"
        "仅输出一个 JSON 对象，不要多余文字。"
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你输出严格的 JSON，不要解释。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }
    base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    try:
        r = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps(body),
            timeout=timeout_seconds,
        )
        if r.status_code != 200:
            return draft
        payload = r.json()
        content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        data = json.loads(content)
    except Exception:
        return draft

    def _pick_str(key: str, fallback: Optional[str]) -> Optional[str]:
        v = data.get(key)
        return str(v).strip() if isinstance(v, str) and v.strip() else fallback

    def _pick_int(key: str, fallback: Optional[int]) -> Optional[int]:
        v = data.get(key)
        try:
            return int(v) if v is not None else fallback
        except (TypeError, ValueError):
            return fallback

    merged = IntentDraft(
        title=(_pick_str("title", draft.title) or draft.title)[:80],
        description=_pick_str("description", draft.description) or draft.description,
        acceptance_criteria=[str(x).strip() for x in (data.get("acceptance_criteria") or []) if str(x).strip()][:8] or draft.acceptance_criteria,
        skill=_pick_str("skill", draft.skill),
        category=_pick_str("category", draft.category),
        kind=_pick_str("kind", draft.kind),
        difficulty=_pick_str("difficulty", draft.difficulty) or draft.difficulty,
        reward_hint=_pick_int("reward_hint", draft.reward_hint),
        deadline_days=_pick_int("deadline_days", draft.deadline_days),
        source="llm",
        raw_intent=draft.raw_intent,
        confidence=min(0.95, draft.confidence + 0.2),
    )
    if not merged.acceptance_criteria:
        merged.acceptance_criteria = draft.acceptance_criteria
    return merged


def parse_intent(intent: str, *, use_llm: bool = False) -> Dict[str, Any]:
    """对外主入口：返回 to_dict() 结果。"""
    draft = _heuristic_parse(intent)
    if use_llm:
        draft = _llm_enhance(draft)
    return draft.to_dict()
