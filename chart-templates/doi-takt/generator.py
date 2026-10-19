"""工序 DOI 节拍图生成器

- 蓝色柱:各工序 DOI(单件作业时间)
- 橙色水平线:节拍时间 TT
- 仅在 TT 线右端标注其数值,模仿用户提供的样式
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import (
    setup_chinese_font,
    figure_to_base64,
    to_string_list,
    to_float_list,
    to_positive_float,
    ChartValidationError,
)


BAR_COLOR = "#4F81BD"
TT_COLOR = "#F39C3F"


def generate(params: dict) -> dict:
    setup_chinese_font()

    process_names = to_string_list(params.get("process_names"), "process_names")
    doi_values = to_float_list(params.get("doi_values"), "doi_values")
    takt_time = to_positive_float(params.get("takt_time"), "takt_time")

    if len(process_names) != len(doi_values):
        raise ChartValidationError("process_names 与 doi_values 长度必须一致")
    if len(doi_values) < 2:
        raise ChartValidationError("至少需要 2 个工序")

    title = str(params.get("title", "")).strip() or "各工序 DOI 节拍图"
    doi_label = str(params.get("doi_label", "")).strip() or "DOI(秒)"
    takt_label = str(params.get("takt_label", "")).strip() or "TT(秒)"
    y_label = str(params.get("y_label", "")).strip() or "时间(秒)"

    n = len(process_names)
    values = np.array(doi_values, dtype=float)

    fig_width = max(10, n * 0.5 + 2)
    fig, ax = plt.subplots(figsize=(fig_width, 6.5))

    x = np.arange(n)
    bar_width = 0.6
    ax.bar(x, values, width=bar_width, color=BAR_COLOR, edgecolor=BAR_COLOR, label=doi_label)

    y_top = max(float(values.max()), takt_time) * 1.10
    y_top = max(y_top, 1.0)
    ax.set_ylim(0, y_top)

    ax.axhline(y=takt_time, color=TT_COLOR, linewidth=2.2, label=takt_label)
    ax.text(
        n - 0.5,
        takt_time + y_top * 0.012,
        f"{takt_time:.2f}",
        color="#222",
        fontsize=11,
        fontweight="bold",
        ha="right",
        va="bottom",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(process_names, rotation=90, fontsize=10)
    ax.set_xlim(-0.7, n - 0.3)

    y_max_int = int(np.ceil(y_top))
    ax.set_yticks(np.arange(0, y_max_int + 1, 1))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.2f}"))
    ax.set_ylabel(y_label, fontsize=11)

    ax.set_title(title, fontsize=15, fontweight="bold", pad=14)

    ax.grid(False)
    ax.spines["top"].set_visible(True)
    ax.spines["right"].set_visible(True)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_edgecolor("#888")

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.32),
        ncol=2,
        frameon=False,
        fontsize=11,
        handlelength=2.6,
    )

    fig.tight_layout()

    over_idx = [i for i, v in enumerate(values) if v > takt_time]
    max_i = int(np.argmax(values))
    min_i = int(np.argmin(values))

    summary = {
        "工序数": n,
        "节拍时间 TT": round(takt_time, 4),
        "最大 DOI": f"{values[max_i]:.2f} ({process_names[max_i]})",
        "最小 DOI": f"{values[min_i]:.2f} ({process_names[min_i]})",
        "平均 DOI": round(float(values.mean()), 2),
        "超 TT 工序数": len(over_idx),
        "超 TT 工序": ", ".join(process_names[i] for i in over_idx) if over_idx else "无",
    }

    return {
        "image_base64": figure_to_base64(fig),
        "summary": summary,
    }
