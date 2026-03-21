"""
Relational Database (PostgreSQL) integration for Agent Arena.
Provides structured data storage for agents, tasks, and user management.
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, text
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
    # 收款账户（用户配置的佣金收款使用）
    receiving_account_type = Column(String(32), nullable=True)  # alipay, bank_card 等
    receiving_account_name = Column(String(64), nullable=True)  # 户名/实名
    receiving_account_number = Column(String(128), nullable=True)  # 账号/卡号（可脱敏）
    commission_balance = Column(Integer, default=0, nullable=False)  # 累计未提现佣金（任务点）
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
    
    # Relationships（tasks 仅通过 Task.agent_id 关联，与 creator_agent_id 区分）
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
    # skill_token 用于把已发布的 Skill 与已注册 Agent 的 config.skill_bound_token 关联起来
    skill_token = Column(String(256), unique=True, index=True, nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    verified = Column(Boolean, default=False, nullable=False)  # 简化：根据该 token 下的完成任务数推导
    version_tag = Column(String(64), nullable=False, default="v1")  # 版本标签（如 v1, v1.1, prod-202603）
    download_skill_url = Column(Text, nullable=True)  # 可选：Skill 包下载链接
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
    
    # Relationships（显式指定 agent_id 为接取者关系，避免与 creator_agent_id 歧义）
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


# Database initialization function
def init_db():
    """Initialize the database tables"""
    Base.metadata.create_all(bind=engine)
    # 为已有 users 表添加收款账户与佣金字段（PostgreSQL / SQLite 兼容：忽略已存在列）
    try:
        with engine.connect() as conn:
            for col, typ in [
                ("receiving_account_type", "VARCHAR(32)"),
                ("receiving_account_name", "VARCHAR(64)"),
                ("receiving_account_number", "VARCHAR(128)"),
                ("commission_balance", "INTEGER DEFAULT 0 NOT NULL"),
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