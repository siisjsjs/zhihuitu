"""产线平衡 / SOP 工作台路由（前缀 /api/v1/lb，全部走 get_current_user 鉴权）。

M1：款式 + 工序 CRUD。M2：工序自动编码（生成/校验/确认）。
后续里程碑（平衡寻优、SOP）在本模块继续扩展。
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from app.core.database import get_db
from app.api.deps import get_current_user
from app.api.response import ok
from app.models.user import User
from app.models.lb_style import LbStyle
from app.models.lb_process import LbProcess
from app.models.lb_plan import LbBalancePlan
from app.models.lb_station import LbStation
from app.models.lb_cutpiece import LbCutPiece, LbProcessCutPiece, LbProcessMaterial
from app.schemas.line_balance import (
    StyleCreate, StyleUpdate, StyleOut,
    ProcessIn, ProcessOut, ProcessBulkIn,
    OptimizeIn, PlanSaveIn, PlanOut,
    CutPieceImportIn, CutPieceOut, StationCutPieceIn,
    StationInfoIn, StationOut, SopBatchIn, VideoClipIn,
    ProcessMaterialIn, TwoHandDataIn,
)
from app.services.sop.coder import encode_processes, to_tree
from app.services.sop import doc_builder
from app.services.sop import xlsx_builder
from app.services.line_balance import optimize_line, derive_kpi
from app.services.lb_tasks import task_manager
from app.services import lb_video
from app.core.paths import LB_UPLOAD_DIR, LB_SOP_DIR, LB_VIDEO_DIR

import uuid
import datetime as _dt
from pathlib import Path

router = APIRouter()


async def _get_owned_style(style_id: int, user: User, db: AsyncSession) -> LbStyle:
    res = await db.execute(
        select(LbStyle).where(LbStyle.id == style_id, LbStyle.owner_id == user.id)
    )
    style = res.scalar_one_or_none()
    if not style:
        raise HTTPException(status_code=404, detail="款式不存在")
    return style


def _style_dict(s: LbStyle) -> dict:
    return StyleOut.model_validate(s, from_attributes=True).model_dump(by_alias=True)


def _process_dict(p: LbProcess) -> dict:
    return ProcessOut.model_validate(p, from_attributes=True).model_dump(by_alias=True)


# ============ 款式 ============
@router.post("/styles")
async def create_style(body: StyleCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    dup = await db.execute(
        select(LbStyle).where(LbStyle.owner_id == user.id, LbStyle.style_code == body.style_code)
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"款号 {body.style_code} 已存在")
    style = LbStyle(
        style_code=body.style_code, name=body.name, total_workers=body.total_workers,
        takt_time=body.takt_time, hourly_output=body.hourly_output, owner_id=user.id,
    )
    db.add(style)
    await db.commit()
    await db.refresh(style)
    return ok(_style_dict(style))


@router.get("/styles")
async def list_styles(page: int = 1, pageSize: int = 20, keyword: str = "", db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(LbStyle).where(LbStyle.owner_id == user.id)
    if keyword:
        q = q.where(LbStyle.name.contains(keyword) | LbStyle.style_code.contains(keyword))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar()
    res = await db.execute(q.order_by(LbStyle.created_at.desc()).offset((page - 1) * pageSize).limit(pageSize))
    return ok({
        "list": [_style_dict(s) for s in res.scalars().all()],
        "total": total, "page": page, "pageSize": pageSize,
    })


@router.get("/styles/{style_id}")
async def get_style(style_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    return ok(_style_dict(await _get_owned_style(style_id, user, db)))


@router.put("/styles/{style_id}")
async def update_style(style_id: int, body: StyleUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    style = await _get_owned_style(style_id, user, db)
    for field in ("name", "total_workers", "takt_time", "hourly_output"):
        val = getattr(body, field)
        if val is not None:
            setattr(style, field, val)
    await db.commit()
    await db.refresh(style)
    return ok(_style_dict(style))


@router.delete("/styles/{style_id}")
async def delete_style(style_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    style = await _get_owned_style(style_id, user, db)
    # 级联删除本款全部从属数据，避免遗留孤儿方案/工位被新款（复用 id）误捡。
    plan_ids = (await db.execute(
        select(LbBalancePlan.id).where(LbBalancePlan.style_id == style.id)
    )).scalars().all()
    station_ids = []
    if plan_ids:
        station_ids = (await db.execute(
            select(LbStation.id).where(LbStation.plan_id.in_(plan_ids))
        )).scalars().all()
    # 关联表（裁片/物料绑定）先删，再删工位、方案、工序、裁片，最后删款式
    if station_ids:
        await db.execute(delete(LbProcessCutPiece).where(LbProcessCutPiece.station_id.in_(station_ids)))
    if plan_ids:
        await db.execute(delete(LbProcessCutPiece).where(LbProcessCutPiece.plan_id.in_(plan_ids)))
        await db.execute(delete(LbStation).where(LbStation.plan_id.in_(plan_ids)))
        await db.execute(delete(LbBalancePlan).where(LbBalancePlan.style_id == style.id))
    proc_ids = (await db.execute(
        select(LbProcess.id).where(LbProcess.style_id == style.id)
    )).scalars().all()
    if proc_ids:
        await db.execute(delete(LbProcessMaterial).where(LbProcessMaterial.process_id.in_(proc_ids)))
    await db.execute(delete(LbProcess).where(LbProcess.style_id == style.id))
    await db.execute(delete(LbCutPiece).where(LbCutPiece.style_id == style.id))
    await db.delete(style)
    await db.commit()
    return ok(message="已删除")


# ============ 工序 ============
@router.get("/styles/{style_id}/processes")
async def list_processes(style_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await _get_owned_style(style_id, user, db)
    res = await db.execute(
        select(LbProcess).where(LbProcess.style_id == style_id).order_by(LbProcess.id)
    )
    return ok({"list": [_process_dict(p) for p in res.scalars().all()]})


@router.post("/styles/{style_id}/processes")
async def add_processes(style_id: int, body: ProcessBulkIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """批量录入工序（Excel 粘贴 / 手动）。replace=True 时先清空本款已有工序。"""
    await _get_owned_style(style_id, user, db)
    codes = [p.original_code for p in body.processes]
    if len(codes) != len(set(codes)):
        raise HTTPException(status_code=400, detail="原始码 originalCode 在本次提交内重复")

    if body.replace:
        await db.execute(delete(LbProcess).where(LbProcess.style_id == style_id))
    else:
        existing = await db.execute(
            select(LbProcess.original_code).where(LbProcess.style_id == style_id)
        )
        exist_codes = {c for (c,) in existing.all()}
        clash = exist_codes & set(codes)
        if clash:
            raise HTTPException(status_code=400, detail=f"原始码已存在：{sorted(clash)}")

    created = []
    for p in body.processes:
        proc = LbProcess(
            style_id=style_id, original_code=p.original_code, original_upstream=p.original_upstream,
            process_name=p.process_name,
            actual_time=p.actual_time, relax_rate=p.relax_rate, rating_factor=p.rating_factor,
            sam=p.computed_sam(), machine_type=p.machine_type,
            worker_machine=p.worker_machine, can_merge=p.can_merge, can_add=p.can_add,
        )
        db.add(proc)
        created.append(proc)
    await db.commit()
    for proc in created:
        await db.refresh(proc)
    return ok({"list": [_process_dict(p) for p in created], "count": len(created)})


@router.put("/processes/{process_id}")
async def update_process(process_id: int, body: ProcessIn, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(
        select(LbProcess).join(LbStyle, LbProcess.style_id == LbStyle.id)
        .where(LbProcess.id == process_id, LbStyle.owner_id == user.id)
    )
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(status_code=404, detail="工序不存在")
    for field in ("original_code", "original_upstream", "process_name",
                  "actual_time", "relax_rate", "rating_factor",
                  "machine_type", "worker_machine", "can_merge", "can_add"):
        setattr(proc, field, getattr(body, field))
    proc.sam = body.computed_sam()
    await db.commit()
    await db.refresh(proc)
    return ok(_process_dict(proc))


@router.delete("/processes/{process_id}")
async def delete_process(process_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    res = await db.execute(
        select(LbProcess).join(LbStyle, LbProcess.style_id == LbStyle.id)
        .where(LbProcess.id == process_id, LbStyle.owner_id == user.id)
    )
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(status_code=404, detail="工序不存在")
    await db.delete(proc)
    await db.commit()
    return ok(message="已删除")


# ============ 工序自动编码（M2 / F2）============
async def _load_processes(style_id: int, db: AsyncSession) -> list[LbProcess]:
    res = await db.execute(
        select(LbProcess).where(LbProcess.style_id == style_id).order_by(LbProcess.id)
    )
    return list(res.scalars().all())


async def _owned_process(process_id: int, user: User, db: AsyncSession) -> LbProcess:
    res = await db.execute(
        select(LbProcess).join(LbStyle, LbProcess.style_id == LbStyle.id)
        .where(LbProcess.id == process_id, LbStyle.owner_id == user.id)
    )
    proc = res.scalar_one_or_none()
    if not proc:
        raise HTTPException(status_code=404, detail="工序不存在")
    return proc


def _to_encoder_input(procs: list[LbProcess]) -> list[dict]:
    return [
        {
            "original_code": p.original_code,
            "original_upstream": p.original_upstream,
            "process_name": p.process_name,
            "sam": p.sam,
            "machine_type": p.machine_type,
            "can_merge": p.can_merge,
            "can_add": p.can_add,
        }
        for p in procs
    ]


@router.post("/styles/{style_id}/encode")
async def encode_style(style_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """工艺诊断：生成点分编码 + 分段判断（不落库，供前端预览/核对）。"""
    style = await _get_owned_style(style_id, user, db)
    procs = await _load_processes(style_id, db)
    if not procs:
        # 切换到尚未录入工序的款式时会自动触发诊断，此处返回空预览而非报错。
        return ok({
            "ok": True, "errors": [], "terminal": None,
            "terminals": [], "roots": [], "processes": [],
        })
    result = encode_processes(_to_encoder_input(procs), takt=style.takt_time)
    return ok({
        "ok": result["ok"],
        "errors": result["errors"],
        "terminal": result["terminal"],
        "terminals": result.get("terminals", []),
        "roots": result["roots"],
        "processes": [
            {
                "originalCode": p["original_code"],
                "genCode": p.get("gen_code"),
                "genUpstream": p.get("gen_upstream"),
                "processName": p.get("process_name"),
                "sam": p.get("sam"),
                "load": p.get("load"),
                "loadRatio": p.get("load_ratio"),
                "isBottleneck": p.get("is_bottleneck", False),
                "segmentReason": p.get("segment_reason"),
            }
            for p in result["processes"]
        ],
    })


@router.get("/styles/{style_id}/process-tree")
async def process_tree(style_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """编码树（X6 nodes/edges）+ 单向流校验结果。每节点附带绑定物料，供流程优化页展示。"""
    style = await _get_owned_style(style_id, user, db)
    procs = await _load_processes(style_id, db)
    if not procs:
        return ok({"ok": True, "errors": [], "nodes": [], "edges": []})
    result = encode_processes(_to_encoder_input(procs), takt=style.takt_time)
    tree = to_tree(result["processes"])

    # 物料按 original_code 聚合附到节点：工序变化时物料随之在树上可见
    pm = await db.execute(
        select(LbProcess.original_code, LbCutPiece.piece_code, LbCutPiece.piece_name, LbProcessMaterial.quantity)
        .join(LbProcessMaterial, LbProcessMaterial.process_id == LbProcess.id)
        .join(LbCutPiece, LbCutPiece.id == LbProcessMaterial.cut_piece_id)
        .where(LbProcess.style_id == style_id)
        .order_by(LbCutPiece.piece_code)
    )
    mat_map: dict[str, list[dict]] = {}
    for code, pcode, pname, qty in pm.all():
        mat_map.setdefault(code, []).append({"pieceCode": pcode, "pieceName": pname, "quantity": qty})
    for n in tree["nodes"]:
        n["materials"] = mat_map.get(n["id"], [])

    return ok({"ok": result["ok"], "errors": result["errors"], **tree})


@router.post("/styles/{style_id}/encode/confirm")
async def confirm_encode(style_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """确认编码：单向流校验通过后，把 gen_code/gen_upstream/分段写入 Process 正式字段。"""
    style = await _get_owned_style(style_id, user, db)
    procs = await _load_processes(style_id, db)
    if not procs:
        raise HTTPException(status_code=400, detail="该款式还没有录入工序")
    result = encode_processes(_to_encoder_input(procs), takt=style.takt_time)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail={"message": "单向流校验未通过", "errors": result["errors"]})

    by_code = {p.original_code: p for p in procs}
    for enc in result["processes"]:
        p = by_code[enc["original_code"]]
        p.gen_code = enc.get("gen_code")
        p.gen_upstream = enc.get("gen_upstream")
        p.segment_reason = enc.get("segment_reason")
        p.load = enc.get("load")
        p.load_ratio = enc.get("load_ratio")
        p.is_bottleneck = enc.get("is_bottleneck", False)
    await db.commit()
    return ok({"confirmed": len(procs), "terminal": result["terminal"]}, message="编码已确认")


# ============ 平衡寻优（M4 / F3）============
def _topo_order(procs: list[LbProcess]) -> list[LbProcess]:
    """按工艺流向（上游→下游）做稳定拓扑排序，把 DAG 线性化成一条装配线序列。

    线平衡的本质是把工序沿单条产线顺序分配到工位，因此先按拓扑序拉直、再合并相邻工序
    即可。遇到环或缺失上游时按录入顺序兜底，保证一定返回全部工序。
    """
    by_code = {p.original_code: p for p in procs}
    order_index = {p.original_code: i for i, p in enumerate(procs)}

    def upstream_codes(p: LbProcess) -> list[str]:
        if not p.original_upstream:
            return []
        raw = p.original_upstream.replace("，", ",").split(",")
        return [c.strip() for c in raw if c.strip() and c.strip() in by_code]

    indeg = {p.original_code: 0 for p in procs}
    children: dict[str, list[str]] = {p.original_code: [] for p in procs}
    for p in procs:
        for up in upstream_codes(p):
            children[up].append(p.original_code)
            indeg[p.original_code] += 1

    available = [c for c in indeg if indeg[c] == 0]
    topo: list[str] = []
    seen: set[str] = set()
    while available:
        available.sort(key=lambda c: order_index[c])
        cur = available.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        topo.append(cur)
        for ch in children[cur]:
            indeg[ch] -= 1
            if indeg[ch] == 0:
                available.append(ch)
    for p in procs:  # 环/遗漏兜底
        if p.original_code not in seen:
            seen.add(p.original_code)
            topo.append(p.original_code)
    return [by_code[c] for c in topo]


def _build_optimize_input(procs: list[LbProcess]) -> tuple[list[dict], dict[int, LbProcess]]:
    """把工序映射成 optimize_line 入参。

    沿拓扑流向分配连续 original_id（1..N），pre_id 取序列中的前一道（id-1），把工艺图
    拉直成串行装配线 —— 这样合并约束（相邻、ID 差≤5、首尾固定）才能被满足并真正产生合并。
    返回 (algo_input, {original_id: LbProcess}) 供寻优后回填工位。
    """
    ordered = _topo_order(procs)
    oid_to_proc: dict[int, LbProcess] = {}
    algo_input = []
    for i, p in enumerate(ordered, start=1):
        oid_to_proc[i] = p
        algo_input.append({
            "original_id": i,
            "name": p.process_name,
            "time": float(p.sam),
            "people": 1,
            "can_add": bool(p.can_add),
            "pre_id": i - 1 if i > 1 else None,
            "can_merge": bool(p.can_merge),
            "added_people": 0,
            "merge_names": [p.process_name],
        })
    return algo_input, oid_to_proc


@router.post("/balance/optimize")
async def submit_optimize(
    style_id: int, body: OptimizeIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """提交平衡寻优任务（异步）。返回 taskId，前端轮询 /balance/tasks/{id}。

    自动寻优：目标产量/工时留空时，以「瓶颈节拍」为合并目标，最大化合并、不额外加人。
    """
    style = await _get_owned_style(style_id, user, db)
    procs = await _load_processes(style_id, db)
    if not procs:
        raise HTTPException(status_code=400, detail="该款式还没有录入工序")
    if body.use_confirmed_codes and any(p.gen_code is None for p in procs):
        raise HTTPException(status_code=400, detail="存在未确认编码的工序，请先生成并确认编码")

    algo_input, oid_to_proc = _build_optimize_input(procs)
    work_hours = body.work_hours or 8.0
    if body.target_output:
        target_output = body.target_output
    else:
        # 自动：目标节拍取瓶颈周期，使「合并到瓶颈以内」成立 → 工位数最少、平衡率最高
        bottleneck = max(p["time"] / p["people"] for p in algo_input)
        total_sec = work_hours * 3600
        target_output = total_sec / bottleneck if bottleneck > 0 else 1.0
    add_people_fix = body.add_people_fix
    proc_id_map = {oid: p.id for oid, p in oid_to_proc.items()}

    task = task_manager.create()

    def _job(progress):
        result, rate, timed_out = optimize_line(
            algo_input, target_output, work_hours,
            progress_callback=progress, add_people_fix=add_people_fix,
        )
        return _optimize_payload(
            style_id, style.style_code, result, work_hours, proc_id_map, timed_out,
            params={"targetOutput": target_output, "workHours": work_hours, "addPeopleFix": add_people_fix, "auto": not body.target_output},
        )

    task_manager.submit(task, _job)
    return ok({"taskId": task.id, "status": task.status})


def _optimize_payload(style_id, style_code, result, work_hours, proc_id_map, timed_out, params, baseline=False):
    """把优化/基线结果列表统一封装成任务结果 + 工位列表。"""
    kpi = derive_kpi(result, work_hours)
    stations = []
    for idx, g in enumerate(result, start=1):
        stations.append({
            "stationCode": f"ST-{idx:03d}",
            "workerCount": g["people"],
            "time": round(g["time"], 2),
            "mergeNames": g.get("merge_names", [g["name"]]),
            "name": g["name"],
            "originalId": g["original_id"],
            "originalIds": g.get("original_ids", [g["original_id"]]),
            "detailTimes": g.get("detail_times"),
        })
    return {
        "styleId": style_id,
        "balanceRate": round(kpi["balance_rate"], 4),
        "timeoutReached": timed_out,
        "baseline": baseline,
        "kpi": kpi,
        "stations": stations,
        "procIdMap": proc_id_map,
        "params": params,
        "styleCode": style_code,
    }


@router.get("/balance/tasks/{task_id}")
async def get_optimize_task(task_id: str, user: User = Depends(get_current_user)):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return ok(task.to_dict())


# ============ 方案快照（M4 / F4）============
def _plan_dict(p: LbBalancePlan) -> dict:
    return PlanOut.model_validate(p, from_attributes=True).model_dump(by_alias=True)


def _auto_plan_name(res: dict) -> str:
    kpi = res.get("kpi", {})
    people = kpi.get("total_people", "?")
    takt = kpi.get("takt", "?")
    rate_pct = round(res.get("balanceRate", 0) * 100, 1)
    return f"{res.get('styleCode', '款')}_{people}人_{takt}s_平衡{rate_pct}%"


@router.post("/plans")
async def save_plan(
    style_id: int, body: PlanSaveIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """把寻优任务结果落库为方案快照 + 工位。"""
    await _get_owned_style(style_id, user, db)
    task = task_manager.get(body.task_id)
    if not task or task.status != "done" or not task.result:
        raise HTTPException(status_code=400, detail="寻优任务未完成或已过期")
    res = task.result
    if res.get("styleId") != style_id:
        raise HTTPException(status_code=400, detail="任务与款式不匹配")
    plan = await _persist_plan(db, style_id, res, name=body.name)
    return ok({**_plan_dict(plan), "stationCount": len(res.get("stations", []))}, message="方案已保存")


async def _persist_plan(db: AsyncSession, style_id: int, res: dict, name: str | None = None) -> LbBalancePlan:
    """把一份寻优/基线结果写成 LbBalancePlan + LbStation。"""
    kpi = res.get("kpi", {})
    plan = LbBalancePlan(
        style_id=style_id,
        name=name or _auto_plan_name(res),
        worker_count=kpi.get("total_people"),
        takt=kpi.get("takt"),
        balance_rate=res.get("balanceRate"),
        total_work_time=kpi.get("total_time"),
        timeout_reached=res.get("timeoutReached", False),
        params=res.get("params"),
    )
    db.add(plan)
    await db.flush()  # 取 plan.id

    # procIdMap: {算法连续 originalId(str/int) -> 真实 LbProcess.id}，把工位包含的工序映射回真实工序
    proc_id_map = res.get("procIdMap") or {}

    def _real_ids(orig_ids: list) -> list[int]:
        out = []
        for oid in orig_ids or []:
            real = proc_id_map.get(oid, proc_id_map.get(str(oid)))
            if real is not None:
                out.append(real)
        return out

    stations = res.get("stations", [])
    for i, s in enumerate(stations):
        st = LbStation(
            plan_id=plan.id,
            station_code=s["stationCode"],
            worker_count=s["workerCount"],
            station_takt=round(s["time"] / s["workerCount"], 2) if s["workerCount"] else s["time"],
            process_ids=_real_ids(s.get("originalIds", [s.get("originalId")])),
            process_detail=s.get("mergeNames"),
            upstream_station=stations[i - 1]["stationCode"] if i > 0 else None,
            downstream_station=stations[i + 1]["stationCode"] if i < len(stations) - 1 else None,
        )
        db.add(st)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/balance/baseline")
async def save_baseline_plan(
    style_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """生成「原始方案」：每道工序自成一个工位（未优化基线），作为对比起点。

    幂等：若本款已有基线方案则直接返回，不重复创建。
    """
    style = await _get_owned_style(style_id, user, db)
    procs = await _load_processes(style_id, db)
    if not procs:
        raise HTTPException(status_code=400, detail="该款式还没有录入工序")

    existing = await db.execute(
        select(LbBalancePlan).where(LbBalancePlan.style_id == style_id)
    )
    for p in existing.scalars().all():
        if (p.params or {}).get("baseline"):
            return ok({**_plan_dict(p), "stationCount": p.worker_count}, message="已有原始方案")

    algo_input, oid_to_proc = _build_optimize_input(procs)
    work_hours = 8.0
    # 基线：不合并、不加人，每道工序 1 工位
    result = [
        {
            "original_id": p["original_id"],
            "name": p["name"],
            "time": p["time"],
            "people": p["people"],
            "merge_names": [p["name"]],
            "detail_times": [p["time"]],
        }
        for p in algo_input
    ]
    res = _optimize_payload(
        style_id, style.style_code, result, work_hours,
        {oid: pr.id for oid, pr in oid_to_proc.items()}, timed_out=False,
        params={"baseline": True, "workHours": work_hours}, baseline=True,
    )
    name = f"{style.style_code}_原始方案_{len(result)}工位"
    plan = await _persist_plan(db, style_id, res, name=name)
    return ok({**_plan_dict(plan), "stationCount": len(result)}, message="原始方案已生成")


@router.get("/plans")
async def list_plans(
    style_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """方案列表（款式独立）：原始方案置顶，其余按保存先后（旧→新）排列，便于对比优化进程。"""
    await _get_owned_style(style_id, user, db)
    res = await db.execute(
        select(LbBalancePlan).where(LbBalancePlan.style_id == style_id)
        .order_by(LbBalancePlan.created_at.asc())
    )
    plans = list(res.scalars().all())
    plans.sort(key=lambda p: (0 if (p.params or {}).get("baseline") else 1, p.created_at))
    return ok({"list": [_plan_dict(p) for p in plans]})


@router.post("/plans/{plan_id}/select")
async def select_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """选用方案：同款式内唯一，set is_selected=True，其余置 False。下次进入自动恢复。"""
    plan = await _owned_plan(plan_id, user, db)
    others = await db.execute(
        select(LbBalancePlan).where(LbBalancePlan.style_id == plan.style_id)
    )
    for p in others.scalars().all():
        p.is_selected = (p.id == plan_id)
    await db.commit()
    await db.refresh(plan)
    return ok(_plan_dict(plan), message="已选用方案")


@router.get("/plans/selected")
async def get_selected_plan(
    style_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """获取本款式当前选用的方案；无则返回 null。"""
    await _get_owned_style(style_id, user, db)
    res = await db.execute(
        select(LbBalancePlan).where(
            LbBalancePlan.style_id == style_id, LbBalancePlan.is_selected == True  # noqa: E712
        )
    )
    plan = res.scalars().first()
    return ok({"plan": _plan_dict(plan) if plan else None})


@router.get("/plans/{plan_id}/stations")
async def plan_stations(
    plan_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(LbBalancePlan).join(LbStyle, LbBalancePlan.style_id == LbStyle.id)
        .where(LbBalancePlan.id == plan_id, LbStyle.owner_id == user.id)
    )
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="方案不存在")
    st_res = await db.execute(
        select(LbStation).where(LbStation.plan_id == plan_id).order_by(LbStation.station_code)
    )
    stations = [
        {
            "id": s.id,
            "stationCode": s.station_code,
            "workerCount": s.worker_count,
            "stationTakt": s.station_takt,
            "processDetail": s.process_detail,
            "upstreamStation": s.upstream_station,
            "downstreamStation": s.downstream_station,
        }
        for s in st_res.scalars().all()
    ]
    return ok({"plan": _plan_dict(plan), "stations": stations})


# ============ 裁片管理 + 排他关联（M6 / F5）============
def _cutpiece_dict(c: LbCutPiece, used: bool = False, quantity: float | None = None) -> dict:
    d = CutPieceOut.model_validate(c, from_attributes=True).model_dump(by_alias=True)
    d["used"] = used
    if quantity is not None:
        d["quantity"] = quantity
    return d


async def _owned_plan(plan_id: int, user: User, db: AsyncSession) -> LbBalancePlan:
    res = await db.execute(
        select(LbBalancePlan).join(LbStyle, LbBalancePlan.style_id == LbStyle.id)
        .where(LbBalancePlan.id == plan_id, LbStyle.owner_id == user.id)
    )
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="方案不存在")
    return plan


async def _owned_station(station_id: int, user: User, db: AsyncSession) -> LbStation:
    res = await db.execute(
        select(LbStation)
        .join(LbBalancePlan, LbStation.plan_id == LbBalancePlan.id)
        .join(LbStyle, LbBalancePlan.style_id == LbStyle.id)
        .where(LbStation.id == station_id, LbStyle.owner_id == user.id)
    )
    st = res.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="工位不存在")
    return st


@router.post("/styles/{style_id}/cutpieces/import")
async def import_cutpieces(
    style_id: int, body: CutPieceImportIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """数据交换导入裁片 JSON（不手输）。piece_code 款内唯一，重复拒绝。"""
    await _get_owned_style(style_id, user, db)
    codes = [p.piece_code for p in body.pieces]
    if len(codes) != len(set(codes)):
        raise HTTPException(status_code=400, detail="裁片编号 pieceCode 在本次导入内重复")

    if body.replace:
        # 先清掉旧裁片的排他关联，再清裁片
        old = await db.execute(select(LbCutPiece.id).where(LbCutPiece.style_id == style_id))
        old_ids = [i for (i,) in old.all()]
        if old_ids:
            await db.execute(delete(LbProcessCutPiece).where(LbProcessCutPiece.cut_piece_id.in_(old_ids)))
        await db.execute(delete(LbCutPiece).where(LbCutPiece.style_id == style_id))
    else:
        existing = await db.execute(
            select(LbCutPiece.piece_code).where(LbCutPiece.style_id == style_id)
        )
        exist = {c for (c,) in existing.all()}
        clash = exist & set(codes)
        if clash:
            raise HTTPException(status_code=400, detail=f"裁片编号已存在：{sorted(clash)}")

    created = []
    for p in body.pieces:
        cp = LbCutPiece(
            style_id=style_id, piece_code=p.piece_code, piece_name=p.piece_name,
            spec=p.spec, material=p.material,
            shape=p.shape, fabric=p.fabric, area_cm2=p.area_cm2,
            size_mm=p.size_mm, ref_image=p.ref_image,
        )
        db.add(cp)
        created.append(cp)
    await db.commit()
    for cp in created:
        await db.refresh(cp)
    return ok({"list": [_cutpiece_dict(c) for c in created], "count": len(created)})


@router.get("/styles/{style_id}/cutpieces")
async def list_cutpieces(
    style_id: int, plan_id: int | None = None, unused_only: bool = False,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """裁片列表。传 plan_id 时标注 used（该方案下已被某工位排他占用）；
    unused_only=True 仅返回未被占用的（双击选择时只显示未引用裁片）。"""
    await _get_owned_style(style_id, user, db)
    res = await db.execute(
        select(LbCutPiece).where(LbCutPiece.style_id == style_id).order_by(LbCutPiece.piece_code)
    )
    pieces = list(res.scalars().all())

    used_ids: set[int] = set()
    if plan_id is not None:
        used_res = await db.execute(
            select(LbProcessCutPiece.cut_piece_id).where(LbProcessCutPiece.plan_id == plan_id)
        )
        used_ids = {i for (i,) in used_res.all()}
    else:
        # 无 plan 上下文：按工序级绑定标注是否已被任一工序使用
        used_res = await db.execute(
            select(LbProcessMaterial.cut_piece_id)
            .join(LbProcess, LbProcess.id == LbProcessMaterial.process_id)
            .where(LbProcess.style_id == style_id)
        )
        used_ids = {i for (i,) in used_res.all()}

    rows = [_cutpiece_dict(c, used=c.id in used_ids) for c in pieces]
    if unused_only:
        rows = [r for r in rows if not r["used"]]
    return ok({"list": rows, "total": len(rows)})


@router.post("/stations/{station_id}/cutpieces")
async def bind_station_cutpieces(
    station_id: int, body: StationCutPieceIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """工位-物料关联（装配 BOM）：整体覆盖本工位绑定，每条带数量。
    物料可被多个工位复用（标准件如螺母/螺栓），不再排他。"""
    station = await _owned_station(station_id, user, db)
    plan_id = station.plan_id
    items = body.normalized()

    # 先解除本工位旧绑定（覆盖语义）
    await db.execute(
        delete(LbProcessCutPiece).where(LbProcessCutPiece.station_id == station_id)
    )
    if items:
        plan = await _owned_plan(plan_id, user, db)
        ids = [it.cut_piece_id for it in items]
        valid_res = await db.execute(
            select(LbCutPiece.id).where(
                LbCutPiece.style_id == plan.style_id,
                LbCutPiece.id.in_(ids),
            )
        )
        valid_ids = {i for (i,) in valid_res.all()}
        bad = set(ids) - valid_ids
        if bad:
            raise HTTPException(status_code=400, detail=f"物料不属于本款：{sorted(bad)}")

        seen: set[int] = set()
        for it in items:
            if it.cut_piece_id in seen:  # 同工位去重，保留首条
                continue
            seen.add(it.cut_piece_id)
            db.add(LbProcessCutPiece(
                plan_id=plan_id, station_id=station_id,
                cut_piece_id=it.cut_piece_id, quantity=it.quantity,
            ))
    await db.commit()
    return ok({"stationId": station_id, "boundCount": len(items)}, message="物料关联已更新")


# ============ 工序级物料关联（新绑定单位：工序）============
@router.get("/processes/{process_id}/materials")
async def get_process_materials(
    process_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """取某工序已绑定的物料（含本工序消耗数量）。"""
    await _owned_process(process_id, user, db)
    pm = await db.execute(
        select(LbCutPiece, LbProcessMaterial.quantity)
        .join(LbProcessMaterial, LbProcessMaterial.cut_piece_id == LbCutPiece.id)
        .where(LbProcessMaterial.process_id == process_id)
        .order_by(LbCutPiece.piece_code)
    )
    pieces = [_cutpiece_dict(c, used=True, quantity=qty) for c, qty in pm.all()]
    return ok({"processId": process_id, "materials": pieces})


@router.post("/processes/{process_id}/materials")
async def bind_process_materials(
    process_id: int, body: ProcessMaterialIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """工序-物料关联（装配 BOM）：整体覆盖本工序绑定，每条带数量。
    物料可被多个工序复用（标准件如螺母/螺栓）。工序变化时物料随之变化，
    优化合并工序成工位后，由工位包含的工序聚合出工位物料，最终汇入 SOP。"""
    proc = await _owned_process(process_id, user, db)
    items = body.normalized()

    await db.execute(
        delete(LbProcessMaterial).where(LbProcessMaterial.process_id == process_id)
    )
    if items:
        ids = [it.cut_piece_id for it in items]
        valid_res = await db.execute(
            select(LbCutPiece.id).where(
                LbCutPiece.style_id == proc.style_id,
                LbCutPiece.id.in_(ids),
            )
        )
        valid_ids = {i for (i,) in valid_res.all()}
        bad = set(ids) - valid_ids
        if bad:
            raise HTTPException(status_code=400, detail=f"物料不属于本款：{sorted(bad)}")
        seen: set[int] = set()
        for it in items:
            if it.cut_piece_id in seen:
                continue
            seen.add(it.cut_piece_id)
            db.add(LbProcessMaterial(
                process_id=process_id, cut_piece_id=it.cut_piece_id, quantity=it.quantity,
            ))
    await db.commit()
    return ok({"processId": process_id, "boundCount": len(items)}, message="物料关联已更新")


# ============ 工序双手作业分析数据 ============
@router.get("/processes/{process_id}/two-hand")
async def get_two_hand(
    process_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    proc = await _owned_process(process_id, user, db)
    return ok({"processId": process_id, "data": proc.two_hand_data})


@router.put("/processes/{process_id}/two-hand")
async def save_two_hand(
    process_id: int, body: TwoHandDataIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """保存工序双手作业分析图数据（TwoHandChart 快照）。"""
    proc = await _owned_process(process_id, user, db)
    proc.two_hand_data = body.data
    await db.commit()
    return ok({"processId": process_id}, message="双手作业分析已保存")


@router.post("/uploads/images")
async def upload_image(
    file: UploadFile = File(...), user: User = Depends(get_current_user),
):
    """上传裁片/参考图，返回可访问 URL（/static/lb/...）。"""
    allowed = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的图片类型：{file.content_type}")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片超过 5MB 上限")
    ext = Path(file.filename or "").suffix.lower() or ".png"
    sub = LB_UPLOAD_DIR / f"u{user.id}"
    sub.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (sub / name).write_bytes(data)
    return ok({"url": f"/static/lb/u{user.id}/{name}", "filename": name})


# ============ 视频分析（工序录入第二入口）============
def _user_video_dir(user_id: int) -> Path:
    d = LB_VIDEO_DIR / f"u{user_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_video_path(user_id: int, filename: str) -> Path:
    """把前端回传的文件名解析到该用户视频目录内，拒绝目录穿越。"""
    base = _user_video_dir(user_id).resolve()
    target = (base / Path(filename).name).resolve()
    if base != target.parent:
        raise HTTPException(status_code=400, detail="非法的文件名")
    return target


@router.post("/styles/{style_id}/video")
async def upload_video(
    style_id: int, file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """上传工序分析视频：落盘 + ffprobe 取时长，供前端打点切分。"""
    await _get_owned_style(style_id, user, db)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in lb_video.ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式：{ext or '未知'}")
    data = await file.read()
    if len(data) > 500 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="视频超过 500MB 上限")
    name = f"{uuid.uuid4().hex}{ext}"
    out = _user_video_dir(user.id) / name
    out.write_bytes(data)
    try:
        duration = lb_video.probe_duration(out)
    except lb_video.VideoError as e:
        out.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    return ok({"url": f"/static/lbvideo/u{user.id}/{name}", "filename": name, "duration": duration})


@router.post("/video/clip")
async def clip_video(
    body: VideoClipIn, user: User = Depends(get_current_user),
):
    """按时间区间切出片段（预览/下载用）。视频归属由用户目录隔离。"""
    src = _safe_video_path(user.id, body.filename)
    if not src.is_file():
        raise HTTPException(status_code=404, detail="视频不存在或已过期")
    clip_name = f"{src.stem}_{int(body.start * 1000)}_{int(body.end * 1000)}.mp4"
    dst = _user_video_dir(user.id) / "clips" / clip_name
    try:
        lb_video.clip_segment(src, dst, body.start, body.end)
    except lb_video.VideoError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok({"url": f"/static/lbvideo/u{user.id}/clips/{clip_name}", "filename": clip_name})


# ============ 工位信息补录 + 单工位 SOP（M6 / F6）============
def _station_full_dict(s: LbStation) -> dict:
    return StationOut.model_validate(s, from_attributes=True).model_dump(by_alias=True)


_STATION_INFO_FIELDS = (
    # 工位人数（SOP 阶段补录）
    "worker_count",
    # 合并工序名（累加，可编辑）
    "process_detail",
    # 旧 5 段（兼容保留）
    "work_steps", "tools", "process_req", "quality_req", "ref_images",
    # 装配 SOP 段
    "process_seq", "work_type", "check_steps", "main_steps", "notes",
    "self_check", "tech_req", "equipment",
    # 审批 / 文档头
    "approver", "reviewer", "department", "owner_name", "file_no", "version",
)


@router.put("/stations/{station_id}/info")
async def update_station_info(
    station_id: int, body: StationInfoIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """补录工位装配 SOP 信息（对齐参考 SOP.xlsx）：工序排号/作业类型/检查工序/
    本工序作业/注意事项/自检/技术要求/设备工装/审批栏 + 旧 5 段兼容字段。"""
    station = await _owned_station(station_id, user, db)
    for field in _STATION_INFO_FIELDS:
        val = getattr(body, field)
        if val is not None:
            if field == "equipment":
                val = [e.model_dump() for e in val]
            setattr(station, field, val)
    await db.commit()
    await db.refresh(station)
    return ok(_station_full_dict(station))


async def _station_materials(station: LbStation, db: AsyncSession) -> list[dict]:
    """聚合工位物料：由工位包含的工序（process_ids）绑定的物料合并而来。

    同一物料被工位内多道工序消耗时，数量累加。这是「工序变化 → 物料随之变化 → 汇入 SOP」
    链路在工位侧的落点。若 process_ids 为空（旧方案/基线未回填），回退到工位级旧绑定。
    """
    proc_ids = station.process_ids or []
    if proc_ids:
        pm = await db.execute(
            select(LbCutPiece, LbProcessMaterial.quantity)
            .join(LbProcessMaterial, LbProcessMaterial.cut_piece_id == LbCutPiece.id)
            .where(LbProcessMaterial.process_id.in_(proc_ids))
            .order_by(LbCutPiece.piece_code)
        )
        agg: dict[int, tuple[LbCutPiece, float]] = {}
        for c, qty in pm.all():
            if c.id in agg:
                agg[c.id] = (c, agg[c.id][1] + (qty or 0))
            else:
                agg[c.id] = (c, qty or 0)
        return [_cutpiece_dict(c, used=True, quantity=q) for c, q in agg.values()]
    # 回退：旧的工位级绑定
    pcp = await db.execute(
        select(LbCutPiece, LbProcessCutPiece.quantity)
        .join(LbProcessCutPiece, LbProcessCutPiece.cut_piece_id == LbCutPiece.id)
        .where(LbProcessCutPiece.station_id == station.id)
        .order_by(LbCutPiece.piece_code)
    )
    return [_cutpiece_dict(c, used=True, quantity=qty) for c, qty in pcp.all()]


@router.get("/stations/{station_id}")
async def get_station(
    station_id: int,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    station = await _owned_station(station_id, user, db)
    pieces = await _station_materials(station, db)
    return ok({**_station_full_dict(station), "cutPieces": pieces})


async def _build_sop_context(station: LbStation, db: AsyncSession) -> dict:
    """拼装单工位 SOP 渲染上下文（款式/方案/工位/物料）。
    物料来自工位包含工序聚合（见 _station_materials）。"""
    plan = (await db.execute(
        select(LbBalancePlan).where(LbBalancePlan.id == station.plan_id)
    )).scalar_one()
    style = (await db.execute(
        select(LbStyle).where(LbStyle.id == plan.style_id)
    )).scalar_one()
    cut_pieces = await _station_materials(station, db)
    return doc_builder.build_station_context(
        station=_station_full_dict(station),
        style=_style_dict(style),
        plan=_plan_dict(plan),
        cut_pieces=cut_pieces,
    )


@router.post("/sop/batch")
async def batch_sop(
    plan_id: int, body: SopBatchIn,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """批量生成方案下所有（或指定）工位的 SOP，异步任务 + 进度。
    fmt=pdf 合并成单个 Batch_SOP_<款号>_<日期>.pdf；fmt=html 合并多页 HTML。"""
    plan = await _owned_plan(plan_id, user, db)
    style = (await db.execute(select(LbStyle).where(LbStyle.id == plan.style_id))).scalar_one()

    q = select(LbStation).where(LbStation.plan_id == plan_id)
    if body.station_ids:
        q = q.where(LbStation.id.in_(body.station_ids))
    st_res = await db.execute(q.order_by(LbStation.station_code))
    stations = list(st_res.scalars().all())
    if not stations:
        raise HTTPException(status_code=400, detail="该方案下没有可生成的工位")

    # 预先把每个工位的渲染上下文取出（避免后台线程触碰 async session）
    contexts = []
    for s in stations:
        contexts.append((s.station_code, await _build_sop_context(s, db)))

    fmt = body.fmt
    style_code = style.style_code
    user_id = user.id
    date_str = _dt.date.today().strftime("%Y%m%d")
    total = len(contexts)

    task = task_manager.create()

    def _job(progress):
        progress(f"开始生成，共 {total} 个工位")
        if fmt == "xlsx":
            data = xlsx_builder.build_batch_xlsx(contexts)
            fname = f"Batch_SOP_{style_code}_{date_str}.xlsx"
            out = LB_SOP_DIR / f"u{user_id}" / fname
            doc_builder.write_file(out, data)
            url = f"/static/sop/u{user_id}/{fname}"
        elif fmt == "pdf":
            pdfs = []
            for i, (code, ctx) in enumerate(contexts, start=1):
                progress(f"正在处理({i}/{total}): {code}")
                html = doc_builder.render_station_html(ctx)
                pdfs.append(doc_builder.html_to_pdf_bytes(html))
            merged = doc_builder.merge_pdfs(pdfs)
            fname = f"Batch_SOP_{style_code}_{date_str}.pdf"
            out = LB_SOP_DIR / f"u{user_id}" / fname
            doc_builder.write_file(out, merged)
            url = f"/static/sop/u{user_id}/{fname}"
        else:
            stations_ctx = []
            for i, (code, ctx) in enumerate(contexts, start=1):
                progress(f"正在处理({i}/{total}): {code}")
                stations_ctx.append(ctx)
            html = doc_builder.render_batch_html(stations_ctx, {"styleCode": style_code})
            fname = f"Batch_SOP_{style_code}_{date_str}.html"
            out = LB_SOP_DIR / f"u{user_id}" / fname
            doc_builder.write_file(out, html.encode("utf-8"))
            url = f"/static/sop/u{user_id}/{fname}"
        progress(f"完成({total}/{total})")
        return {"url": url, "filename": fname, "count": total, "fmt": fmt}

    task_manager.submit(task, _job)
    return ok({"taskId": task.id, "status": task.status, "total": total})


@router.get("/sop/tasks/{task_id}")
async def get_sop_task(task_id: str, user: User = Depends(get_current_user)):
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return ok(task.to_dict())


@router.post("/sop/{station_id}")
async def generate_station_sop(
    station_id: int, fmt: str = "html",
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """单工位 SOP：fmt=html 返回 HTML；fmt=xlsx 生成装配 SOP Excel（对齐参考件）；
    fmt=pdf 生成 PDF。xlsx/pdf 落盘返回下载 URL。"""
    station = await _owned_station(station_id, user, db)
    ctx = await _build_sop_context(station, db)
    style_code = ctx["style"].get("styleCode", "style")

    if fmt == "xlsx":
        data = xlsx_builder.build_station_xlsx(ctx)
        fname = f"SOP_{style_code}_{station.station_code}.xlsx"
        out = LB_SOP_DIR / f"u{user.id}" / fname
        doc_builder.write_file(out, data)
        return ok({"url": f"/static/sop/u{user.id}/{fname}", "filename": fname})

    html = doc_builder.render_station_html(ctx)
    if fmt == "html":
        return HTMLResponse(content=html)
    if fmt == "pdf":
        try:
            pdf = doc_builder.html_to_pdf_bytes(html)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"PDF 生成失败，可改用 HTML：{e}")
        fname = f"{style_code}_{station.station_code}.pdf"
        out = LB_SOP_DIR / f"u{user.id}" / fname
        doc_builder.write_file(out, pdf)
        return ok({"url": f"/static/sop/u{user.id}/{fname}", "filename": fname})
    raise HTTPException(status_code=400, detail="fmt 仅支持 html / xlsx / pdf")
