import asyncio
import json
import re
import secrets

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.api.response import ok, err

router = APIRouter()


class RegisterBody(BaseModel):
    username: str
    email: str = ""
    password: str


class LoginBody(BaseModel):
    username: str = ""
    email: str = ""
    password: str


@router.post("/register")
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=body.username,
        email=body.email.strip() or None,
        hashed_password=await asyncio.to_thread(hash_password, body.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return ok({"token": token, "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role}})


@router.post("/login")
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    if not body.username:
        raise HTTPException(status_code=401, detail="请输入用户名")
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    password_ok = await asyncio.to_thread(verify_password, body.password, user.hashed_password) if user else False
    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token({"sub": str(user.id)})
    return ok({"token": token, "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role, "avatar": user.avatar, "createdAt": str(user.created_at) if user.created_at else None}})


def _safe_redirect(value: str) -> str:
    """只允许同源相对路径作为 SSO 落地页，防止 open redirect。"""
    value = (value or "").strip()
    if len(value) <= 200 and value.startswith("/") and not value.startswith("//"):
        if re.fullmatch(r"/[A-Za-z0-9\-._~!$&'()*+,;=:@/?%\[\]#]*", value):
            return value
    return "/templates"


def _sso_html_success(token: str, user: dict, redirect: str = "/templates") -> HTMLResponse:
    """SSO 成功页：把 token/userInfo 写入本地源，跳转到目标相对路径（默认模板中心）。"""
    info_json = json.dumps(user, ensure_ascii=True)
    token_lit = json.dumps(token)
    # userInfo 需写成 JSON 字符串字面量（带引号），否则 JS 会把对象强转成 "[object Object]"
    info_lit = json.dumps(info_json)
    redirect_lit = json.dumps(redirect)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="referrer" content="no-referrer">
<title>正在进入绘图平台…</title>
</head>
<body>
<script>
  localStorage.setItem('token', {token_lit});
  localStorage.setItem('userInfo', {info_lit});
  location.replace({redirect_lit});
</script>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=200)


def _sso_html_error(msg: str, portal_url: str = "https://kb.example.com") -> HTMLResponse:
    """SSO 失败页：提示先从知识库门户进入。"""
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="referrer" content="no-referrer">
<title>无法进入绘图平台</title>
</head>
<body style="font-family:system-ui,-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;display:flex;align-items:center;justify-content:center;min-height:90vh;margin:0;background:#f7f9fc">
<div style="text-align:center;padding:40px;background:#fff;border-radius:16px;box-shadow:0 8px 30px rgba(15,23,42,.08)">
  <h2 style="margin:0 0 12px;color:#0f172a">{msg}</h2>
  <p style="color:#64748b;margin:0 0 20px">账号与知识库互通，请先登录知识库门户。</p>
  <a href="{portal_url}" target="_blank" rel="noopener"
     style="display:inline-block;padding:10px 22px;border-radius:10px;background:#2563eb;color:#fff;text-decoration:none;font-weight:600">前往知识库门户</a>
</div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=401)


async def _sso_authenticate(token: str, db: AsyncSession):
    """校验 kgqa token 并 find-or-create 本地用户。

    返回 (user, None) 或 (None, 错误消息)。/sso(浏览器 HTML)与
    /sso-token(kgqa 服务端换 token)共用这段逻辑,保证账号同步口径一致。
    """
    settings = get_settings()
    kgqa_base = (settings.KGQA_BASE_URL or "").strip().rstrip("/")
    if not kgqa_base:
        return None, "SSO 未配置，请联系管理员"

    kgqa_user = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{kgqa_base}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                kgqa_user = resp.json()
    except Exception:
        kgqa_user = None

    if not kgqa_user or kgqa_user.get("status") != "active":
        return None, "登录已失效，请从知识库门户重新进入"

    username = (kgqa_user.get("username") or "").strip()
    if not username:
        return None, "知识库账号异常，无法登录"

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            username=username,
            email=kgqa_user.get("email") or None,
            hashed_password=await asyncio.to_thread(hash_password, secrets.token_urlsafe(32)),
            role=kgqa_user.get("role", "user"),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        if kgqa_user.get("role") in ("admin", "user"):
            user.role = kgqa_user["role"]
        user.is_active = True
        await db.commit()
        await db.refresh(user)
    return user, None


@router.post("/sso")
async def sso(
    token: str = Form(...),
    redirect: str = Form("/templates"),
    db: AsyncSession = Depends(get_db),
):
    """知识库门户跳转登录：服务端校验 kgqa token，find-or-create 本地用户，写入浏览器存储并跳转。"""
    settings = get_settings()
    kgqa_base = (settings.KGQA_BASE_URL or "").strip().rstrip("/") or "https://kb.example.com"
    user, error = await _sso_authenticate(token, db)
    if user is None:
        return _sso_html_error(error, kgqa_base)

    zt_token = create_access_token({"sub": str(user.id)})
    info = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "avatar": user.avatar,
    }
    return _sso_html_success(zt_token, info, _safe_redirect(redirect))


class SsoTokenBody(BaseModel):
    token: str


@router.post("/sso-token")
async def sso_token(body: SsoTokenBody, db: AsyncSession = Depends(get_db)):
    """kgqa 后端服务间换 token：校验 kgqa 用户 token，返回该用户在本平台的 JWT(JSON)。

    与 /sso 同一套 find-or-create 逻辑——知识库问答里触发绘图工具时,
    出图/保存图表都记在提问用户自己的账号下(账号同步,无需共享服务账号)。
    """
    user, error = await _sso_authenticate(body.token, db)
    if user is None:
        raise HTTPException(status_code=401, detail=error or "登录已失效")
    zt_token = create_access_token({"sub": str(user.id)})
    return ok({
        "token": zt_token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    })
