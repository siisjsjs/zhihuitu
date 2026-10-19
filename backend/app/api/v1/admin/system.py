from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.core.paths import ANNOUNCEMENT_UPLOAD_DIR
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.system_config import SystemConfig, Announcement
from app.models.ai_config import AiConfig
from app.api.response import ok
from app.utils.operation_logger import log_operation

router = APIRouter()


# System Config
@router.get("/system-config")
async def get_system_config(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(SystemConfig))
    items = res.scalars().all()
    return ok({item.key: item.value for item in items})


@router.put("/system-config")
async def update_system_config(body: dict, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    for key, value in body.items():
        res = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        cfg = res.scalar_one_or_none()
        if cfg:
            cfg.value = value
        else:
            db.add(SystemConfig(key=key, value=value))
    await log_operation(db, admin.id, "更新系统配置", "system_config", detail={"keys": list(body.keys())}, ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok()


# AI Config
class AiConfigBody(BaseModel):
    provider: str
    apiKey: str
    baseUrl: str | None = None
    model: str


@router.get("/ai-config")
async def list_ai_config(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(AiConfig).order_by(AiConfig.sort_order))
    items = res.scalars().all()
    return ok([{"id": a.id, "provider": a.provider, "baseUrl": a.base_url, "model": a.model, "isEnabled": a.is_enabled} for a in items])


@router.post("/ai-config")
async def create_ai_config(body: AiConfigBody, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    cfg = AiConfig(provider=body.provider, api_key=body.apiKey, base_url=body.baseUrl, model=body.model)
    db.add(cfg)
    await db.flush()
    await log_operation(db, admin.id, "新增AI配置", "ai_config", str(cfg.id), ip_address=request.client.host if request.client else None)
    await db.commit()
    await db.refresh(cfg)
    return ok({"id": cfg.id})


@router.put("/ai-config/{cfg_id}")
async def update_ai_config(cfg_id: int, body: AiConfigBody, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(AiConfig).where(AiConfig.id == cfg_id))
    cfg = res.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")
    cfg.provider = body.provider
    cfg.api_key = body.apiKey
    cfg.base_url = body.baseUrl
    cfg.model = body.model
    await db.commit()
    return ok()


@router.delete("/ai-config/{cfg_id}")
async def delete_ai_config(cfg_id: int, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(AiConfig).where(AiConfig.id == cfg_id))
    cfg = res.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")
    await db.delete(cfg)
    await log_operation(db, admin.id, "删除AI配置", "ai_config", str(cfg_id), ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok()


@router.post("/ai-config/{cfg_id}/toggle")
async def toggle_ai_config(cfg_id: int, request: Request, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(AiConfig).where(AiConfig.id == cfg_id))
    cfg = res.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="配置不存在")
    cfg.is_enabled = not cfg.is_enabled
    await log_operation(db, admin.id, "切换AI配置", "ai_config", str(cfg_id), detail={"isEnabled": cfg.is_enabled}, ip_address=request.client.host if request.client else None)
    await db.commit()
    return ok()


_ANNOUNCEMENT_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_ANNOUNCEMENT_IMAGE_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}
_ANNOUNCEMENT_IMAGE_MAX = 5 * 1024 * 1024


def _norm_image_url(url: str | None) -> str | None:
    if not url:
        return None
    s = url.strip()
    return s or None


class AnnouncementBody(BaseModel):
    title: str = ""
    content: str = ""
    isActive: bool = True
    isHighlight: bool = False
    imageUrl: str | None = None


@router.get("/announcements")
async def list_announcements(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(Announcement).order_by(Announcement.id.desc()))
    items = res.scalars().all()
    return ok(
        [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "isActive": a.is_active,
                "isHighlight": a.is_highlight,
                "imageUrl": a.image_url,
                "createdAt": a.created_at.isoformat() if a.created_at else None,
            }
            for a in items
        ]
    )


@router.post("/announcements/upload-image")
async def upload_announcement_image(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin),
):
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in _ANNOUNCEMENT_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPG、PNG、GIF、WebP 图片")
    raw = await file.read()
    if len(raw) > _ANNOUNCEMENT_IMAGE_MAX:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")
    ext = _ANNOUNCEMENT_IMAGE_EXT[ct]
    name = f"{uuid.uuid4().hex}{ext}"
    path = ANNOUNCEMENT_UPLOAD_DIR / name
    path.write_bytes(raw)
    return ok({"url": f"/static/announcements/{name}"})


@router.post("/announcements")
async def create_announcement(
    body: AnnouncementBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    if body.isActive:
        await db.execute(update(Announcement).values(is_active=False))
    ann = Announcement(
        title=body.title,
        content=body.content,
        is_active=body.isActive,
        is_highlight=body.isHighlight,
        image_url=_norm_image_url(body.imageUrl),
    )
    db.add(ann)
    await db.flush()
    await log_operation(
        db,
        admin.id,
        "新增公告",
        "announcement",
        str(ann.id),
        detail={"title": body.title[:80]},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(ann)
    return ok({"id": ann.id})


@router.put("/announcements/{ann_id}")
async def update_announcement(
    ann_id: int,
    body: AnnouncementBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    res = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = res.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    if body.isActive:
        await db.execute(update(Announcement).values(is_active=False).where(Announcement.id != ann_id))
    ann.title = body.title
    ann.content = body.content
    ann.is_active = body.isActive
    ann.is_highlight = body.isHighlight
    ann.image_url = _norm_image_url(body.imageUrl)
    await log_operation(
        db,
        admin.id,
        "更新公告",
        "announcement",
        str(ann_id),
        detail={"title": body.title[:80]},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return ok()


@router.delete("/announcements/{ann_id}")
async def delete_announcement(
    ann_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    res = await db.execute(select(Announcement).where(Announcement.id == ann_id))
    ann = res.scalar_one_or_none()
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    await db.delete(ann)
    await log_operation(
        db,
        admin.id,
        "删除公告",
        "announcement",
        str(ann_id),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return ok()
