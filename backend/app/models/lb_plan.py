"""产线平衡工作台 — 方案快照模型（计划书 §F1 BalancePlan / §F4）。"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, JSON, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LbBalancePlan(Base):
    """组合方案/快照：一次平衡寻优的结果集合，命名规则 款号_人数_节拍_平衡率。"""

    __tablename__ = "lb_balance_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_styles.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))  # 9800_56人_162.3s_平衡59.2%
    worker_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    takt: Mapped[float | None] = mapped_column(Float, nullable=True)
    balance_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_work_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeout_reached: Mapped[bool] = mapped_column(Boolean, default=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)  # 用户当前选用（款式内唯一）
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 算法入参快照
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_lb_plans_style_created", "style_id", "created_at"),
    )
