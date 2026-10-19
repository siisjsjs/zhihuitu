from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Any
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.template import Template
from app.models.chart import ChartRecord
from app.api.response import ok
from app.utils.operation_logger import log_operation

router = APIRouter()


class TemplateBody(BaseModel):
    name: str
    engine: str
    category: str
    description: str = ""
    config: Any = None


class UpdateTemplateBody(BaseModel):
    name: str | None = None
    category: str | None = None
    config: Any = None


class SortBody(BaseModel):
    ids: list[str]


@router.get("")
async def list_templates(page: int = 1, pageSize: int = 10, keyword: str = "", category: str = "", db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    q = select(Template)
    if keyword:
        q = q.where(Template.name.contains(keyword))
    if category:
        q = q.where(Template.category == category)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    res = await db.execute(q.offset((page - 1) * pageSize).limit(pageSize).order_by(Template.sort_order))
    items = res.scalars().all()

    ids = [t.id for t in items]
    uses: dict[str, int] = {}
    if ids:
        uses_res = await db.execute(
            select(ChartRecord.template_id, func.count())
            .where(ChartRecord.template_id.in_(ids))
            .group_by(ChartRecord.template_id)
        )
        uses = {tid: cnt for tid, cnt in uses_res.all()}

    total_uses = (await db.execute(select(func.count()).select_from(ChartRecord))).scalar()

    return ok({
        "list": [{
            "id": t.id, "name": t.name, "engine": t.engine, "category": t.category,
            "description": t.description, "status": t.status,
            "usesCount": uses.get(t.id, 0),
            "createdAt": t.created_at,
        } for t in items],
        "total": total, "totalUses": total_uses, "page": page, "pageSize": pageSize,
    })


@router.post("")
async def create_template(body: TemplateBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    import uuid
    t = Template(id=str(uuid.uuid4())[:8], name=body.name, engine=body.engine, category=body.category, description=body.description, config=body.config)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return ok({"id": t.id})


@router.put("/{template_id}")
async def update_template(template_id: str, body: UpdateTemplateBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(Template).where(Template.id == template_id))
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if body.name is not None:
        t.name = body.name
    if body.category is not None:
        t.category = body.category
    if body.config is not None:
        t.config = body.config
    await db.commit()
    return ok({"id": t.id})


@router.delete("/{template_id}")
async def delete_template(template_id: str, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(Template).where(Template.id == template_id))
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.delete(t)
    await log_operation(db, admin.id, "删除模板", "template", template_id, ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok(message="已删除")


@router.post("/{template_id}/publish")
async def publish(template_id: str, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(Template).where(Template.id == template_id))
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    t.status = "published"
    await log_operation(db, admin.id, "上架模板", "template", template_id, ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok()


@router.post("/{template_id}/unpublish")
async def unpublish(template_id: str, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(Template).where(Template.id == template_id))
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    t.status = "draft"
    await log_operation(db, admin.id, "下架模板", "template", template_id, ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok()


@router.put("/sort")
async def sort_templates(body: SortBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    for i, tid in enumerate(body.ids):
        res = await db.execute(select(Template).where(Template.id == tid))
        t = res.scalar_one_or_none()
        if t:
            t.sort_order = i
    await db.commit()
    return ok()
