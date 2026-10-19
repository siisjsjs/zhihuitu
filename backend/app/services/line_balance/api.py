"""产线平衡优化对外封装入口（无 GUI / 无授权）。

optimize_with_backtracking 接收的是"已加完人、已知节拍"的工序，原程序在 GUI 层
（optimize_balance）先做了两件事：算节拍、循环加人降瓶颈。本模块把这段预处理收进
optimize_line()，让复用方一行调用即可。

输入/输出契约见扩展计划书 §3。
"""
from __future__ import annotations
import copy
from .optimizer import optimize_with_backtracking, evaluate_solution

REQUIRED_FIELDS = ("original_id", "name", "time", "people", "can_add", "pre_id", "can_merge")


def _validate(processes: list[dict]) -> None:
    """系统边界校验（算法内部不重复校验）。"""
    if not processes:
        raise ValueError("processes 不能为空")
    ids = []
    for i, p in enumerate(processes):
        missing = [f for f in REQUIRED_FIELDS if f not in p]
        if missing:
            raise ValueError(f"第 {i} 个工序缺少字段：{missing}")
        if p["people"] < 1:
            raise ValueError(f"工序 {p['original_id']} 的 people 必须 ≥ 1")
        if p["time"] <= 0:
            raise ValueError(f"工序 {p['original_id']} 的 time 必须 > 0")
        ids.append(p["original_id"])
    if len(ids) != len(set(ids)):
        raise ValueError("original_id 必须唯一")
    id_set = set(ids)
    for p in processes:
        pre = p.get("pre_id")
        if pre is not None and pre not in id_set:
            raise ValueError(f"工序 {p['original_id']} 的 pre_id={pre} 不存在")


def _normalize(processes: list[dict]) -> list[dict]:
    """补齐算法所需的派生字段，不修改调用方原数据。"""
    out = copy.deepcopy(processes)
    for p in out:
        p.setdefault("added_people", 0)
        p.setdefault("merge_names", [p["name"]])
    return out


def optimize_line(
    processes: list[dict],
    target_output: float,
    work_hours: float,
    progress_callback=None,
    add_people_fix: bool = False,
):
    """产线平衡优化主入口。

    Args:
        processes: list[dict]，字段见计划书 §3.1（original_id/name/time/people/
            can_add/pre_id/can_merge，可选 added_people/merge_names）。
        target_output: 目标每班产能（件），> 0。
        work_hours: 每班工时（小时），> 0。
        progress_callback: callable|None，进度回调，纯跑传 None。
        add_people_fix: 加人预处理逻辑选择。
            False（默认）= 复现原 exe 行为（保留反编译原始判断，已对拍一致）；
            True = 采用修正逻辑 `and not can_add`（计划书 §6 风险#1 怀疑的正确语义）。

    Returns:
        (result, rate, timeout_reached) —— 见计划书 §3.2。
    """
    if target_output <= 0 or work_hours <= 0:
        raise ValueError("target_output 和 work_hours 必须 > 0")

    _validate(processes)
    procs = _normalize(processes)

    total_sec = work_hours * 3600
    target_takt = total_sec / target_output

    # —— 预处理：给瓶颈工序加人，直到瓶颈达标或无法再加 ——
    while True:
        for p in procs:
            p["cycle_time"] = p["time"] / p["people"]
        b = max(procs, key=lambda x: x["cycle_time"])
        if add_people_fix:
            # 修正语义：瓶颈已达标，或该工序不允许加人 → 停止
            if b["cycle_time"] <= target_takt or not b["can_add"]:
                break
        else:
            # 原 exe 语义（原样保留，便于对拍）
            if b["cycle_time"] <= target_takt or b["can_add"]:
                break
        b["people"] += 1
        b["added_people"] += 1

    return optimize_with_backtracking(procs, target_takt, progress_callback)


def derive_kpi(result: list[dict], work_hours: float) -> dict:
    """从优化结果派生常用 KPI（计划书 §3.3）。"""
    total_sec = work_hours * 3600
    total_time = sum(p["time"] for p in result)
    total_people = sum(p["people"] for p in result)
    final_bottleneck = max(p["time"] / p["people"] for p in result)
    final_output = round(total_sec / final_bottleneck) if final_bottleneck else 0
    return {
        "total_time": round(total_time, 2),
        "total_people": total_people,
        "station_count": len(result),
        "takt": round(final_bottleneck, 2),
        "output_per_shift": final_output,
        "balance_rate": round(evaluate_solution(result), 4),
    }
