"""产线平衡工作台 — 工序领域模型（计划书 §F1 Process）。

原始码（original_code/upstream）与自动生成码（gen_code/upstream）并存：
前者由用户录入用于表达上下游关系，后者由 F2 编码引擎算出。
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, JSON, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LbProcess(Base):
    """工序：录入的原始作业单元，编码引擎与平衡寻优的输入。"""

    __tablename__ = "lb_processes"

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_styles.id"), index=True)

    # —— 原始录入字段 ——
    original_code: Mapped[str] = mapped_column(String(50))  # 原始 S 码，款内唯一，表上下游
    original_upstream: Mapped[str | None] = mapped_column(String(50), nullable=True)
    process_name: Mapped[str] = mapped_column(String(200))
    # 实测/系数（用户录入）；标准工时 sam 由三者派生：sam = actual_time × rating_factor × (1 + relax_rate)
    actual_time: Mapped[float | None] = mapped_column(Float, nullable=True)   # 实际时间(s)
    relax_rate: Mapped[float] = mapped_column(Float, default=0.0)             # 放宽率(0~1)
    rating_factor: Mapped[float] = mapped_column(Float, default=1.0)          # 评定系数
    sam: Mapped[float] = mapped_column(Float)  # 标准工时(s)，后续编码/寻优/节拍全用它
    machine_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 单/双/平/高，可组合
    worker_machine: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # —— 编码引擎产出（F2 写入）——
    gen_code: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 点分多级码 10.020.210
    gen_upstream: Mapped[str | None] = mapped_column(String(100), nullable=True)
    segment_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 瓶颈保护/支路不均/复合均衡
    load: Mapped[float | None] = mapped_column(Float, nullable=True)  # 负荷(s)
    load_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # 占比(%)
    is_bottleneck: Mapped[bool] = mapped_column(Boolean, default=False)

    # —— 平衡约束标记 ——
    can_merge: Mapped[bool] = mapped_column(Boolean, default=True)
    can_add: Mapped[bool] = mapped_column(Boolean, default=True)  # 可加人

    # —— 双手作业分析（F-流程优化方式2）：TwoHandChart 数据快照 ——
    # 形如 {headerInfo:{...}, steps:[{leftDesc,leftSymbol,rightSymbol,rightDesc}]}
    two_hand_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_lb_processes_style_code", "style_id", "original_code"),
    )
