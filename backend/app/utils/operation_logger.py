from sqlalchemy.ext.asyncio import AsyncSession
from app.models.operation_log import OperationLog


async def log_operation(db: AsyncSession, admin_id: int, action: str, target_type: str | None = None, target_id: str | None = None, detail: dict | None = None, ip_address: str | None = None):
    db.add(OperationLog(admin_id=admin_id, action=action, target_type=target_type, target_id=str(target_id) if target_id else None, detail=detail, ip_address=ip_address))
