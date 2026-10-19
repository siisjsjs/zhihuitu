from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.feedback import Feedback
from app.api.response import ok
from app.utils.operation_logger import log_operation

router = APIRouter()


class ReplyBody(BaseModel):
    reply: str


class StatusBody(BaseModel):
    status: str


@router.get("")
async def list_feedback(page: int = 1, pageSize: int = 10, status: str = "", db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    q = select(Feedback)
    if status:
        q = q.where(Feedback.status == status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    res = await db.execute(q.offset((page - 1) * pageSize).limit(pageSize).order_by(Feedback.created_at.desc()))
    items = res.scalars().all()
    return ok({"list": [{"id": f.id, "userId": f.user_id, "title": f.title, "content": f.content, "status": f.status, "adminReply": f.admin_reply, "createdAt": f.created_at} for f in items], "total": total, "page": page, "pageSize": pageSize})


@router.post("/{feedback_id}/reply")
async def reply_feedback(feedback_id: int, body: ReplyBody, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    fb = res.scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="反馈不存在")
    fb.admin_reply = body.reply
    fb.replied_at = datetime.utcnow()
    fb.status = "replied"
    await log_operation(db, admin.id, "回复反馈", "feedback", str(feedback_id), ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok()


@router.post("/{feedback_id}/status")
async def update_status(feedback_id: int, body: StatusBody, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    fb = res.scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="反馈不存在")
    fb.status = body.status
    await log_operation(db, admin.id, "更新反馈状态", "feedback", str(feedback_id), detail={"status": body.status}, ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok()
