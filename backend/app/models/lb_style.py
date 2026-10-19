"""产线平衡工作台 — 款式领域模型（计划书 §F1 Style）。"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LbStyle(Base):
    """款式：一条产线方案的顶层归属对象，按 owner 隔离。"""

    __tablename__ = "lb_styles"

    id: Mapped[int] = mapped_column(primary_key=True)
    style_code: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(200))
    total_workers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    takt_time: Mapped[float | None] = mapped_column(Float, nullable=True)  # 目标节拍(s)
    hourly_output: Mapped[float | None] = mapped_column(Float, nullable=True)  # 每小时产量(件)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("owner_id", "style_code", name="uq_lb_style_owner_code"),
        Index("ix_lb_styles_owner_code", "owner_id", "style_code"),
    )
