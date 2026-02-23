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
    # 收款账户（用户收取 1% 佣金时使用）
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
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="agents")
    tasks = relationship("Task", back_populates="agent")
    conversations = relationship("Conversation", back_populates="agent")

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
    reward_points = Column(Integer, default=0)  # 任务奖励点（完成时发给接取者）
    completion_webhook_url = Column(Text, nullable=True)  # 完成回调 URL（有奖励时发布者必填，接取者提交完成时 POST 通知）
    submitted_at = Column(DateTime, nullable=True)  # 接取者提交完成时间
    verification_deadline_at = Column(DateTime, nullable=True)  # 发布者验收截止（submitted_at + 6h，超时自动完成）
    parent_task_id = Column(Integer, ForeignKey("tasks.id"))  # For subtasks
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")
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
    """用户佣金流水：任务发布者收取的 1% 佣金记录"""
    __tablename__ = "user_commission_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    remark = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=func.now())
    user = relationship("User", backref="commission_records")


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
    except Exception:
        pass

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