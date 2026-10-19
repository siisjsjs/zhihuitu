"""产线平衡工作台 — 工位模型（计划书 §F1 Station）。

一个工位 = 平衡寻优后的一组工序合并结果，是 SOP 文档的拼装单位。
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, JSON, DateTime, func, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LbStation(Base):
    """工位：方案下的组合结果，含合并的工序明细与补录的 SOP 信息。"""

    __tablename__ = "lb_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_balance_plans.id"), index=True)
    station_code: Mapped[str] = mapped_column(String(20))  # ST-001
    worker_count: Mapped[int] = mapped_column(Integer, default=1)  # 多人工位 1/2

    balance_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    station_takt: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_consume: Mapped[float | None] = mapped_column(Float, nullable=True)
    upstream_station: Mapped[str | None] = mapped_column(String(20), nullable=True)
    downstream_station: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 合并进本工位的工序（id 列表 + 展示用明细），快照存 JSON 便于直接渲染
    process_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    process_detail: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # —— SOP 5 段补录信息（F6，旧）——
    work_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools: Mapped[str | None] = mapped_column(Text, nullable=True)
    process_req: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_req: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_images: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # —— 装配 SOP 补录（对齐参考 SOP.xlsx）——
    process_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)        # 工序排号
    work_type: Mapped[str | None] = mapped_column(String(50), nullable=True)       # 作业类型
    check_steps: Mapped[str | None] = mapped_column(Text, nullable=True)   # 检查工序（分行）
    main_steps: Mapped[str | None] = mapped_column(Text, nullable=True)    # 本工序作业（分行）
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)         # 注意事项（分行）
    self_check: Mapped[str | None] = mapped_column(Text, nullable=True)    # 自检（分行）
    tech_req: Mapped[str | None] = mapped_column(Text, nullable=True)      # 技术要求
    equipment: Mapped[list | None] = mapped_column(JSON, nullable=True)            # 设备工装 [{name,model,condition}]
    # 审批栏 / 文档头
    approver: Mapped[str | None] = mapped_column(String(50), nullable=True)        # 核准
    reviewer: Mapped[str | None] = mapped_column(String(50), nullable=True)        # 审核
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)     # 部门
    owner_name: Mapped[str | None] = mapped_column(String(50), nullable=True)      # 负责人
    file_no: Mapped[str | None] = mapped_column(String(50), nullable=True)         # 文件编号
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)         # 版本号

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_lb_stations_plan_code", "plan_id", "station_code"),
    )
