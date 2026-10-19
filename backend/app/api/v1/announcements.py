import hashlib
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.system_config import Announcement
from app.api.response import ok

router = APIRouter()


def _announcement_version(ann: Announcement) -> str:
    img = (ann.image_url or "").strip()
    raw = f"{ann.id}|{ann.title}|{ann.content}|{int(bool(ann.is_highlight))}|{img}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


@router.get("/announcements/current")
async def get_current_announcement(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Announcement)
        .where(Announcement.is_active.is_(True))
        .order_by(Announcement.id.desc())
        .limit(1)
    )
    ann = res.scalar_one_or_none()
    title_ok = (ann.title or "").strip() if ann else ""
    content_ok = (ann.content or "").strip() if ann else ""
    image_ok = (ann.image_url or "").strip() if ann else ""
    if not ann or (not title_ok and not content_ok and not image_ok):
        return ok(None)
    return ok(
        {
            "id": ann.id,
            "title": ann.title,
            "content": ann.content,
            "isHighlight": bool(ann.is_highlight),
            "imageUrl": image_ok or None,
            "version": _announcement_version(ann),
        }
    )
