"""
Agent Arena - Security Module with Agent Authentication
JWT-based authentication with agent-specific permissions and rate limiting.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import bcrypt

# Password hashing (bcrypt 72-byte limit; direct bcrypt to avoid passlib compat issues)

def _truncate_password(p: str) -> bytes:
    return p.encode("utf-8")[:72]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return bcrypt.checkpw(_truncate_password(plain_password), hashed_password.encode("utf-8"))

def get_password_hash(password: str) -> str:
    """Hash a password (truncated to 72 bytes for bcrypt)."""
    return bcrypt.hashpw(_truncate_password(password), bcrypt.gensalt()).decode("utf-8")

# JWT settings（生产环境必须设置 JWT_SECRET 环境变量）
SECRET_KEY = os.getenv("JWT_SECRET", "clawjob-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
AGENT_TOKEN_EXPIRE_HOURS = 24

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Rate limiter（全局默认 120 次/分钟，可通过 RATE_LIMIT_DEFAULT 覆盖）
_rate_limit_default = os.getenv("RATE_LIMIT_DEFAULT", "120/minute")
limiter = Limiter(key_func=get_remote_address, default_limits=[_rate_limit_default])

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_agent_token(agent_id: str, agent_name: str) -> str:
    """Create a JWT token specifically for an agent."""
    expire = datetime.utcnow() + timedelta(hours=AGENT_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": agent_id,
        "agent_name": agent_name,
        "exp": expire,
        "type": "agent"
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = {"user_id": user_id, "token_type": payload.get("type", "user")}
        return token_data
    except jwt.PyJWTError:
        raise credentials_exception

async def get_current_agent(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current agent from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate agent credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        agent_id: str = payload.get("sub")
        agent_type = payload.get("type")
        if agent_id is None or agent_type != "agent":
            raise credentials_exception
        token_data = {
            "agent_id": agent_id,
            "agent_name": payload.get("agent_name"),
            "token_type": "agent"
        }
        return token_data
    except jwt.PyJWTError:
        raise credentials_exception

def verify_agent_access(agent_id: str, required_permissions: list) -> bool:
    """Verify if an agent has the required permissions."""
    # In a real implementation, this would check against a database
    # For now, we'll assume all agents have basic permissions
    return True

# Security headers middleware
async def security_headers_middleware(request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response