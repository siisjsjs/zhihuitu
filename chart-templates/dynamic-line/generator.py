"""动态折线图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, to_matrix, to_string_list, ChartValidationError


def _to_frame_index(value, total: int) -> int:
    if value is None or str(value).strip() == "":
        return total
    try:
        frame = int(float(value))
    except (TypeError, ValueError):
        raise ChartValidationError("frame_index 必须是数字")
    if frame <= 0:
        return total
    if frame > total:
        raise ChartValidationError(f"frame_index 必须在 1 到 {total} 之间，0 表示显示全部")
    return frame


def generate(params: dict) -> dict:
    setup_chinese_font()
    x_values = np.array(to_float_list(params.get("x_values"), "x_values"), dtype=float)
    series_names = to_string_list(params.get("series_names"), "series_names")
    values = np.array(to_matrix(params.get("values"), "values"), dtype=float)

    if x_values.size < 2:
        raise ChartValidationError("至少需要 2 个时间点")
    if len(series_names) < 1:
        raise ChartValidationError("至少需要 1 个折线系列")
    if values.shape != (x_values.size, len(series_names)):
        raise ChartValidationError("values 行数必须等于 x_values 数量，列数必须等于 series_names 数量")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "时间"
    y_label = str(params.get("y_label", "")).strip() or "数值"
    legend_title = str(params.get("legend_title", "")).strip()
    source = str(params.get("source", "")).strip()
    frame_index = _to_frame_index(params.get("frame_index", 0), x_values.size)

    shown_x = x_values[:frame_index]
    shown_values = values[:frame_index, :]
    y_min = float(np.nanmin(values))
    y_max = float(np.nanmax(values))
    y_padding = max((y_max - y_min) * 0.08, 1)

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#17becf"]
    markers = ["o", "s", "^", "D", "v", "P", "X"]

    fig, ax = plt.subplots(figsize=(10, 7), facecolor="#f8f9fa")
    ax.set_facecolor("white")

    highlight_name = "中国" if any("中国" in name for name in series_names) else ""
    for idx, series_name in enumerate(series_names):
        line_width = 2.5 if highlight_name and highlight_name in series_name else 2
        ax.plot(
            shown_x,
            shown_values[:, idx],
            color=colors[idx % len(colors)],
            linestyle="-",
            linewidth=line_width,
            marker=markers[idx % len(markers)],
            markersize=5,
            markeredgecolor="white",
            markeredgewidth=1,
            label=series_name,
        )

    if source:
        ax.text(0.02, 0.03, source, transform=ax.transAxes, fontsize=8, color="#666666", ha="left", va="bottom")

    ax.set_title(title if title else "动态折线图", fontsize=16, pad=20, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=12, labelpad=10)
    ax.set_ylabel(y_label, fontsize=12, labelpad=10)
    ax.set_xlim(float(x_values.min()) - 0.5, float(x_values.max()) + 0.5)
    ax.set_ylim(y_min - y_padding, y_max + y_padding)
    ax.grid(True, linestyle="--", alpha=0.7, color="#d0d0d0")
    ax.legend(title=legend_title if legend_title else None, loc="upper right", fontsize=10, framealpha=0.9)
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")
    fig.tight_layout()

    latest_values = shown_values[-1, :]
    max_idx = int(np.nanargmax(latest_values))
    min_idx = int(np.nanargmin(latest_values))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "时间点数": int(x_values.size),
            "当前显示点数": int(frame_index),
            "系列数": len(series_names),
            "当前最高系列": series_names[max_idx],
            "当前最高值": round(float(latest_values[max_idx]), 4),
            "当前最低系列": series_names[min_idx],
            "当前最低值": round(float(latest_values[min_idx]), 4),
        },
    }
