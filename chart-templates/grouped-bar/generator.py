"""分组柱状图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from _utils import setup_chinese_font, figure_to_base64, to_matrix, to_string_list, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    x_labels = to_string_list(params.get("x_labels"), "x_labels")
    series_names = to_string_list(params.get("series_names"), "series_names")
    values = np.array(to_matrix(params.get("values"), "values"), dtype=float)
    if len(x_labels) < 2:
        raise ChartValidationError("至少需要 2 个横轴分类")
    if len(series_names) < 2:
        raise ChartValidationError("至少需要 2 个分组系列")
    if values.shape != (len(x_labels), len(series_names)):
        raise ChartValidationError("values 行数必须等于 x_labels 数量，列数必须等于 series_names 数量")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "分类"
    y_label = str(params.get("y_label", "")).strip() or "数值"
    legend_title = str(params.get("legend_title", "")).strip()
    show_value_labels = str(params.get("show_value_labels", "0")).strip() != "0"

    fig, ax = plt.subplots(figsize=(10, 7))
    x = np.arange(len(x_labels))
    group_width = 0.78
    bar_width = group_width / len(series_names)
    colors = ["#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#22d3ee"]

    for idx, series_name in enumerate(series_names):
        offset = (idx - (len(series_names) - 1) / 2) * bar_width
        bars = ax.bar(
            x + offset,
            values[:, idx],
            width=bar_width * 0.9,
            label=series_name,
            color=colors[idx % len(colors)],
            edgecolor="white",
            linewidth=1,
        )
        if show_value_labels:
            for bar, value in zip(bars, values[:, idx]):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value,
                    f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    ax.set_title(title if title else "分组柱状图", fontsize=16, pad=20, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=14, labelpad=10)
    ax.set_ylabel(y_label, fontsize=14, labelpad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=15, ha="right")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.legend(title=legend_title if legend_title else None, loc="upper right", fontsize=10, frameon=True, framealpha=0.9)
    ax.grid(axis="y", linestyle="--", alpha=0.55)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")
    fig.tight_layout()

    totals = values.sum(axis=1)
    max_idx = int(np.argmax(totals))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "横轴分类数": len(x_labels),
            "系列数": len(series_names),
            "总计": round(float(values.sum()), 4),
            "最高分类": x_labels[max_idx],
            "最高分类总值": round(float(totals[max_idx]), 4),
        },
    }
