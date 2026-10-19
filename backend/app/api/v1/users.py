import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.api.deps import get_current_user
from app.models.user import User
from app.api.response import ok

router = APIRouter()


class UpdateUserBody(BaseModel):
    username: str | None = None
    avatar: str | None = None


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return ok({"id": user.id, "username": user.username, "email": user.email, "role": user.role, "avatar": user.avatar, "createdAt": user.created_at})


@router.put("/me")
async def update_me(body: UpdateUserBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    if body.username:
        user.username = body.username
    if body.avatar:
        user.avatar = body.avatar
    await db.commit()
    return ok({"id": user.id, "username": user.username, "email": user.email, "role": user.role, "avatar": user.avatar})


class ChangePasswordBody(BaseModel):
    oldPassword: str
    newPassword: str


@router.put("/me/password")
async def change_password(body: ChangePasswordBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    password_ok = await asyncio.to_thread(verify_password, body.oldPassword, user.hashed_password)
    if not password_ok:
        raise HTTPException(status_code=400, detail="旧密码错误")
    if len(body.newPassword) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")
    user.hashed_password = await asyncio.to_thread(hash_password, body.newPassword)
    await db.commit()
    return ok({"message": "密码已更新"})
