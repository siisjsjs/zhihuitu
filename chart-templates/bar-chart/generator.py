"""柱状图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from _utils import setup_chinese_font, figure_to_base64, to_float_list, to_string_list, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    categories = to_string_list(params.get("categories"), "categories")
    values = np.array(to_float_list(params.get("values"), "values"), dtype=float)
    if len(categories) != values.size:
        raise ChartValidationError("categories 与 values 长度必须一致")
    if values.size < 2:
        raise ChartValidationError("至少需要 2 个分类")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "分类"
    y_label = str(params.get("y_label", "")).strip() or "数值"
    show_value_labels = str(params.get("show_value_labels", "1")).strip() != "0"

    fig, ax = plt.subplots(figsize=(10, 7))
    x = np.arange(len(categories))
    colors = ["#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#22d3ee", "#fb7185"]
    bars = ax.bar(
        x,
        values,
        color=[colors[idx % len(colors)] for idx in range(len(categories))],
        edgecolor="white",
        linewidth=1,
        width=0.65,
    )

    if show_value_labels:
        offset = max((float(values.max()) - float(values.min())) * 0.02, abs(float(values.max())) * 0.01, 1)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + offset if value >= 0 else value - offset,
                f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}",
                ha="center",
                va="bottom" if value >= 0 else "top",
                fontsize=10,
                fontweight="bold",
            )

    ax.set_title(title if title else "柱状图", fontsize=16, pad=20, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=14, labelpad=10)
    ax.set_ylabel(y_label, fontsize=14, labelpad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=20, ha="right")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", linestyle="--", alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")
    fig.tight_layout()

    max_idx = int(np.argmax(values))
    min_idx = int(np.argmin(values))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "分类数": int(values.size),
            "总计": round(float(values.sum()), 4),
            "最大分类": categories[max_idx],
            "最大值": round(float(values[max_idx]), 4),
            "最小分类": categories[min_idx],
            "最小值": round(float(values[min_idx]), 4),
        },
    }
