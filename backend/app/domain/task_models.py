"""Task request/response models."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

class EscrowMilestoneIn(BaseModel):
    """托管里程碑：title + weight + acceptance_criteria（weight 之和须为 1）"""

    title: str
    weight: float
    acceptance_criteria: str = ""


class AuctionConfigIn(BaseModel):
    """反向竞标配置：开启后 reward_points 作为 max_reward 上限从账户扣除。"""
    enabled: bool = False
    min_reward: int = 0  # 底价，可为 0 表示不设
    deadline: Optional[str] = None  # ISO8601；到期不再接受新报价
    auto_pick: str = "manual"  # manual | lowest_price


class PublishTaskBody(BaseModel):
    title: str
    description: str = ""
    task_type: str = "general"
    priority: str = "medium"
    reward_points: int = 0  # 任务奖励点（发布时从账户扣减，验收通过或超时后发给接取者）
    completion_webhook_url: str = ""  # 有奖励点时必填：接取者提交完成时 POST 回调此 URL，供发布方验收
    invited_agent_ids: list = []  # 可选：仅这些 Agent 可接取；空表示对所有人开放
    creator_agent_id: Optional[int] = None  # 可选：由某 Agent 代发（须为当前用户的 Agent）
    # NOTE: translated comment in English.
    escrow_milestones: List[EscrowMilestoneIn] = []
    auction: Optional[AuctionConfigIn] = None  # 反向竞标配置
    # NOTE: translated comment in English.
    category: str = ""  # 任务分类：development, design, research, writing, data, other
    requirements: str = ""  # 详细要求说明
    # NOTE: translated comment in English.
    location: str = ""  # 地点要求，如 "远程"、"北京"
    duration_estimate: str = ""  # 预计时长，如 "~1h"、"~3h"
    skills: list = []  # 所需技能标签，如 ["数据分析", "Python"]
    discord_webhook_url: str = ""  # 可选：将任务推送到指定 Discord 频道，便于具备 Skill 的 Agent 发现并接取
    verification_method: str = "manual_review"  # manual_review | proof_link | checklist | hybrid
    verification_requirements: list = []  # 验收清单要求（用于 checklist / hybrid）
    related_skill_token: str = ""  # 可选：将任务显式关联到某个已发布 Skill token
    verification_hours: Optional[int] = None  # 发布者验收窗口（小时），默认 6，范围 1–168
    collaborative: bool = False  # 可选：标记为适合多 Agent / 协作型任务（展示用）
    settlement_mode: str = "platform_credits"  # platform_credits | agent_direct（Agent 间直接结算）
class SubscribeTaskBody(BaseModel):
    agent_id: int


class RejectCompletionBody(BaseModel):
    rejection_reason: str  # 必填：作为 RL 惩罚信号，供接取者改进


class EscrowDisputeBody(BaseModel):
    reason: str
    evidence: dict = {}


class SubmitCompletionBody(BaseModel):
    result_summary: str = ""  # 完成结果摘要，会随 webhook 发给发布方
    evidence: dict = {}  # 可选证据/输出，会随 webhook 发给发布方


class ConfirmTaskBody(BaseModel):
    verification_mode: str = "manual_review"  # manual_review | spot_check | webhook_result
    verification_note: str = ""
class PlaceBidBody(BaseModel):
    agent_id: int
    price: int
    eta_hours: Optional[int] = None
    proposal: str = ""
class CloseAuctionBody(BaseModel):
    auto_pick_if_bids: bool = True  # 到期若仍有 active 报价且 auto_pick=lowest_price，则自动选最低价
class PostCommentBody(BaseModel):
    content: str = ""
    agent_id: Optional[int] = None  # A2A: 以该 Agent 身份留言（需为当前用户的 Agent）
    kind: str = "message"  # message | status_update
class A2AMessageBody(BaseModel):
    content: str = ""
    agent_id: Optional[int] = None
    kind: str = "message"  # message | status_update
class WorkflowPlanBody(BaseModel):
    nodes: List[int]
    edges: List[dict] = []


class BatchConfirmBody(BaseModel):
    task_ids: List[int]


class PaymentMethodIn(BaseModel):
    type: str  # alipay | wechat | bank | crypto | custom
    label: str = ""
    account_masked: str = ""
    details_for_counterparty: str = ""
    webhook_url: str = ""


class PaymentProfileBody(BaseModel):
    methods: List[PaymentMethodIn] = []


class PayerMarkPaidBody(BaseModel):
    proof_links: List[str] = []
    note: str = ""
    method_used: str = ""

