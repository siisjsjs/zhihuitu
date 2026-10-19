"""堆叠柱状图生成器"""
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
        raise ChartValidationError("至少需要 2 个堆叠系列")
    if values.shape != (len(x_labels), len(series_names)):
        raise ChartValidationError("values 行数必须等于 x_labels 数量，列数必须等于 series_names 数量")
    if np.any(values < 0):
        raise ChartValidationError("values 不能包含负数")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "分类"
    y_label = str(params.get("y_label", "")).strip() or "数值"
    legend_title = str(params.get("legend_title", "")).strip() or "系列"
    show_total_labels = str(params.get("show_total_labels", "1")).strip() != "0"

    totals = values.sum(axis=1)
    x = np.arange(len(x_labels))
    bottom = np.zeros(len(x_labels))
    palette = plt.get_cmap("Set3").colors

    fig, ax = plt.subplots(figsize=(10, 7))
    for idx, series_name in enumerate(series_names):
        ax.bar(
            x,
            values[:, idx],
            bottom=bottom,
            label=series_name,
            color=palette[idx % len(palette)],
            width=0.7,
            edgecolor="white",
            linewidth=1.5,
        )
        bottom += values[:, idx]

    if show_total_labels:
        label_offset = max(float(totals.max()) * 0.01, 1)
        for idx, total in enumerate(totals):
            ax.text(
                idx,
                total + label_offset,
                f"{total:,.0f}",
                ha="center",
                va="bottom",
                fontweight="bold",
                fontsize=10,
            )

    ax.set_title(title if title else "堆叠柱状图", fontsize=18, pad=20, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=14, labelpad=10)
    ax.set_ylabel(y_label, fontsize=14, labelpad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=30, ha="right")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.legend(
        title=legend_title,
        title_fontsize=12,
        fontsize=10,
        loc="upper left",
        frameon=True,
        shadow=True,
    )
    ax.grid(axis="y", linestyle="--", alpha=0.7, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")
    if totals.max() > 0:
        ax.set_ylim(0, totals.max() * 1.12)
    fig.tight_layout()

    max_idx = int(np.argmax(totals))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "横轴分类数": len(x_labels),
            "堆叠系列数": len(series_names),
            "总计": round(float(totals.sum()), 4),
            "最高分类": x_labels[max_idx],
            "最高分类总值": round(float(totals[max_idx]), 4),
        },
    }
