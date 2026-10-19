"""甘特图生成器（服务端 matplotlib 静态出图）"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

DEFAULT_PHASE_COLORS = [
    "#4472C4", "#548235", "#BF8F00", "#C00000", "#7030A0", "#2E75B6",
    "#ED7D31", "#70AD47", "#FFC000", "#5B9BD5",
]


def _hex_to_rgb(hex_color: str):
    s = str(hex_color).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return None
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _lighten(hex_color: str, amount: float) -> str:
    rgb = _hex_to_rgb(hex_color)
    if rgb is None:
        return "#9ca3af"
    r, g, b = (round(c + (255 - c) * amount) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, amount: float = 0.25) -> str:
    rgb = _hex_to_rgb(hex_color)
    if rgb is None:
        return "#374151"
    r, g, b = (round(c * (1 - amount)) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _to_number(value, default, field_desc):
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ChartValidationError(f"{field_desc} 必须是数字") from exc


def _parse_phases(raw):
    if not isinstance(raw, list) or not raw:
        raise ChartValidationError("phases 阶段列表不能为空，至少需要一个阶段")
    phases = []
    for i, p in enumerate(raw):
        if not isinstance(p, dict):
            raise ChartValidationError(f"第 {i + 1} 个阶段必须是对象")
        name = str(p.get("name") or f"阶段{i + 1}").strip()
        color = str(p.get("color") or DEFAULT_PHASE_COLORS[i % len(DEFAULT_PHASE_COLORS)]).strip()
        if _hex_to_rgb(color) is None:
            color = DEFAULT_PHASE_COLORS[i % len(DEFAULT_PHASE_COLORS)]
        start = _to_number(p.get("startMonth"), 1, f"阶段「{name}」的 startMonth")
        duration = _to_number(p.get("duration"), 1, f"阶段「{name}」的 duration")
        if duration <= 0:
            raise ChartValidationError(f"阶段「{name}」的 duration 必须大于 0")
        tasks = []
        for j, t in enumerate(p.get("tasks") or []):
            if not isinstance(t, dict):
                raise ChartValidationError(f"阶段「{name}」的第 {j + 1} 个任务必须是对象")
            t_name = str(t.get("name") or f"任务{j + 1}").strip()
            t_start = _to_number(t.get("startMonth"), start, f"任务「{t_name}」的 startMonth")
            t_dur = _to_number(t.get("duration"), 1, f"任务「{t_name}」的 duration")
            if t_dur <= 0:
                raise ChartValidationError(f"任务「{t_name}」的 duration 必须大于 0")
            tasks.append({"name": t_name, "start": t_start, "duration": t_dur})
        phases.append({"name": name, "color": color, "start": start,
                       "duration": duration, "tasks": tasks})
    return phases


def generate(params: dict) -> dict:
    setup_chinese_font()
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")

    title = str(params.get("title") or "项目甘特图").strip()
    phases = _parse_phases(params.get("phases"))

    months_raw = params.get("months")
    months = [str(m).strip() for m in months_raw] if isinstance(months_raw, list) else []

    # 时间轴长度取月份标签数与所有条形最远右端的较大者，缺标签时自动补默认月名
    max_end = max(
        [ph["start"] + ph["duration"] for ph in phases]
        + [t["start"] + t["duration"] for ph in phases for t in ph["tasks"]]
    )
    n_months = max(len(months), int(math.ceil(max_end - 1 + 1e-9)), 1)
    while len(months) < n_months:
        months.append(f"{len(months) + 1}月")

    # 自上而下逐行排列：阶段行 + 其任务行
    rows = []  # (label, start, duration, color, is_phase)
    for ph in phases:
        rows.append((ph["name"], ph["start"], ph["duration"], ph["color"], True))
        for t in ph["tasks"]:
            rows.append((t["name"], t["start"], t["duration"], ph["color"], False))
    total_rows = len(rows)

    fig_w = max(10.0, 0.85 * n_months + 4.0)
    fig_h = max(3.2, 0.38 * total_rows + 1.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    for i, (label, start, duration, color, is_phase) in enumerate(rows):
        y = total_rows - 1 - i
        left = start - 1
        if is_phase:
            ax.axhspan(y - 0.5, y + 0.5, color=color, alpha=0.07, zorder=1)
            ax.barh(y, duration, left=left, height=0.62,
                    color=color, edgecolor=_darken(color), linewidth=1.0, zorder=3)
        else:
            ax.barh(y, duration, left=left, height=0.42,
                    color=_lighten(color, 0.62), edgecolor=_lighten(color, 0.2),
                    linewidth=0.9, zorder=3)

    # 竖向月份网格线（整数月边界）
    for x in range(0, n_months + 1):
        ax.axvline(x, color="#c8cdd4", linewidth=0.8, linestyle="--", zorder=2)

    ax.set_xlim(0, n_months)
    ax.set_ylim(-0.7, total_rows - 0.3)
    ax.set_xticks([i + 0.5 for i in range(n_months)])
    ax.set_xticklabels(months, fontsize=10)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=6)
    ax.tick_params(axis="y", length=0, pad=4)

    ax.set_yticks([total_rows - 1 - i for i in range(total_rows)])
    ax.set_yticklabels([r[0] if r[4] else "    " + r[0] for r in rows], fontsize=10)
    for tick_label, row in zip(ax.get_yticklabels(), rows):
        if row[4]:
            tick_label.set_fontweight("bold")
            tick_label.set_color(_darken(row[3], 0.3))
        else:
            tick_label.set_color("#374151")

    for spine in ("left", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.spines["top"].set_color("#9ca3af")

    if title:
        ax.set_title(title, fontsize=15, fontweight="bold", pad=26, color="#1f2937")

    task_count = sum(len(ph["tasks"]) for ph in phases)
    min_start = min(
        [ph["start"] for ph in phases]
        + [t["start"] for ph in phases for t in ph["tasks"]]
    )
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "阶段数": len(phases),
            "任务总数": task_count,
            "总工期跨度(月)": round(float(max_end - min_start), 2),
        },
    }
