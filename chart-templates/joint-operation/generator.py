"""联合作业分析图生成器（服务端 matplotlib 版，版式对齐 JointOperation.vue）"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

BORDER = "#8a8a8a"
HEADER_BG = "#e8e8e8"
SUBHEADER_BG = "#f0f0f0"
LABEL_BG = "#f5f5f5"
AVG_BG = "#fafafa"
WORK_BG = "#a0a0a0"
IDLE_BG = "#ffffff"
GOOD = "#16a34a"
BAD = "#dc2626"
IDLE_TXT = "#94a3b8"
TEXT = "#333333"

PT2U = 100.0 / 72.0


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
    f = round(float(v), 2)
    return str(int(f)) if f == int(f) else f"{f:g}"


def generate(params: dict) -> dict:
    setup_chinese_font()
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")

    header = params.get("headerInfo") or {}
    if not isinstance(header, dict):
        raise ChartValidationError("headerInfo 必须是对象")
    task_name = str(header.get("taskName", "") or "—")
    operator = str(header.get("operator", "") or "—")
    date = str(header.get("date", "") or "—")
    location = str(header.get("location", "") or "—")
    remarks = str(header.get("remarks", "") or "—")

    raw_cols = params.get("columns")
    if not isinstance(raw_cols, list) or not raw_cols:
        raise ChartValidationError("columns（作业者列）不能为空")
    columns = []
    for i, c in enumerate(raw_cols):
        if not isinstance(c, dict) or not c.get("id"):
            raise ChartValidationError(f"columns 第 {i + 1} 项缺少 id")
        columns.append({"id": str(c["id"]), "name": str(c.get("name", "") or f"作业者{i + 1}")})

    raw_rows = params.get("timeRows")
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ChartValidationError("timeRows（时间行）不能为空")
    time_rows = []
    for i, r in enumerate(raw_rows):
        if not isinstance(r, dict):
            raise ChartValidationError(f"timeRows 第 {i + 1} 项必须是对象")
        try:
            t = float(r.get("time"))
        except (TypeError, ValueError):
            raise ChartValidationError(f"timeRows 第 {i + 1} 项的 time 必须是数字")
        cells_in = r.get("cells") or {}
        cells = {}
        for c in columns:
            cc = cells_in.get(c["id"]) or {}
            try:
                dur = float(cc.get("duration", 0) or 0)
            except (TypeError, ValueError):
                raise ChartValidationError(f"timeRows 第 {i + 1} 行 {c['name']} 的 duration 必须是数字")
            cells[c["id"]] = {"desc": str(cc.get("desc", "") or ""),
                              "duration": dur,
                              "isWork": bool(cc.get("isWork", False))}
        time_rows.append({"time": t, "cells": cells})

    n = len(time_rows)
    cycle = max(r["time"] for r in time_rows)
    if cycle <= 0:
        raise ChartValidationError("timeRows 的时间点必须大于 0")

    # ── 统计 ──
    stats = {}
    for c in columns:
        work = sum(r["cells"][c["id"]]["duration"] for r in time_rows if r["cells"][c["id"]]["isWork"])
        idle = max(0.0, cycle - work)
        eff = round(work / cycle * 100, 1) if cycle > 0 else 0.0
        stats[c["id"]] = {"work": work, "idle": idle, "eff": eff}
    avg_work = sum(s["work"] for s in stats.values()) / len(columns)
    avg_idle = sum(s["idle"] for s in stats.values()) / len(columns)
    avg_eff = round(sum(s["work"] for s in stats.values()) / (cycle * len(columns)) * 100, 1)

    # ── 合并组（同列连续相同 desc+isWork，desc 为空不合并） ──
    def _groups_for(col_id):
        groups, i = [], 0
        while i < n:
            cell = time_rows[i]["cells"][col_id]
            span = 1
            if cell["desc"]:
                while i + span < n:
                    nxt = time_rows[i + span]["cells"][col_id]
                    if nxt["desc"] == cell["desc"] and nxt["isWork"] == cell["isWork"]:
                        span += 1
                    else:
                        break
            groups.append((i, span))
            i += span
        return groups

    col_groups = {c["id"]: _groups_for(c["id"]) for c in columns}

    # ── 列布局 ──
    C = len(columns)
    time_w = 56.0
    desc_w = max(96.0, min(150.0, 640.0 / C))
    bar_w = 30.0
    unit_w = desc_w + bar_w
    total_w = time_w + unit_w * C
    x_units = [time_w + unit_w * k for k in range(C)]

    # ── 行高：等高基础 + 保证文字放得下 ──
    fs_body = 9.0
    heights = [36.0] * n
    for c in columns:
        for start, span in col_groups[c["id"]]:
            desc = time_rows[start]["cells"][c["id"]]["desc"] or "—"
            lines = _wrap(desc, desc_w - 12, fs_body)
            need = len(lines) * fs_body * PT2U * 1.45 + 10
            cur = sum(heights[start:start + span])
            if cur < need:
                add = (need - cur) / span
                for k in range(start, start + span):
                    heights[k] += add

    title_h, info_h, head1_h, head2_h = 44.0, 28.0, 30.0, 22.0
    stats_title_h, stats_head_h, stats_row_h = 30.0, 26.0, 26.0
    total_h = (title_h + info_h * 2 + head1_h + head2_h + sum(heights)
               + stats_title_h + stats_head_h + stats_row_h * (C + 1))

    fig = plt.figure(figsize=(total_w / 100.0, total_h / 100.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-1, total_w + 1)
    ax.set_ylim(total_h + 1, -1)
    ax.axis("off")

    y = 0.0
    _cell(ax, 0, y, total_w, title_h, "联合作业分析图", fontsize=15, bold=True)
    y += title_h

    # 信息区 行1: 作业名称 | 值 | 操作者 | 值
    k_w = 84.0
    v1_w = total_w * 0.45
    _cell(ax, 0, y, k_w, info_h, "作业名称", fill=LABEL_BG, bold=True)
    _cell(ax, k_w, y, v1_w, info_h, task_name)
    _cell(ax, k_w + v1_w, y, k_w, info_h, "操作者", fill=LABEL_BG, bold=True)
    _cell(ax, k_w * 2 + v1_w, y, total_w - k_w * 2 - v1_w, info_h, operator)
    y += info_h
    # 行2: 日期 | 值 | 作业地点 | 值 | 备注 | 值
    seg_v = (total_w - k_w * 3) / 3.0
    xx = 0.0
    for k_txt, v_txt in (("日期", date), ("作业地点", location), ("备注", remarks)):
        _cell(ax, xx, y, k_w, info_h, k_txt, fill=LABEL_BG, bold=True)
        xx += k_w
        _cell(ax, xx, y, seg_v, info_h, v_txt, wrap=True, fontsize=9)
        xx += seg_v
    y += info_h

    # 主表表头
    _cell(ax, 0, y, time_w, head1_h + head2_h, "时间/s", fill=HEADER_BG, bold=True, fontsize=9.5)
    for k, c in enumerate(columns):
        _cell(ax, x_units[k], y, unit_w, head1_h, c["name"], fill=HEADER_BG, bold=True, fontsize=9.5, wrap=True)
        _cell(ax, x_units[k], y + head1_h, desc_w, head2_h, "描述", fill=SUBHEADER_BG, bold=True, fontsize=8.5)
        _cell(ax, x_units[k] + desc_w, y + head1_h, bar_w, head2_h, "时间", fill=SUBHEADER_BG, bold=True, fontsize=8.5)
    y += head1_h + head2_h

    # 数据区
    row_y = [y]
    for h in heights:
        row_y.append(row_y[-1] + h)
    for i, r in enumerate(time_rows):
        _cell(ax, 0, row_y[i], time_w, heights[i], _fmt(r["time"]), fontsize=8.5)
    for k, c in enumerate(columns):
        for start, span in col_groups[c["id"]]:
            cell = time_rows[start]["cells"][c["id"]]
            gy, gh = row_y[start], sum(heights[start:start + span])
            _cell(ax, x_units[k], gy, desc_w, gh, cell["desc"] or "—",
                  fontsize=fs_body, ha="left", wrap=True)
            _cell(ax, x_units[k] + desc_w, gy, bar_w, gh,
                  fill=WORK_BG if cell["isWork"] else IDLE_BG)
    y = row_y[-1]

    # 统计汇总
    _cell(ax, 0, y, total_w, stats_title_h, "统计汇总", fill=AVG_BG, bold=True, fontsize=11.5)
    y += stats_title_h
    fr = [0.28, 0.18, 0.18, 0.18, 0.18]
    sw = [f * total_w for f in fr]
    sx = [sum(sw[:k]) for k in range(5)]
    for k, head in enumerate(["操作者", "周程/s", "工作时间/s", "空闲时间/s", "效率/%"]):
        _cell(ax, sx[k], y, sw[k], stats_head_h, head, fill=HEADER_BG, bold=True, fontsize=9.5)
    y += stats_head_h

    def _stat_row(label, work, idle, eff, bold_label=False, fill="white", eff_color=None):
        nonlocal y
        _cell(ax, sx[0], y, sw[0], stats_row_h, label, bold=bold_label, fontsize=9.5, fill=fill, wrap=True)
        _cell(ax, sx[1], y, sw[1], stats_row_h, _fmt(cycle), fontsize=9.5, fill=fill)
        _cell(ax, sx[2], y, sw[2], stats_row_h, _fmt(work), fontsize=9.5, fill=fill, color=GOOD)
        _cell(ax, sx[3], y, sw[3], stats_row_h, _fmt(idle), fontsize=9.5, fill=fill, color=IDLE_TXT)
        if eff_color is None:
            eff_color = GOOD if eff >= 80 else (BAD if eff < 50 else TEXT)
        _cell(ax, sx[4], y, sw[4], stats_row_h, f"{eff}%", bold=True, fontsize=9.5, fill=fill, color=eff_color)
        y += stats_row_h

    for c in columns:
        s = stats[c["id"]]
        _stat_row(c["name"], s["work"], s["idle"], s["eff"])
    _stat_row("平均", avg_work, avg_idle, avg_eff, bold_label=True, fill=AVG_BG, eff_color=TEXT)

    summary = {"周程时间(s)": round(cycle, 2), "平均效率(%)": avg_eff}
    for c in columns:
        summary[f"{c['name']}利用率(%)"] = stats[c["id"]]["eff"]

    return {"image_base64": figure_to_base64(fig), "summary": summary}
