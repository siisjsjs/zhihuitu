from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Any
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.chart import ChartRecord
from app.models.template import Template
from app.api.response import ok
from app.services.chart_generator import generate_chart
from app.services.excel_export import build_chart_excel

router = APIRouter()


class SaveChartBody(BaseModel):
    title: str
    templateId: str
    chartData: Any = None


class UpdateChartBody(BaseModel):
    title: str | None = None
    chartData: Any = None


class GenerateBody(BaseModel):
    templateId: str
    params: dict


@router.post("/generate")
async def generate(body: GenerateBody, user: User = Depends(get_current_user)):
    try:
        result = await generate_chart(body.templateId, body.params)
        return ok(result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图表生成失败: {str(e)}")


@router.post("")
async def save_chart(body: SaveChartBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(select(Template).where(Template.id == body.templateId))
    tpl = res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    chart = ChartRecord(user_id=user.id, title=body.title, template_id=body.templateId, engine=tpl.engine, chart_data=body.chartData)
    db.add(chart)
    await db.commit()
    await db.refresh(chart)
    return ok({"id": chart.id, "title": chart.title, "createdAt": chart.created_at})


@router.get("")
async def list_charts(page: int = 1, pageSize: int = 10, keyword: str = "", templateId: str = "", db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(ChartRecord).where(ChartRecord.user_id == user.id)
    if keyword:
        q = q.where(ChartRecord.title.contains(keyword))
    if templateId:
        q = q.where(ChartRecord.template_id == templateId)
    total_res = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_res.scalar()
    res = await db.execute(q.offset((page - 1) * pageSize).limit(pageSize).order_by(ChartRecord.created_at.desc()))
    charts = res.scalars().all()
    return ok({
        "list": [
            {
                "id": c.id,
                "title": c.title,
                "templateId": c.template_id,
                "engine": c.engine,
                "thumbnail": c.thumbnail,
                "createdAt": c.created_at,
                "updatedAt": c.updated_at,
            }
            for c in charts
        ],
        "total": total,
        "page": page,
        "pageSize": pageSize,
    })


@router.get("/{chart_id}")
async def get_chart(chart_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(select(ChartRecord).where(ChartRecord.id == chart_id, ChartRecord.user_id == user.id))
    chart = res.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    return ok({"id": chart.id, "title": chart.title, "templateId": chart.template_id, "engine": chart.engine, "chartData": chart.chart_data, "createdAt": chart.created_at, "updatedAt": chart.updated_at})


@router.get("/{chart_id}/export-excel")
async def export_chart_excel(chart_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """服务端生成与编辑器「导出 Excel」同款的工作簿,直接下载不经浏览器组件。"""
    res = await db.execute(select(ChartRecord).where(ChartRecord.id == chart_id, ChartRecord.user_id == user.id))
    chart = res.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    try:
        content, filename = build_chart_excel(chart.template_id, chart.chart_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Excel 导出失败: {str(e)}")
    quoted = quote(filename)
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
    )


@router.put("/{chart_id}")
async def update_chart(chart_id: int, body: UpdateChartBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(select(ChartRecord).where(ChartRecord.id == chart_id, ChartRecord.user_id == user.id))
    chart = res.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    if body.title is not None:
        chart.title = body.title
    if body.chartData is not None:
        chart.chart_data = body.chartData
    await db.commit()
    await db.refresh(chart)
    return ok({"id": chart.id, "updatedAt": chart.updated_at})


@router.delete("/{chart_id}")
async def delete_chart(chart_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(select(ChartRecord).where(ChartRecord.id == chart_id, ChartRecord.user_id == user.id))
    chart = res.scalar_one_or_none()
    if not chart:
        raise HTTPException(status_code=404, detail="图表不存在")
    await db.delete(chart)
    await db.commit()
    return ok(message="已删除")
