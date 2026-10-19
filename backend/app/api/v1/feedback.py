from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.feedback import Feedback
from app.api.response import ok

router = APIRouter()


class FeedbackBody(BaseModel):
    title: str
    content: str


@router.post("")
async def submit_feedback(body: FeedbackBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    fb = Feedback(user_id=user.id, title=body.title, content=body.content)
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return ok({"id": fb.id})


@router.get("")
async def list_feedback(page: int = 1, pageSize: int = 10, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Feedback).where(Feedback.user_id == user.id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    res = await db.execute(q.offset((page - 1) * pageSize).limit(pageSize).order_by(Feedback.created_at.desc()))
    items = res.scalars().all()
    return ok({"list": [{"id": f.id, "title": f.title, "content": f.content, "status": f.status, "adminReply": f.admin_reply, "createdAt": f.created_at} for f in items], "total": total, "page": page, "pageSize": pageSize})
