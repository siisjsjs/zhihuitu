from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import engine, AsyncSessionLocal, Base
from app.core.paths import ANNOUNCEMENT_UPLOAD_DIR, LB_UPLOAD_DIR, LB_SOP_DIR, LB_VIDEO_DIR
from app.core.security import hash_password
from app.models.user import User
from app.services.template_registry import sync_templates
from app.utils.db_migrate import migrate_announcement_columns, migrate_lb_columns

settings = get_settings()
ANNOUNCEMENT_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LB_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LB_SOP_DIR.mkdir(parents=True, exist_ok=True)
LB_VIDEO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="智绘图 API", version="1.0.0")

app.mount(
    "/static/announcements",
    StaticFiles(directory=str(ANNOUNCEMENT_UPLOAD_DIR)),
    name="announcement_uploads",
)

app.mount(
    "/static/lb",
    StaticFiles(directory=str(LB_UPLOAD_DIR)),
    name="lb_uploads",
)

app.mount(
    "/static/sop",
    StaticFiles(directory=str(LB_SOP_DIR)),
    name="sop_docs",
)

app.mount(
    "/static/lbvideo",
    StaticFiles(directory=str(LB_VIDEO_DIR)),
    name="lb_video",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _ensure_bootstrap_user() -> None:
    name = (settings.BOOTSTRAP_USER_USERNAME or "").strip()
    password = settings.BOOTSTRAP_USER_PASSWORD or ""
    if not name or not password:
        return
    role = settings.BOOTSTRAP_USER_ROLE if settings.BOOTSTRAP_USER_ROLE in ("admin", "user") else "admin"
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.username == name))
        if existing.scalar_one_or_none():
            return
        user = User(
            username=name,
            email=f"{name}@bootstrap.local",
            hashed_password=await asyncio.to_thread(hash_password, password),
            role=role,
            is_active=True,
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError:
            # 多 worker 同时启动时可能并发创建同一个引导账号；已有一个成功即可。
            await db.rollback()


@app.on_event("startup")
async def startup():
    if settings.BACKEND_AUTO_CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(migrate_announcement_columns)
            await conn.run_sync(migrate_lb_columns)
        await _ensure_bootstrap_user()
    if settings.BACKEND_SYNC_TEMPLATES_ON_STARTUP:
        async with AsyncSessionLocal() as db:
            await sync_templates(db)


from app.api.v1 import router as v1_router
app.include_router(v1_router, prefix="/api/v1")
