from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.chart import ChartRecord
from app.api.response import ok
from app.utils.operation_logger import log_operation

router = APIRouter()


@router.get("")
async def list_users(page: int = 1, pageSize: int = 10, keyword: str = "", db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    q = select(User)
    if keyword:
        q = q.where(User.username.contains(keyword) | User.email.contains(keyword))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    res = await db.execute(q.order_by(User.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize))
    users = res.scalars().all()

    user_ids = [u.id for u in users]
    agg: dict[int, tuple[int, datetime | None]] = {}
    if user_ids:
        agg_res = await db.execute(
            select(
                ChartRecord.user_id,
                func.count().label("cnt"),
                func.max(ChartRecord.created_at).label("last"),
            )
            .where(ChartRecord.user_id.in_(user_ids))
            .group_by(ChartRecord.user_id)
        )
        agg = {r.user_id: (r.cnt, r.last) for r in agg_res.all()}

    return ok({
        "list": [{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "status": "active" if u.is_active else "banned",
            "chartsCount": agg.get(u.id, (0, None))[0],
            "lastActive": agg.get(u.id, (0, None))[1],
            "createdAt": u.created_at,
        } for u in users],
        "total": total, "page": page, "pageSize": pageSize,
    })


@router.get("/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    charts_count = (await db.execute(select(func.count()).select_from(ChartRecord).where(ChartRecord.user_id == user_id))).scalar()
    last_active = (await db.execute(select(func.max(ChartRecord.created_at)).where(ChartRecord.user_id == user_id))).scalar()
    return ok({"id": u.id, "username": u.username, "email": u.email, "role": u.role, "status": "active" if u.is_active else "banned", "chartsCount": charts_count, "lastActive": last_active, "createdAt": u.created_at})


@router.post("/{user_id}/ban")
async def ban_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.is_active = False
    await log_operation(db, admin.id, "封禁用户", "user", str(user_id), ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok(message="用户已封禁")


@router.post("/{user_id}/unban")
async def unban_user(user_id: int, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(User).where(User.id == user_id))
    u = res.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.is_active = True
    await log_operation(db, admin.id, "解封用户", "user", str(user_id), ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok(message="用户已解封")
