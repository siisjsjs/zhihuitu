import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import get_db
from app.models.template import Template
from app.api.response import ok

router = APIRouter()

_TEMPLATE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@router.get("")
async def list_templates(category: str = "", keyword: str = "", db: AsyncSession = Depends(get_db)):
    q = select(Template).where(Template.status == "published")
    if category:
        q = q.where(Template.category == category)
    if keyword:
        q = q.where(Template.name.contains(keyword))
    res = await db.execute(q.order_by(Template.sort_order))
    templates = res.scalars().all()
    return ok([{
        "id": t.id, "name": t.name, "engine": t.engine, "category": t.category,
        "description": t.description, "tags": t.tags, "status": t.status,
        "sortOrder": t.sort_order, "thumbnail": None,
        "config": {k: v for k, v in (t.config or {}).items() if k != "promptContent"}
    } for t in templates])


@router.get("/{template_id}/preview")
async def template_preview(template_id: str):
    """公开缩略图接口(kgqa 问答模板推荐卡热链用,无需 token)。

    kgqa 侧不存任何缩略图:新模板照常走 sync_templates 上架
    (模板目录含 preview.png),kgqa 的推荐卡缩略图自动出现。
    """
    # 白名单校验防路径穿越(id 只允许字母数字下划线连字符)
    if not _TEMPLATE_ID_RE.fullmatch(template_id):
        raise HTTPException(status_code=404, detail="模板不存在")
    path = Path(get_settings().CHART_TEMPLATES_DIR).resolve() / template_id / "preview.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="缩略图不存在")
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/{template_id}")
async def get_template(template_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Template).where(Template.id == template_id))
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    config = t.config or {}
    return ok({
        "id": t.id, "name": t.name, "engine": t.engine, "category": t.category,
        "description": t.description, "tags": t.tags, "status": t.status,
        "sortOrder": t.sort_order, "config": {k: v for k, v in config.items() if k != "promptContent"},
        "promptContent": config.get("promptContent", "")
    })
