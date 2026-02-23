"""
ClawJob - 注册与登录（含 Google OAuth）
"""
import os
import secrets
from urllib.parse import urlencode, quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import User, get_db
from app.security import get_password_hash, create_access_token, verify_password
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

# Google OAuth 配置（从环境变量读取）
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class RegisterBody(BaseModel):
    username: str
    email: str
    password: str


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
    """用户注册"""
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="邮箱已存在")
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(
        data={"sub": str(user.id), "type": "user"},
        expires_delta=timedelta(days=7),
    )
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "username": user.username}


@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == body.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.hashed_password:
        raise HTTPException(status_code=401, detail="该账号仅支持 Google 登录")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(
        data={"sub": str(user.id), "type": "user"},
        expires_delta=timedelta(days=7),
    )
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "username": user.username}


# ---------- Google OAuth ----------
@router.get("/google")
def google_login():
    """跳转到 Google 授权页"""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="未配置 GOOGLE_CLIENT_ID")
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(url=url)


@router.get("/google/callback")
def google_callback(code: str = None, state: str = None, db: Session = Depends(get_db)):
    """Google 回调：用 code 换 token，取用户信息，创建/登录用户并重定向到前端带 token"""
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=missing_code")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=server_config")

    with httpx.Client() as client:
        # 用 code 换 access_token
        r = client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if r.status_code != 200:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=token_exchange")
    data = r.json()
    access_token = data.get("access_token")
    if not access_token:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_access_token")

    with httpx.Client() as client:
        ui = client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if ui.status_code != 200:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=userinfo")
    profile = ui.json()
    email = profile.get("email")
    name = profile.get("name") or profile.get("email", "").split("@")[0]
    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=no_email")

    # 按 email 查找或创建用户（username 用 email 前缀或 name，唯一即可）
    user = db.query(User).filter(User.email == email).first()
    if not user:
        base_username = name.replace(" ", "_")[:30] or email.split("@")[0]
        username = base_username
        n = 0
        while db.query(User).filter(User.username == username).first():
            n += 1
            username = f"{base_username}_{n}"
        user = User(
            username=username,
            email=email,
            hashed_password=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(
        data={"sub": str(user.id), "type": "user"},
        expires_delta=timedelta(days=7),
    )
    # 重定向到前端，token 放在 hash 中避免被服务器日志记录
    safe_username = quote(user.username, safe="")
    return RedirectResponse(url=f"{FRONTEND_URL}#/auth/callback?token={token}&username={safe_username}")
