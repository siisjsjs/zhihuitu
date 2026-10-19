"""基础折线图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, to_matrix, to_string_list, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    x_values = np.array(to_float_list(params.get("x_values"), "x_values"), dtype=float)
    series_names = to_string_list(params.get("series_names"), "series_names")
    values = np.array(to_matrix(params.get("values"), "values"), dtype=float)
    if x_values.size < 2:
        raise ChartValidationError("至少需要 2 个横轴点")
    if len(series_names) < 1:
        raise ChartValidationError("至少需要 1 个折线系列")
    if values.shape != (x_values.size, len(series_names)):
        raise ChartValidationError("values 行数必须等于 x_values 数量，列数必须等于 series_names 数量")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "时间"
    y_label = str(params.get("y_label", "")).strip() or "数值"
    legend_title = str(params.get("legend_title", "")).strip()
    source = str(params.get("source", "")).strip()

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#2563eb", "#f97316", "#16a34a", "#dc2626", "#7c3aed", "#0891b2"]
    markers = ["o", "s", "^", "D", "v", "P"]
    for idx, series_name in enumerate(series_names):
        ax.plot(
            x_values,
            values[:, idx],
            color=colors[idx % len(colors)],
            linewidth=2.2,
            marker=markers[idx % len(markers)],
            markersize=5,
            markeredgecolor="white",
            markeredgewidth=1,
            label=series_name,
        )

    y_min = float(np.nanmin(values))
    y_max = float(np.nanmax(values))
    padding = max((y_max - y_min) * 0.08, 1)
    ax.set_title(title if title else "折线图", fontsize=16, pad=20, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=14, labelpad=10)
    ax.set_ylabel(y_label, fontsize=14, labelpad=10)
    ax.set_xlim(float(x_values.min()) - 0.5, float(x_values.max()) + 0.5)
    ax.set_ylim(y_min - padding, y_max + padding)
    ax.grid(True, linestyle="--", alpha=0.55)
    if len(series_names) > 1:
        ax.legend(title=legend_title if legend_title else None, loc="upper right", fontsize=10, frameon=True, framealpha=0.9)
    if source:
        fig.text(0.5, 0.02, source, ha="center", fontsize=10, color="gray")
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")
    fig.tight_layout(rect=(0, 0.03 if source else 0, 1, 1))

    latest_values = values[-1, :]
    max_idx = int(np.nanargmax(latest_values))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "横轴点数": int(x_values.size),
            "系列数": len(series_names),
            "最新最高系列": series_names[max_idx],
            "最新最高值": round(float(latest_values[max_idx]), 4),
            "整体最大值": round(float(y_max), 4),
            "整体最小值": round(float(y_min), 4),
        },
    }
