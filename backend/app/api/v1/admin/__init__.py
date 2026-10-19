from fastapi import APIRouter
from app.api.v1.admin import dashboard, users, templates, feedback, system, operation_logs

router = APIRouter()
router.include_router(dashboard.router, prefix="/dashboard", tags=["admin-dashboard"])
router.include_router(users.router, prefix="/users", tags=["admin-users"])
router.include_router(templates.router, prefix="/templates", tags=["admin-templates"])
router.include_router(feedback.router, prefix="/feedback", tags=["admin-feedback"])
router.include_router(system.router, tags=["admin-system"])
router.include_router(operation_logs.router, prefix="/operation-logs", tags=["admin-operation-logs"])
