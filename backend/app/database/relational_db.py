"""
Relational Database (PostgreSQL) integration for Agent Arena.
Provides structured data storage for agents, tasks, and user management.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from typing import Optional, List
import os
from datetime import datetime

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agentarena:agentarena123@localhost:5432/agentarena")

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # 空表示仅 OAuth 登录
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    credits = Column(Integer, default=0)  # 任务点/信用点余额
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # NOTE: translated comment in English.
    receiving_account_type = Column(String(32), nullable=True)  # alipay, bank_card 等
    receiving_account_name = Column(String(64), nullable=True)  # 户名/实名
    receiving_account_number = Column(String(128), nullable=True)  # 账号/卡号（可脱敏）
    commission_balance = Column(Integer, default=0, nullable=False)  # 累计未提现佣金（任务点）
    referral_code = Column(String(32), nullable=True, unique=True, index=True)  # 个人邀请码
    # KYC / KYB（C-14）
    kyc_status = Column(String(16), default="none", nullable=False, index=True)  # none | pending | approved | rejected
    kyc_kind = Column(String(16), nullable=True)  # personal | business
    kyc_approved_at = Column(DateTime, nullable=True)
    # 当前活跃工作区（D-17，可空表示个人模式）
    active_workspace_id = Column(Integer, nullable=True, index=True)
    # 订阅档位（D-18）
    subscription_tier = Column(String(16), default="free", nullable=False, index=True)  # free | pro | team | enterprise
    subscription_renews_at = Column(DateTime, nullable=True)
    # Relationships
    agents = relationship("Agent", back_populates="owner")
    tasks = relationship("Task", back_populates="owner")

class Agent(Base):
    """Agent model for AI agents"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    agent_type = Column(String, nullable=False)  # e.g., "researcher", "coder", "analyst"
    personality_traits = Column(JSON)  # Store personality traits as JSON
    capabilities = Column(JSON)  # Store agent capabilities
    config = Column(JSON)  # Store agent configuration
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    category = Column(String(32), nullable=True)  # 注册来源：skill | mcp | web | api
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # NOTE: translated comment in English.
    owner = relationship("User", back_populates="agents")
    tasks = relationship("Task", back_populates="agent", foreign_keys="Task.agent_id")
    conversations = relationship("Conversation", back_populates="agent")
    published_template = relationship("PublishedAgentTemplate", back_populates="agent", uselist=False)

class PublishedAgentTemplate(Base):
    """已发布的 Agent 模板 / Skill：供市场展示与下载（OpenClaw 配置 + Skill 或仅 Skill）"""
    __tablename__ = "published_agent_templates"
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, unique=True)  # 一 Agent 仅可发布一条
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    verified = Column(Boolean, default=False, nullable=False)  # 平台验证标识
    version_tag = Column(String(64), nullable=False, default="v1")  # 版本标签（如 v1, v1.1, prod-202603）
    download_agent_url = Column(Text, nullable=True)  # 下载完整 Agent 模板的 URL
    download_skill_url = Column(Text, nullable=True)  # 仅下载 Skill 的 URL
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    agent = relationship("Agent", back_populates="published_template")


class PublishedSkill(Base):
    """已发布的 Skill：供技能市场展示与下载（独立于 Agent 模板）。"""
    __tablename__ = "published_skills"

    id = Column(Integer, primary_key=True, index=True)
    # NOTE: translated comment in English.
    skill_token = Column(String(256), unique=True, index=True, nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    verified = Column(Boolean, default=False, nullable=False)  # 简化：根据该 token 下的完成任务数推导
    version_tag = Column(String(64), nullable=False, default="v1")  # 版本标签（如 v1, v1.1, prod-202603）
    download_skill_url = Column(Text, nullable=True)  # 可选：Skill 包下载链接
    # D-19 付费分成
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    pricing_model = Column(String(16), default="free", nullable=False)  # free | per_invoke | per_download | subscription
    price_per_unit = Column(Integer, default=0, nullable=False)  # 任务点
    revenue_share_bp = Column(Integer, default=7000, nullable=False)  # 作者分成（基点，默认 70%）
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class Task(Base):
    """Task model for agent tasks"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")  # pending, running, completed, failed
    priority = Column(String, default="medium")  # low, medium, high, critical
    task_type = Column(String, nullable=False)  # e.g., "research", "coding", "analysis"
    input_data = Column(JSON)  # Input data for the task
    output_data = Column(JSON)  # Output data from the task
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # 接取者 agent，空表示待接取
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 发布者
    creator_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # 可选：由某 Agent 代发，空表示用户直接发布
    reward_points = Column(Integer, default=0)  # 任务奖励点（完成时发给接取者）
    completion_webhook_url = Column(Text, nullable=True)  # 完成回调 URL（有奖励时发布者必填，接取者提交完成时 POST 通知）
    submitted_at = Column(DateTime, nullable=True)  # 接取者提交完成时间
    verification_deadline_at = Column(DateTime, nullable=True)  # 发布者验收截止（submitted_at + 6h，超时自动完成）
    invited_agent_ids = Column(JSON, nullable=True)  # 可选：仅这些 Agent 可接取；空/空数组表示对所有人开放
    category = Column(String(64), nullable=True)  # 任务分类：development, design, research, writing, data, other
    requirements = Column(Text, nullable=True)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"))  # For subtasks
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)
    
    # NOTE: translated comment in English.
    agent = relationship("Agent", back_populates="tasks", foreign_keys=[agent_id])
    owner = relationship("User", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks = relationship("Task", remote_side=[parent_task_id], back_populates="parent_task", overlaps="parent_task")
    conversation = relationship("Conversation", back_populates="task", uselist=False)

class Conversation(Base):
    """Conversation model for agent interactions"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    messages = Column(JSON)  # Store conversation messages as JSON
    context = Column(JSON)  # Store conversation context
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="conversations")
    task = relationship("Task", back_populates="conversation")

class KnowledgeBase(Base):
    """Knowledge base model for storing agent knowledge"""
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text)  # Raw content
    extra_metadata = Column(JSON)  # Additional metadata
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User")


class TaskSubscription(Base):
    """任务订阅：某 Agent 订阅了某任务"""
    __tablename__ = "task_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    # Relationships
    task = relationship("Task", backref="subscriptions")
    agent = relationship("Agent", backref="subscribed_tasks")


class TaskComment(Base):
    """任务评论/动态"""
    __tablename__ = "task_comments"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    kind = Column(String(32), default="comment")
    created_at = Column(DateTime, default=func.now())
    task = relationship("Task", backref="comments")
    user = relationship("User", backref="task_comments")


class InternalMessage(Base):
    """站内信：用户之间的私信消息。"""
    __tablename__ = "internal_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    related_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    sender = relationship("User", foreign_keys=[sender_user_id], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_user_id], backref="received_messages")
    related_task = relationship("Task")


class ChatTopic(Base):
    """社区聊天话题：按 Skill 聚合讨论。"""
    __tablename__ = "chat_topics"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    skill_tag = Column(String(64), nullable=False, index=True)
    creator_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True, index=True)
    visibility = Column(String(16), default="public", nullable=False)  # public | internal
    status = Column(String(16), default="active", nullable=False, index=True)  # active | archived
    heat_score = Column(Float, default=0.0, nullable=False, index=True)
    auto_generated = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    creator_agent = relationship("Agent")


class ChatMessage(Base):
    """社区聊天消息（Markdown 存储 + 预清洗 HTML）。"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("chat_topics.id"), nullable=False, index=True)
    author_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 便于权限与通知复用
    reply_to_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True, index=True)
    content_md = Column(Text, nullable=False)
    content_html_sanitized = Column(Text, nullable=True)
    # 多模态附件（URL 引用）：[{kind,url,mime_type,name,size_bytes,meta}]
    attachments = Column(JSON, nullable=True)
    # 消息意图（学习/协作向，可选）：chat | tip | question | resource | recap
    intent = Column(String(32), nullable=True, index=True)
    comment_count = Column(Integer, default=0, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    topic = relationship("ChatTopic", backref="messages")
    author_agent = relationship("Agent")
    user = relationship("User")
    reply_to = relationship("ChatMessage", remote_side=[id], backref="replies")


class ChatTopicMember(Base):
    """话题成员（Agent 维度），用于未读与推荐分发过滤。"""
    __tablename__ = "chat_topic_members"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("chat_topics.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    role = Column(String(16), default="member", nullable=False)  # owner | member
    last_read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)

    topic = relationship("ChatTopic", backref="members")
    agent = relationship("Agent")


class ChatDispatchLog(Base):
    """热门话题/回复分发记录（幂等 + 限频依据）。"""
    __tablename__ = "chat_dispatch_logs"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("chat_topics.id"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True, index=True)
    target_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    reason = Column(String(128), nullable=False, default="hot_topic")
    sent_at = Column(DateTime, default=func.now(), index=True)

    topic = relationship("ChatTopic")
    message = relationship("ChatMessage")
    target_agent = relationship("Agent")


class PaymentMethod(Base):
    """用户绑定的支付方式：支付宝、信用卡、比特币等"""
    __tablename__ = "payment_methods"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # alipay, credit_card, bitcoin
    masked_info = Column(String, nullable=False)  # 脱敏展示，如 支付宝 ***@xx.com / 卡尾号1234 / 地址bc1q...
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    # Relationships
    user = relationship("User", backref="payment_methods")


class CreditTransaction(Base):
    """信用点流水"""
    __tablename__ = "credit_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # 正=收入，负=支出
    type = Column(String, nullable=False)  # recharge, task_publish, task_reward, task_refund
    ref_id = Column(Integer, nullable=True)  # 关联 task_id / recharge_order_id 等
    remark = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    user = relationship("User", backref="credit_transactions")


class PlatformClearingAccount(Base):
    """平台中转账户：用于管理任务佣金（手续费），与支付宝关联便于结算"""
    __tablename__ = "platform_clearing_accounts"
    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Integer, default=0, nullable=False)  # 累计手续费（任务点）
    alipay_account = Column(String(128), nullable=True)  # 支付宝账号（脱敏展示，如 platform***@alipay.com）
    alipay_name = Column(String(64), nullable=True)  # 支付宝实名（可选）
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    records = relationship("PlatformCommissionRecord", back_populates="clearing_account")


class PlatformCommissionRecord(Base):
    """平台佣金流水：每笔任务手续费的记录"""
    __tablename__ = "platform_commission_records"
    id = Column(Integer, primary_key=True, index=True)
    clearing_account_id = Column(Integer, ForeignKey("platform_clearing_accounts.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    remark = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=func.now())
    clearing_account = relationship("PlatformClearingAccount", back_populates="records")


class UserCommissionRecord(Base):
    """用户佣金流水：任务发布者配置的佣金记录"""
    __tablename__ = "user_commission_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    remark = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=func.now())
    user = relationship("User", backref="commission_records")


class UserApiCredential(Base):
    """用户托管的第三方 API 密钥（存储密文与脱敏显示值）。"""
    __tablename__ = "user_api_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(64), nullable=False)  # openai, anthropic, custom
    label = Column(String(128), nullable=False)  # 用户自定义别名
    secret_cipher = Column(Text, nullable=False)  # 密文
    secret_masked = Column(String(64), nullable=False)  # 脱敏展示，如 sk-***abcd
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    user = relationship("User", backref="api_credentials")


class RechargeOrder(Base):
    """充值订单：信用卡/支付宝/比特币等渠道，创建订单后返回支付链接/二维码/地址，支付完成后确认到账"""
    __tablename__ = "recharge_orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # 任务点数量
    payment_method_type = Column(String, nullable=False)  # credit_card, alipay, bitcoin
    status = Column(String, nullable=False, default="pending")  # pending, paid, failed, cancelled
    gateway_order_id = Column(String, nullable=True)  # 支付网关订单号，生产环境用
    payment_url = Column(Text, nullable=True)  # 信用卡跳转支付 URL
    payment_qr = Column(Text, nullable=True)  # 支付宝等二维码内容
    btc_address = Column(String, nullable=True)  # 比特币充值地址
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    user = relationship("User", backref="recharge_orders")


class VerificationCode(Base):
    """邮箱验证码：注册时发送，有效期 5 分钟"""
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(256), nullable=False, index=True)
    code = Column(String(16), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())


class SystemLog(Base):
    """系统运行与审计日志：API 请求、注册、任务等关键事件"""
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now())
    level = Column(String(16), nullable=False, index=True)  # info, warning, error
    category = Column(String(64), nullable=False, index=True)  # request, auth, task, agent, system
    message = Column(Text, nullable=False)
    extra = Column(JSON, nullable=True)  # 扩展字段：path, method, status_code, user_id 等
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    path = Column(String(512), nullable=True)
    method = Column(String(16), nullable=True)
    status_code = Column(Integer, nullable=True)


class TaskBid(Base):
    """反向竞标：Agent 对某个已开启竞拍的任务提交报价。"""
    __tablename__ = "task_bids"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    bidder_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    price = Column(Integer, nullable=False)  # 报价（任务点）
    eta_hours = Column(Integer, nullable=True)  # 预计交付时长（小时）
    proposal = Column(Text, nullable=True)  # 方案说明
    status = Column(String(16), nullable=False, default="active", index=True)
    # active | withdrawn | won | lost
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    task = relationship("Task", backref="bids")
    agent = relationship("Agent")
    bidder = relationship("User")


class Referral(Base):
    """邀请注册记录：新用户通过邀请码注册即写入一条；首单返点只发放一次。"""
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, index=True)
    referrer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    invitee_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    code = Column(String(32), nullable=False, index=True)
    signup_at = Column(DateTime, default=func.now())
    first_task_reward_at = Column(DateTime, nullable=True)
    referrer_bonus_points = Column(Integer, default=0, nullable=False)
    invitee_bonus_points = Column(Integer, default=0, nullable=False)
    referrer = relationship("User", foreign_keys=[referrer_user_id], backref="referrals_sent")
    invitee = relationship("User", foreign_keys=[invitee_user_id])


class SafetyEvent(Base):
    """内容安全事件：发布/提交/留言等文本被敏感词或 PII 命中的审计记录。"""
    __tablename__ = "safety_events"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    source = Column(String(32), nullable=False, index=True)
    # publish_task | submit_completion | message | comment | intent | other
    related_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    action = Column(String(16), nullable=False)  # block | redact | warn
    reasons = Column(JSON, nullable=True)  # e.g. ["blacklist:word_xxx", "pii:email"]
    snippet = Column(Text, nullable=True)  # 原文片段（可能包含已脱敏版本）
    pii_types = Column(JSON, nullable=True)  # ["email", "phone", "id_card"]


class ExecutionRun(Base):
    """单次 /tasks/{id}/execute 的运行。"""
    __tablename__ = "execution_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), nullable=False, unique=True, index=True)  # uuid
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    started_at = Column(DateTime, default=func.now(), index=True)
    ended_at = Column(DateTime, nullable=True)
    ok = Column(Boolean, default=False, nullable=False)
    quota_exceeded = Column(Boolean, default=False, nullable=False)
    error = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0, nullable=False)
    cost_credits = Column(Integer, default=0, nullable=False)
    duration_ms = Column(Integer, default=0, nullable=False)
    triggered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)


class KycRecord(Base):
    """KYC / KYB 提交记录（C-14）。每个用户最多保留多条历史记录，最新一条决定 user.kyc_status。"""
    __tablename__ = "kyc_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(16), nullable=False)  # personal | business
    status = Column(String(16), nullable=False, default="pending", index=True)  # pending | approved | rejected
    legal_name = Column(String(128), nullable=True)
    id_type = Column(String(32), nullable=True)  # id_card | passport | other
    id_number_masked = Column(String(64), nullable=True)
    id_number_cipher = Column(Text, nullable=True)
    country = Column(String(64), nullable=True)
    business_name = Column(String(256), nullable=True)
    business_id = Column(String(128), nullable=True)  # 统一社会信用代码 / Tax ID
    contact_email = Column(String(256), nullable=True)
    contact_phone = Column(String(64), nullable=True)
    attachments = Column(JSON, nullable=True)  # [{name, url, hash}]
    submitted_at = Column(DateTime, default=func.now(), index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(String(512), nullable=True)


class Workspace(Base):
    """企业 / 团队工作区（D-17）。共享余额、共享发布权限。"""
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(64), nullable=False, unique=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kyb_record_id = Column(Integer, ForeignKey("kyc_records.id"), nullable=True)
    plan = Column(String(16), default="free", nullable=False)  # free | team | enterprise
    seats = Column(Integer, default=3, nullable=False)
    credits = Column(Integer, default=0, nullable=False)  # 工作区余额（任务点）
    billing_email = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WorkspaceMember(Base):
    """工作区成员与角色。"""
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False, default="publisher")  # owner | admin | publisher | accounting | auditor
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    joined_at = Column(DateTime, default=func.now())


class WorkspaceInvitation(Base):
    """工作区邀请：通过 token 接受加入。"""
    __tablename__ = "workspace_invitations"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    email = Column(String(256), nullable=False, index=True)
    role = Column(String(16), nullable=False, default="publisher")
    token = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(String(16), default="pending", nullable=False)  # pending | accepted | revoked | expired
    invited_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    accepted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class SubscriptionPlan(Base):
    """订阅计划目录（D-18）。Free / Pro / Team / Enterprise。"""
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), nullable=False, unique=True, index=True)  # free | pro | team | enterprise
    name = Column(String(64), nullable=False)
    monthly_price_cents = Column(Integer, default=0, nullable=False)
    monthly_credits = Column(Integer, default=0, nullable=False)  # 每月赠送任务点
    seat_quota = Column(Integer, default=1, nullable=False)
    commission_discount_bp = Column(Integer, default=0, nullable=False)  # 佣金折扣（基点，1bp=0.01%）
    features = Column(JSON, nullable=True)  # ["rfq", "priority_match", "sandbox_x", ...]
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now())


class Subscription(Base):
    """订阅订单（D-18）。绑定 user 或 workspace 之一。"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    plan_code = Column(String(32), nullable=False, index=True)
    status = Column(String(16), default="active", nullable=False)  # active | cancelled | expired
    started_at = Column(DateTime, default=func.now())
    renews_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    seats = Column(Integer, default=1, nullable=False)
    last_charge_amount = Column(Integer, default=0, nullable=False)


class SkillRevenueShare(Base):
    """Skill 付费分成（D-19）。每次 Skill 调用 / 下载结算的明细。"""
    __tablename__ = "skill_revenue_shares"

    id = Column(Integer, primary_key=True, index=True)
    skill_token = Column(String(256), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    consumer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    related_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True, index=True)
    event_kind = Column(String(16), nullable=False, default="invoke")  # invoke | download | subscribe
    gross_amount = Column(Integer, nullable=False)  # 计费总额（任务点）
    platform_fee = Column(Integer, default=0, nullable=False)
    author_payout = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), index=True)


class SkillPurchase(Base):
    """Skill 付费购买/订阅凭证（D-19 闭环）。

    买家以 `per_download` 购买后获得可重复下载的权益；`subscription` 购买获得带
    到期时间的权益。`per_invoke` 不在此表落账（随任务结算，见 SkillRevenueShare）。
    退款窗口内可申请退款（status -> refunded）。
    """
    __tablename__ = "skill_purchases"

    id = Column(Integer, primary_key=True, index=True)
    skill_token = Column(String(256), nullable=False, index=True)
    buyer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    author_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    pricing_model = Column(String(16), nullable=False, default="per_download")  # per_download | subscription
    gross_amount = Column(Integer, nullable=False, default=0)
    platform_fee = Column(Integer, nullable=False, default=0)
    author_payout = Column(Integer, nullable=False, default=0)
    revenue_share_id = Column(Integer, ForeignKey("skill_revenue_shares.id"), nullable=True, index=True)
    status = Column(String(16), nullable=False, default="active", index=True)  # active | refunded | expired
    expires_at = Column(DateTime, nullable=True)  # subscription 到期；download 为空（永久权益）
    refunded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)


class WithdrawalRequest(Base):
    """提现申请（C-14 提现闸门：approved 后才能创建并执行）。"""
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # 任务点
    status = Column(String(16), nullable=False, default="pending", index=True)
    # pending | approved | rejected | paid | cancelled
    receiving_account_type = Column(String(32), nullable=True)
    receiving_account_name = Column(String(64), nullable=True)
    receiving_account_number = Column(String(128), nullable=True)
    submitted_at = Column(DateTime, default=func.now(), index=True)
    processed_at = Column(DateTime, nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remark = Column(String(512), nullable=True)


class ExecutionStep(Base):
    """执行过程的细粒度步骤：工具调用 / A2A 消息 / 阶段事件等。"""
    __tablename__ = "execution_steps"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    idx = Column(Integer, nullable=False, default=0)
    kind = Column(String(32), nullable=False)  # start | tool | a2a | output | error | quota | end
    name = Column(String(128), nullable=True)
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    ok = Column(Boolean, default=True, nullable=False)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=func.now(), index=True)
    duration_ms = Column(Integer, default=0, nullable=False)
    tokens = Column(Integer, default=0, nullable=False)
    cost_credits = Column(Integer, default=0, nullable=False)


# Database initialization function
def init_db():
    """Initialize the database tables"""
    Base.metadata.create_all(bind=engine)
    # NOTE: translated comment in English.
    try:
        with engine.connect() as conn:
            for col, typ in [
                ("receiving_account_type", "VARCHAR(32)"),
                ("receiving_account_name", "VARCHAR(64)"),
                ("receiving_account_number", "VARCHAR(128)"),
                ("commission_balance", "INTEGER DEFAULT 0 NOT NULL"),
                ("referral_code", "VARCHAR(32)"),
                ("kyc_status", "VARCHAR(16) DEFAULT 'none' NOT NULL"),
                ("kyc_kind", "VARCHAR(16)"),
                ("kyc_approved_at", "TIMESTAMP"),
                ("active_workspace_id", "INTEGER"),
                ("subscription_tier", "VARCHAR(16) DEFAULT 'free' NOT NULL"),
                ("subscription_renews_at", "TIMESTAMP"),
            ]:
                try:
                    if engine.dialect.name == "postgresql":
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}"))
                    else:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typ}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
            for col, typ in [
                ("category", "VARCHAR(64)"),
                ("requirements", "TEXT"),
            ]:
                try:
                    if engine.dialect.name == "postgresql":
                        conn.execute(text(f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS {col} {typ}"))
                    else:
                        conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col} {typ}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
            for col, typ in [
                ("version_tag", "VARCHAR(64) DEFAULT 'v1' NOT NULL"),
            ]:
                try:
                    if engine.dialect.name == "postgresql":
                        conn.execute(text(f"ALTER TABLE published_agent_templates ADD COLUMN IF NOT EXISTS {col} {typ}"))
                        conn.execute(text(f"ALTER TABLE published_skills ADD COLUMN IF NOT EXISTS {col} {typ}"))
                    else:
                        conn.execute(text(f"ALTER TABLE published_agent_templates ADD COLUMN {col} {typ}"))
                        conn.execute(text(f"ALTER TABLE published_skills ADD COLUMN {col} {typ}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
            for col, typ in [
                ("author_user_id", "INTEGER"),
                ("pricing_model", "VARCHAR(16) DEFAULT 'free' NOT NULL"),
                ("price_per_unit", "INTEGER DEFAULT 0 NOT NULL"),
                ("revenue_share_bp", "INTEGER DEFAULT 7000 NOT NULL"),
            ]:
                try:
                    if engine.dialect.name == "postgresql":
                        conn.execute(text(f"ALTER TABLE published_skills ADD COLUMN IF NOT EXISTS {col} {typ}"))
                    else:
                        conn.execute(text(f"ALTER TABLE published_skills ADD COLUMN {col} {typ}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
            # Community V1: chat_messages 多模态附件字段 + 消息意图
            for col, typ in [
                ("attachments", "JSON"),
                ("intent", "VARCHAR(32)"),
            ]:
                try:
                    if engine.dialect.name == "postgresql":
                        conn.execute(text(f"ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS {col} {typ}"))
                    else:
                        conn.execute(text(f"ALTER TABLE chat_messages ADD COLUMN {col} {typ}"))
                    conn.commit()
                except Exception:
                    conn.rollback()
    except Exception:
        pass
    _ensure_admin_user_from_env()


def _ensure_admin_user_from_env():
    """若设置了 ADMIN_USERNAME 与 ADMIN_PASSWORD，则创建或更新该管理员账号（is_superuser=True）。"""
    admin_username = os.getenv("ADMIN_USERNAME", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not admin_username or not admin_password:
        return
    try:
        from app.security import get_password_hash
    except Exception:
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == admin_username).first()
        hashed = get_password_hash(admin_password)
        if user:
            user.hashed_password = hashed
            user.is_superuser = True
            user.is_active = True
            db.commit()
        else:
            admin_email = os.getenv("ADMIN_EMAIL", "").strip() or f"{admin_username}@admin.local"
            if db.query(User).filter(User.email == admin_email).first():
                admin_email = f"admin_{admin_username}@admin.local"
            user = User(
                username=admin_username,
                email=admin_email,
                hashed_password=hashed,
                is_superuser=True,
                is_active=True,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


# Dependency for getting database session
def get_db():
    """Get database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD operations
class CRUDBase:
    """Base CRUD operations"""
    
    @staticmethod
    def get_by_id(db, model, id: int):
        """Get record by ID"""
        return db.query(model).filter(model.id == id).first()
    
    @staticmethod
    def get_all(db, model, skip: int = 0, limit: int = 100):
        """Get all records with pagination"""
        return db.query(model).offset(skip).limit(limit).all()
    
    @staticmethod
    def create(db, model, **kwargs):
        """Create new record"""
        db_obj = model(**kwargs)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def update(db, db_obj, **kwargs):
        """Update existing record"""
        for key, value in kwargs.items():
            setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    @staticmethod
    def delete(db, db_obj):
        """Delete record"""
        db.delete(db_obj)
        db.commit()
        return db_obj

# Specific CRUD classes
class CRUDUser(CRUDBase):
    """User CRUD operations"""
    pass

class CRUDAgent(CRUDBase):
    """Agent CRUD operations"""
    pass

class CRUDTask(CRUDBase):
    """Task CRUD operations"""
    pass

class CRUDConversation(CRUDBase):
    """Conversation CRUD operations"""
    pass

class CRUDKnowledgeBase(CRUDBase):
    """Knowledge base CRUD operations"""
    pass

# RelationalDB wrapper for dependency injection and health check
class RelationalDB:
    """Wrapper exposing init_db, get_db, and health_check."""
    def get_db(self):
        return get_db()

    async def health_check(self):
        """Health check for PostgreSQL."""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return "connected"
        except Exception as e:
            return f"error: {e}"

    async def initialize(self):
        """Create tables if not exist."""
        init_db()


# Initialize database on import
if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")