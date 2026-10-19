from fastapi import APIRouter
from app.api.v1 import auth, charts, templates, ai_chat, export, feedback, users, announcements, line_balance
from app.api.v1.admin import router as admin_router

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(charts.router, prefix="/charts", tags=["charts"])
router.include_router(templates.router, prefix="/templates", tags=["templates"])
router.include_router(ai_chat.router, prefix="/ai", tags=["ai"])
router.include_router(export.router, prefix="/export", tags=["export"])
router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(announcements.router, tags=["announcements"])
router.include_router(line_balance.router, prefix="/lb", tags=["line-balance"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])
