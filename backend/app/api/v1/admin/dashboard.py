from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, date, timezone
from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models.user import User
from app.models.chart import ChartRecord
from app.models.feedback import Feedback
from app.models.template import Template
from app.api.response import ok

router = APIRouter()


def fmt_delta(current: int, previous: int) -> str:
    if previous == 0:
        return f"+{current}" if current > 0 else "0"
    pct = round((current - previous) / previous * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    today_charts = (await db.execute(select(func.count()).select_from(ChartRecord).where(func.date(ChartRecord.created_at) == str(today)))).scalar()
    yesterday_charts = (await db.execute(select(func.count()).select_from(ChartRecord).where(func.date(ChartRecord.created_at) == str(yesterday)))).scalar()

    today_new_users = (await db.execute(select(func.count()).select_from(User).where(func.date(User.created_at) == str(today)))).scalar()
    yesterday_new_users = (await db.execute(select(func.count()).select_from(User).where(func.date(User.created_at) == str(yesterday)))).scalar()

    pending_feedback = (await db.execute(select(func.count()).select_from(Feedback).where(Feedback.status == "pending"))).scalar()

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
    active_users = (await db.execute(select(func.count(func.distinct(ChartRecord.user_id))).where(ChartRecord.created_at >= week_ago))).scalar()
    prev_active = (await db.execute(select(func.count(func.distinct(ChartRecord.user_id))).where(ChartRecord.created_at >= two_weeks_ago, ChartRecord.created_at < week_ago))).scalar()

    return ok({
        "totalUsers": total_users, "todayCharts": today_charts, "activeUsers": active_users, "pendingFeedback": pending_feedback,
        "userDelta": fmt_delta(today_new_users, yesterday_new_users),
        "chartDelta": fmt_delta(today_charts, yesterday_charts),
        "activeDelta": fmt_delta(active_users, prev_active),
        "feedbackDelta": f"+{pending_feedback}" if pending_feedback > 0 else "0",
    })


@router.get("/trends")
async def trends(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    today = datetime.utcnow().date()
    start = today - timedelta(days=6)
    res = await db.execute(
        select(func.date(ChartRecord.created_at).label("day"), func.count().label("cnt"))
        .where(func.date(ChartRecord.created_at) >= str(start))
        .group_by(func.date(ChartRecord.created_at))
    )
    counts = {str(r.day): r.cnt for r in res.all()}
    labels = []
    values = []
    for i in range(7):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%m/%d"))
        values.append(counts.get(str(d), 0))
    return ok({"labels": labels, "values": values})


@router.get("/chart-distribution")
async def chart_distribution(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(ChartRecord.template_id, func.count()).group_by(ChartRecord.template_id))
    rows = res.all()
    return ok({"labels": [r[0] for r in rows], "values": [r[1] for r in rows]})


@router.get("/hot-templates")
async def hot_templates(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    res = await db.execute(select(ChartRecord.template_id, func.count().label("cnt")).group_by(ChartRecord.template_id).order_by(func.count().desc()).limit(5))
    rows = res.all()
    return ok([{"name": r[0], "count": r[1]} for r in rows])


@router.get("/daily-activity")
async def daily_activity(days: int = 7, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    days = max(1, min(days, 30))
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days - 1)

    res = await db.execute(
        select(
            ChartRecord.id,
            ChartRecord.title,
            ChartRecord.template_id,
            ChartRecord.engine,
            ChartRecord.created_at,
            User.username,
        )
        .join(User, User.id == ChartRecord.user_id, isouter=True)
        .where(func.date(ChartRecord.created_at) >= str(start))
        .order_by(ChartRecord.created_at.desc())
    )
    rows = res.all()

    buckets: dict[str, list] = {}
    for r in rows:
        day = r.created_at.date().isoformat() if r.created_at else str(today)
        buckets.setdefault(day, []).append({
            "id": r.id,
            "title": r.title,
            "templateId": r.template_id,
            "engine": r.engine,
            "username": r.username or "已注销用户",
            "createdAt": r.created_at,
        })

    result = []
    for i in range(days):
        d = (today - timedelta(days=i)).isoformat()
        items = buckets.get(d, [])
        users = {it["username"] for it in items}
        result.append({
            "date": d,
            "total": len(items),
            "userCount": len(users),
            "items": items,
        })
    return ok(result)
