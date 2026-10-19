"""产线平衡工作台 Pydantic 请求/响应模型（前端字段走 camelCase）。"""
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class LbBase(BaseModel):
    """统一：入参/出参字段对外 camelCase，内部 snake_case。"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# —— 款式 ——
class StyleCreate(LbBase):
    style_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    total_workers: int | None = None
    takt_time: float | None = None
    hourly_output: float | None = None


class StyleUpdate(LbBase):
    name: str | None = None
    total_workers: int | None = None
    takt_time: float | None = None
    hourly_output: float | None = None


class StyleOut(LbBase):
    id: int
    style_code: str
    name: str
    total_workers: int | None = None
    takt_time: float | None = None
    hourly_output: float | None = None


# —— 工序 ——
class ProcessIn(LbBase):
    original_code: str = Field(min_length=1, max_length=50)
    original_upstream: str | None = None
    process_name: str = Field(min_length=1, max_length=200)
    # 实测/系数：标准工时由三者派生 sam = actual_time × rating_factor × (1 + relax_rate)
    actual_time: float | None = Field(default=None, ge=0)
    relax_rate: float = Field(default=0.0, ge=0)       # 放宽率(0~1，如 0.13 表示 13%)
    rating_factor: float = Field(default=1.0, gt=0)    # 评定系数(如 1.0)
    # 标准工时：可直接传（向后兼容/无实测时），留空则由上面三者算出
    sam: float | None = Field(default=None, gt=0)
    machine_type: str | None = None
    worker_machine: str | None = None
    can_merge: bool = True
    can_add: bool = True

    def computed_sam(self) -> float:
        """标准工时：优先用实测×系数派生；无实测时回退到直接传入的 sam。"""
        if self.actual_time is not None:
            return round(self.actual_time * self.rating_factor * (1 + self.relax_rate), 2)
        if self.sam is not None:
            return self.sam
        return 0.0


class ProcessOut(LbBase):
    id: int
    original_code: str
    original_upstream: str | None = None
    process_name: str
    actual_time: float | None = None
    relax_rate: float = 0.0
    rating_factor: float = 1.0
    sam: float
    machine_type: str | None = None
    worker_machine: str | None = None
    gen_code: str | None = None
    gen_upstream: str | None = None
    segment_reason: str | None = None
    load: float | None = None
    load_ratio: float | None = None
    is_bottleneck: bool = False
    can_merge: bool = True
    can_add: bool = True
    two_hand_data: dict | None = None


class ProcessBulkIn(LbBase):
    """批量录入/Excel 粘贴：整表替换或追加由 replace 控制。"""
    processes: list[ProcessIn]
    replace: bool = False


# —— 平衡寻优 ——
class OptimizeIn(LbBase):
    """自动寻优：不再要求用户填目标产量/工时。

    target_output/work_hours 留空时后端自动取「瓶颈节拍」为目标，最大化合并。
    """
    target_output: float | None = Field(default=None, gt=0)  # 目标每班产能(件)，留空自动
    work_hours: float | None = Field(default=None, gt=0)      # 每班工时(小时)，留空默认 8h
    add_people_fix: bool = False        # 加人预处理语义开关（见 optimize_line）
    use_confirmed_codes: bool = False   # 自动寻优不强制已确认编码


class PlanSaveIn(LbBase):
    """保存方案快照：name 不传则自动按 款号_人数_节拍_平衡率 生成。"""
    task_id: str
    name: str | None = None


class PlanOut(LbBase):
    id: int
    name: str
    worker_count: int | None = None
    takt: float | None = None
    balance_rate: float | None = None
    total_work_time: float | None = None
    timeout_reached: bool = False
    is_selected: bool = False
    params: dict | None = None


# —— 物料 / BOM（F5，装配语义）——
class CutPieceIn(LbBase):
    piece_code: str = Field(min_length=1, max_length=50)   # 材料编号
    piece_name: str | None = None                          # 材料名称
    spec: str | None = None                                # 材料规格
    material: str | None = None                            # 材质（金属/塑料…）
    shape: str | None = None
    fabric: str | None = None
    area_cm2: float | None = None
    size_mm: str | None = None
    ref_image: str | None = None


class CutPieceImportIn(LbBase):
    """数据交换导入：整批物料 JSON。replace=True 时先清空本款物料。"""
    pieces: list[CutPieceIn]
    replace: bool = False


class CutPieceOut(LbBase):
    id: int
    piece_code: str
    piece_name: str | None = None
    spec: str | None = None
    material: str | None = None
    shape: str | None = None
    fabric: str | None = None
    area_cm2: float | None = None
    size_mm: str | None = None
    ref_image: str | None = None
    used: bool = False        # 是否已被任一工位关联（仅作提示，非排他）
    quantity: float | None = None  # 在当前查询工位上下文中的关联数量


class StationCutPieceItem(LbBase):
    """工位-物料关联条目：物料 id + 本工位消耗数量。"""
    cut_piece_id: int
    quantity: float = Field(default=1, gt=0)


class StationCutPieceIn(LbBase):
    """工位-物料关联（整体覆盖本工位）。

    兼容两种入参：items=[{cutPieceId,quantity}]（推荐，带数量），
    或旧版 cutPieceIds=[id...]（数量默认 1）。
    """
    items: list[StationCutPieceItem] | None = None
    cut_piece_ids: list[int] | None = None

    def normalized(self) -> list[StationCutPieceItem]:
        if self.items:
            return self.items
        if self.cut_piece_ids:
            return [StationCutPieceItem(cut_piece_id=i, quantity=1) for i in self.cut_piece_ids]
        return []


# —— 工序-物料关联（新：绑定单位为工序，优化后由工位聚合）——
class ProcessMaterialItem(LbBase):
    """工序-物料关联条目：物料 id + 本工序消耗数量。"""
    cut_piece_id: int
    quantity: float = Field(default=1, gt=0)


class ProcessMaterialIn(LbBase):
    """工序-物料关联（整体覆盖本工序绑定）。"""
    items: list[ProcessMaterialItem] | None = None
    cut_piece_ids: list[int] | None = None

    def normalized(self) -> list[ProcessMaterialItem]:
        if self.items:
            return self.items
        if self.cut_piece_ids:
            return [ProcessMaterialItem(cut_piece_id=i, quantity=1) for i in self.cut_piece_ids]
        return []


# —— 工序双手作业分析数据（TwoHandChart 快照）——
class TwoHandDataIn(LbBase):
    data: dict | None = None


# —— 工位信息补录（F6 / 装配 SOP）——
class EquipmentItem(LbBase):
    name: str | None = None
    model: str | None = None
    condition: str | None = None


class StationInfoIn(LbBase):
    # 工位人数（流程优化不再填，移到 SOP 阶段由用户补录）
    worker_count: int | None = None
    # 合并工序名（累加），用户可在树状图/SOP 直接编辑
    process_detail: list[str] | None = None
    # 旧 5 段（保留兼容）
    work_steps: str | None = None
    tools: str | None = None
    process_req: str | None = None
    quality_req: str | None = None
    ref_images: list[str] | None = None
    # 装配 SOP 段
    process_seq: int | None = None
    work_type: str | None = None
    check_steps: str | None = None
    main_steps: str | None = None
    notes: str | None = None
    self_check: str | None = None
    tech_req: str | None = None
    equipment: list[EquipmentItem] | None = None
    approver: str | None = None
    reviewer: str | None = None
    department: str | None = None
    owner_name: str | None = None
    file_no: str | None = None
    version: str | None = None


class StationOut(LbBase):
    id: int
    station_code: str
    worker_count: int
    station_takt: float | None = None
    upstream_station: str | None = None
    downstream_station: str | None = None
    process_detail: list | None = None
    work_steps: str | None = None
    tools: str | None = None
    process_req: str | None = None
    quality_req: str | None = None
    ref_images: list | None = None
    process_seq: int | None = None
    work_type: str | None = None
    check_steps: str | None = None
    main_steps: str | None = None
    notes: str | None = None
    self_check: str | None = None
    tech_req: str | None = None
    equipment: list | None = None
    approver: str | None = None
    reviewer: str | None = None
    department: str | None = None
    owner_name: str | None = None
    file_no: str | None = None
    version: str | None = None


# —— SOP 批量生成（F6 / M7）——
class SopBatchIn(LbBase):
    """批量生成：默认整方案全部工位；可传 station_ids 子集。fmt=html|pdf|xlsx。"""
    station_ids: list[int] | None = None
    fmt: str = "xlsx"


# —— 视频分析切片（工序录入第二入口）——
class VideoClipIn(LbBase):
    """对已上传视频按时间区间切片，start/end 单位秒。filename 为上传返回的文件名。"""
    filename: str = Field(min_length=1, max_length=200)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
