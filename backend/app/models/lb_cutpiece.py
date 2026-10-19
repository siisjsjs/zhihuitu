"""产线平衡工作台 — 物料/裁片与工位-物料关联模型（装配 BOM 语义）。

业务规则（已从“裁片排他”改为“装配 BOM 复用”）：
- 物料（材料编号/名称/规格/材质）是 SOP 的数据源，code 款内唯一。
- 标准件（螺母/螺栓等）可被多个工位复用，每次关联带数量，不再排他。
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LbCutPiece(Base):
    """物料/裁片：SOP 数据源，导入 JSON / Excel，piece_code 款内唯一。

    兼容旧裁片字段（shape/fabric/area_cm2/size_mm），新增装配 BOM 字段
    material（材质）/ spec（规格）；material_code/name 复用 piece_code/piece_name。
    """

    __tablename__ = "lb_cut_pieces"

    id: Mapped[int] = mapped_column(primary_key=True)
    style_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_styles.id"), index=True)
    piece_code: Mapped[str] = mapped_column(String(50))  # 材料编号，款内唯一
    piece_name: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 材料名称
    spec: Mapped[str | None] = mapped_column(String(200), nullable=True)      # 材料规格
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 材质（金属/塑料…）
    # —— 兼容旧裁片字段 ——
    shape: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fabric: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area_cm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    size_mm: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ref_image: Mapped[str | None] = mapped_column(String(500), nullable=True)  # LD-xxxx.jpg
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("style_id", "piece_code", name="uq_lb_cutpiece_style_code"),
    )


class LbProcessCutPiece(Base):
    """工位-物料关联（装配 BOM，可复用）：一个物料可被多个工位消耗，每条带数量。"""

    __tablename__ = "lb_process_cut_pieces"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_balance_plans.id"), index=True)
    station_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_stations.id"), index=True)
    cut_piece_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_cut_pieces.id"))
    quantity: Mapped[float] = mapped_column(Float, default=1)  # 本工位消耗数量
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        # 同一工位内同一物料只登记一行（避免重复绑定），但允许跨工位复用。
        UniqueConstraint("station_id", "cut_piece_id", name="uq_lb_pcp_station_piece"),
        Index("ix_lb_pcp_plan", "plan_id"),
    )


class LbProcessMaterial(Base):
    """工序-物料关联（装配 BOM，可复用）：物料直接绑到工序上。

    这是新的绑定单位（早期绑在工位上，但工位只有优化生成方案后才存在）。
    工序变化时物料随之变化；优化合并工序成工位后，工位物料由其包含工序聚合而来，
    最终汇入 SOP。一个物料可被多个工序消耗，每条带数量。
    """

    __tablename__ = "lb_process_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    process_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_processes.id"), index=True)
    cut_piece_id: Mapped[int] = mapped_column(Integer, ForeignKey("lb_cut_pieces.id"))
    quantity: Mapped[float] = mapped_column(Float, default=1)  # 本工序消耗数量
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("process_id", "cut_piece_id", name="uq_lb_pm_process_piece"),
    )
