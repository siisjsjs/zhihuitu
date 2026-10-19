import base64
import io
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.chart import ChartRecord

router = APIRouter()


class ExportPdfBody(BaseModel):
    chartId: int


def _build_pdf(img_bytes: bytes) -> io.BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Image as RLImage

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    img_buf = io.BytesIO(img_bytes)
    img = RLImage(img_buf, width=500, height=350)
    doc.build([img])
    buf.seek(0)
    return buf


@router.post("/pdf")
async def export_pdf(body: ExportPdfBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(select(ChartRecord).where(ChartRecord.id == body.chartId, ChartRecord.user_id == user.id))
    chart = res.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")

    chart_data = chart.chart_data or {}
    image_b64 = chart_data.get("image_base64", "")
    if not image_b64:
        raise HTTPException(status_code=400, detail="该图表无图片数据")

    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    img_bytes = base64.b64decode(image_b64)

    buf = await asyncio.to_thread(_build_pdf, img_bytes)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=chart_{body.chartId}.pdf"})
