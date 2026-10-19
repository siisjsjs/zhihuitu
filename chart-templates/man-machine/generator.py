"""人机作业分析图生成器（服务端 matplotlib 版，版式对齐 ManMachineChart.vue）"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

BORDER = "#999999"
HEADER_BG = "#e8e8e8"
SUBHEADER_BG = "#f0f0f0"
LABEL_BG = "#f1f5f9"
STATS_BG = "#f8fafc"
WORK_BG = "#a0a0a0"
IDLE_BG = "#ffffff"
GOOD = "#16a34a"
BAD = "#dc2626"
TEXT = "#333333"

PT2U = 100.0 / 72.0  # 1pt 字号在画布单位坐标下的近似高度（figsize = 尺寸/100 英寸）


def _char_w(ch: str, fontsize: float) -> float:
    return fontsize * PT2U * (1.0 if ord(ch) > 0x2E7F else 0.58)


def _wrap(text: str, max_w: float, fontsize: float):
    lines = []
    for raw in str(text).split("\n"):
        cur, w = "", 0.0
        for ch in raw:
            cw = _char_w(ch, fontsize)
            if cur and w + cw > max_w:
                lines.append(cur)
                cur, w = ch, cw
            else:
                cur += ch
                w += cw
        lines.append(cur)
    return lines or [""]


def _cell(ax, x, y, w, h, text="", fill="white", fontsize=10, bold=False,
          color=TEXT, ha="center", wrap=False, lw=0.9):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=BORDER,
                           linewidth=lw, zorder=1))
    text = "" if text is None else str(text)
    if text:
        if wrap:
            text = "\n".join(_wrap(text, w - 12, fontsize))
        tx = x + w / 2 if ha == "center" else x + 6
        ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fontsize,
                color=color, fontweight="bold" if bold else "normal",
                linespacing=1.35, zorder=2)


def _fmt(v: float) -> str:
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:g}"


def _merge_groups(keys):
    """连续相同 key 合并，返回 [(start, span), ...]"""
    groups, i = [], 0
    while i < len(keys):
        span = 1
        while i + span < len(keys) and keys[i + span] == keys[i]:
            span += 1
        groups.append((i, span))
        i += span
    return groups


def generate(params: dict) -> dict:
    setup_chinese_font()
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")

    header = params.get("headerInfo") or {}
    if not isinstance(header, dict):
        raise ChartValidationError("headerInfo 必须是对象")
    task_name = str(header.get("taskName", "") or "")
    worker_name = str(header.get("worker", "") or "操作者")
    date = str(header.get("date", "") or "")
    analyst = str(header.get("analyst", "") or "")

    raw_machines = params.get("machines")
    if not isinstance(raw_machines, list) or not raw_machines:
        raise ChartValidationError("machines（机器列）不能为空")
    machines = []
    for i, m in enumerate(raw_machines):
        if not isinstance(m, dict) or not m.get("id"):
            raise ChartValidationError(f"machines 第 {i + 1} 项缺少 id")
        machines.append({"id": str(m["id"]), "name": str(m.get("name", "") or f"机器{i + 1}")})

    raw_rows = params.get("rows")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ChartValidationError("rows（作业行）不能为空")

    def _norm_state(v):
        return "work" if str(v).strip().lower() in ("work", "working") else "idle"

    rows = []
    for i, r in enumerate(raw_rows):
        if not isinstance(r, dict):
            raise ChartValidationError(f"rows 第 {i + 1} 项必须是对象")
        try:
            t = float(r.get("time"))
        except (TypeError, ValueError):
            raise ChartValidationError(f"rows 第 {i + 1} 项的 time 必须是数字")
        if t < 0:
            raise ChartValidationError(f"rows 第 {i + 1} 项的 time 不能为负数")
        cells_in = r.get("cells") or {}
        cells = {}
        for m in machines:
            c = cells_in.get(m["id"]) or {}
            cells[m["id"]] = {"desc": str(c.get("desc", "") or ""), "state": _norm_state(c.get("state", "idle"))}
        rows.append({
            "time": t,
            "workerDesc": str(r.get("workerDesc", "") or ""),
            "workerState": _norm_state(r.get("workerState", "idle")),
            "cells": cells,
        })

    n = len(rows)
    times = [r["time"] for r in rows]
    cycle = sum(times)
    if cycle <= 0:
        raise ChartValidationError("所有作业行的 time 之和必须大于 0")

    # ── 统计 ──
    worker_work = sum(r["time"] for r in rows if r["workerState"] == "work")
    worker_eff = round(worker_work / cycle * 100, 1)
    machine_stats = {}
    for m in machines:
        w = sum(r["time"] for r in rows if r["cells"][m["id"]]["state"] == "work")
        machine_stats[m["id"]] = {"work": w, "idle": cycle - w, "eff": round(w / cycle * 100, 1)}

    # ── 合并组（连续相同 描述+状态） ──
    worker_groups = _merge_groups([(r["workerDesc"], r["workerState"]) for r in rows])
    machine_groups = {
        m["id"]: _merge_groups([(r["cells"][m["id"]]["desc"], r["cells"][m["id"]]["state"]) for r in rows])
        for m in machines
    }

    # ── 列布局 ──
    M = len(machines)
    time_w = 54.0
    desc_w = 170.0 if M <= 2 else max(120.0, 560.0 / (M + 1))
    bar_w = 42.0
    unit_w = desc_w + bar_w
    total_w = time_w + unit_w * (1 + M)
    x_time = 0.0
    x_units = [time_w + unit_w * k for k in range(1 + M)]  # 0=操作人，1..M=机器

    # ── 数据行高：时间成比例 + 保证文字放得下 ──
    fs_body = 9.5
    scale = min(8.0, max(0.6, 300.0 / cycle))
    heights = [max(t * scale, 18.0) for t in times]

    def _ensure_group_height(groups, texts):
        for start, span in groups:
            lines = _wrap(texts[start], desc_w - 12, fs_body)
            need = len(lines) * fs_body * PT2U * 1.45 + 10
            cur = sum(heights[start:start + span])
            if cur < need:
                add = (need - cur) / span
                for k in range(start, start + span):
                    heights[k] += add

    _ensure_group_height(worker_groups, [r["workerDesc"] for r in rows])
    for m in machines:
        _ensure_group_height(machine_groups[m["id"]], [r["cells"][m["id"]]["desc"] for r in rows])

    # ── 行布局 ──
    title_h, info_h, head1_h, head2_h = 44.0, 28.0, 30.0, 24.0
    stats_title_h, stats_head_h, stats_row_h = 30.0, 26.0, 26.0
    data_h = sum(heights)
    total_h = (title_h + info_h * 3 + head1_h + head2_h + data_h
               + stats_title_h + stats_head_h + stats_row_h * (1 + M))

    fig = plt.figure(figsize=(total_w / 100.0, total_h / 100.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-1, total_w + 1)
    ax.set_ylim(total_h + 1, -1)
    ax.axis("off")

    y = 0.0
    # 标题
    _cell(ax, 0, y, total_w, title_h, "人机作业分析图", fontsize=15, bold=True)
    y += title_h
    # 信息区
    label_w, val_w = 90.0, 170.0
    _cell(ax, 0, y, label_w, info_h, "作业名称", fill=LABEL_BG, bold=True)
    _cell(ax, label_w, y, total_w - label_w, info_h, task_name)
    y += info_h
    rest = total_w - label_w * 2 - val_w
    _cell(ax, 0, y, label_w, info_h, "操作者", fill=LABEL_BG, bold=True)
    _cell(ax, label_w, y, val_w, info_h, worker_name)
    _cell(ax, label_w + val_w, y, label_w, info_h, "机器", fill=LABEL_BG, bold=True)
    _cell(ax, label_w * 2 + val_w, y, rest, info_h, "、".join(m["name"] for m in machines))
    y += info_h
    _cell(ax, 0, y, label_w, info_h, "日期", fill=LABEL_BG, bold=True)
    _cell(ax, label_w, y, val_w, info_h, date)
    _cell(ax, label_w + val_w, y, label_w, info_h, "研究者", fill=LABEL_BG, bold=True)
    _cell(ax, label_w * 2 + val_w, y, rest, info_h, analyst)
    y += info_h

    # 表头
    _cell(ax, x_time, y, time_w, head1_h + head2_h, "时间/s", fill=HEADER_BG, bold=True, fontsize=10)
    col_names = [worker_name] + [m["name"] for m in machines]
    for k, name in enumerate(col_names):
        _cell(ax, x_units[k], y, unit_w, head1_h, name, fill=HEADER_BG, bold=True, fontsize=10.5, wrap=True)
        _cell(ax, x_units[k], y + head1_h, desc_w, head2_h, "描述", fill=SUBHEADER_BG, bold=True, fontsize=9)
        _cell(ax, x_units[k] + desc_w, y + head1_h, bar_w, head2_h, "状态", fill=SUBHEADER_BG, bold=True, fontsize=9)
    y += head1_h + head2_h

    # 数据区
    row_y = [y]
    for h in heights:
        row_y.append(row_y[-1] + h)
    cum = 0.0
    for i, r in enumerate(rows):
        cum += r["time"]
        _cell(ax, x_time, row_y[i], time_w, heights[i], _fmt(cum), fontsize=8.5)

    def _draw_col(x0, groups, descs, states):
        for start, span in groups:
            gy, gh = row_y[start], sum(heights[start:start + span])
            _cell(ax, x0, gy, desc_w, gh, descs[start], fontsize=fs_body, ha="left", wrap=True)
            is_work = states[start] == "work"
            _cell(ax, x0 + desc_w, gy, bar_w, gh, fill=WORK_BG if is_work else IDLE_BG)

    _draw_col(x_units[0], worker_groups,
              [r["workerDesc"] for r in rows], [r["workerState"] for r in rows])
    for k, m in enumerate(machines):
        _draw_col(x_units[k + 1], machine_groups[m["id"]],
                  [r["cells"][m["id"]]["desc"] for r in rows],
                  [r["cells"][m["id"]]["state"] for r in rows])
    y = row_y[-1]

    # 统计汇总
    _cell(ax, 0, y, total_w, stats_title_h, "统计汇总", fill=STATS_BG, bold=True, fontsize=11.5)
    y += stats_title_h
    fr = [0.24, 0.19, 0.19, 0.19, 0.19]
    sw = [f * total_w for f in fr]
    sx = [sum(sw[:k]) for k in range(5)]
    for k, head in enumerate(["项目", "周程/s", "工作时间/s", "空闲时间/s", "利用率/%"]):
        _cell(ax, sx[k], y, sw[k], stats_head_h, head, fill=HEADER_BG, bold=True, fontsize=9.5)
    y += stats_head_h

    def _stat_row(label, work, idle, eff):
        nonlocal y
        _cell(ax, sx[0], y, sw[0], stats_row_h, label, fill=LABEL_BG, bold=True, fontsize=9.5)
        _cell(ax, sx[1], y, sw[1], stats_row_h, _fmt(cycle), fontsize=9.5)
        _cell(ax, sx[2], y, sw[2], stats_row_h, _fmt(work), fontsize=9.5)
        _cell(ax, sx[3], y, sw[3], stats_row_h, _fmt(idle), fontsize=9.5)
        _cell(ax, sx[4], y, sw[4], stats_row_h, f"{eff}%", bold=True, fontsize=9.5,
              color=GOOD if eff >= 80 else BAD)
        y += stats_row_h

    _stat_row(worker_name, worker_work, cycle - worker_work, worker_eff)
    for m in machines:
        st = machine_stats[m["id"]]
        _stat_row(m["name"], st["work"], st["idle"], st["eff"])

    summary = {
        "周程时间(s)": round(cycle, 2),
        "人员工作时间(s)": round(worker_work, 2),
        "人员利用率(%)": worker_eff,
    }
    for m in machines:
        summary[f"{m['name']}利用率(%)"] = machine_stats[m["id"]]["eff"]

    return {"image_base64": figure_to_base64(fig), "summary": summary}
