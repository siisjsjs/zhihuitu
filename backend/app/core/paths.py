from pathlib import Path
from app.core.config import get_settings

# backend/app/core/paths.py → parents[2] == backend/
BACKEND_ROOT = Path(__file__).resolve().parents[2]
settings = get_settings()

ANNOUNCEMENT_UPLOAD_DIR = (
    Path(settings.ANNOUNCEMENT_UPLOAD_DIR)
    if settings.ANNOUNCEMENT_UPLOAD_DIR
    else BACKEND_ROOT / "uploads" / "announcements"
)

# 产线平衡工作台：裁片/参考图上传目录 + SOP 文档产物目录 + 工序视频目录
LB_UPLOAD_DIR = BACKEND_ROOT / "uploads" / "line_balance"
LB_SOP_DIR = BACKEND_ROOT / "uploads" / "sop"
LB_VIDEO_DIR = BACKEND_ROOT / "uploads" / "lb_video"
