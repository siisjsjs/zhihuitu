"""饼图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, to_string_list, ChartValidationError


def _to_highlight_index(value, total: int) -> int:
    if value is None or str(value).strip() == "":
        return 0
    try:
        index = int(float(value))
    except (TypeError, ValueError):
        raise ChartValidationError("highlight_index 必须是数字")
    if index < 0 or index > total:
        raise ChartValidationError(f"highlight_index 必须在 0 到 {total} 之间")
    return index


def generate(params: dict) -> dict:
    setup_chinese_font()
    categories = to_string_list(params.get("categories"), "categories")
    values = np.array(to_float_list(params.get("values"), "values"), dtype=float)

    if len(categories) != values.size:
        raise ChartValidationError("categories 与 values 长度必须一致")
    if values.size < 2:
        raise ChartValidationError("至少需要 2 个分类")
    if np.any(values < 0):
        raise ChartValidationError("values 不能包含负数")
    total = float(values.sum())
    if total <= 0:
        raise ChartValidationError("values 总和必须大于 0")

    title = str(params.get("title", "")).strip()
    legend_title = str(params.get("legend_title", "")).strip() or "分类"
    highlight_index = _to_highlight_index(params.get("highlight_index", 0), len(categories))
    explode = [0.1 if highlight_index == idx + 1 else 0 for idx in range(len(categories))]

    palette = [
        "#FF9999", "#66B3FF", "#99FF99", "#FFCC99", "#C2C2F0",
        "#FBBF24", "#A7F3D0", "#F9A8D4", "#93C5FD", "#DDD6FE",
    ]
    colors = [palette[idx % len(palette)] for idx in range(len(categories))]

    fig, ax = plt.subplots(figsize=(10, 7))
    wedges, _texts, autotexts = ax.pie(
        values,
        explode=explode,
        labels=categories,
        colors=colors,
        autopct="%.1f%%",
        shadow=True,
        startangle=90,
        pctdistance=0.85,
        radius=0.72,
        center=(-0.28, 0),
        wedgeprops={"edgecolor": "black", "linewidth": 1},
        textprops={"fontsize": 12},
    )

    for autotext in autotexts:
        autotext.set_fontweight("bold")
        autotext.set_color("darkblue")

    ax.set_title(title if title else "分类占比分析", fontsize=16, fontweight="bold", pad=20)
    ax.legend(
        wedges,
        categories,
        title=legend_title,
        loc="upper right",
        bbox_to_anchor=(0.98, 0.92),
        fontsize=10,
        frameon=True,
        shadow=True,
    )
    ax.axis("equal")
    ax.set_frame_on(True)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")
    fig.tight_layout()

    max_idx = int(np.argmax(values))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "分类数": int(values.size),
            "总计": round(total, 4),
            "最大分类": categories[max_idx],
            "最大值": round(float(values[max_idx]), 4),
            "最大占比": round(float(values[max_idx] / total * 100), 2),
        },
    }
