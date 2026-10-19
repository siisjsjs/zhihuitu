from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, JSON, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ChartRecord(Base):
    __tablename__ = "chart_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    template_id: Mapped[str] = mapped_column(String(100), ForeignKey("templates.id"))
    engine: Mapped[str] = mapped_column(String(50))
    chart_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_chart_records_user_created", "user_id", "created_at"),
        Index("ix_chart_records_template", "template_id"),
    )
