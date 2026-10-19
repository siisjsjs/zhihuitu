from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.operation_log import OperationLog
from app.api.response import ok

router = APIRouter()


@router.get("")
async def list_operation_logs(page: int = 1, pageSize: int = 20, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    total = (await db.execute(select(func.count()).select_from(OperationLog))).scalar()
    res = await db.execute(select(OperationLog).order_by(OperationLog.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize))
    logs = res.scalars().all()
    return ok({
        "list": [{"id": l.id, "adminId": l.admin_id, "action": l.action, "targetType": l.target_type, "targetId": l.target_id, "detail": l.detail, "ipAddress": l.ip_address, "createdAt": l.created_at} for l in logs],
        "total": total,
    })
