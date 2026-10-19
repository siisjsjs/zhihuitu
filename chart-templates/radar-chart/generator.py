"""雷达图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_matrix, to_string_list, ChartValidationError


def _to_positive_number(value, field_name: str, default: float) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ChartValidationError(f"{field_name} 必须是数字") from exc
    if number <= 0:
        raise ChartValidationError(f"{field_name} 必须大于 0")
    return number


def generate(params: dict) -> dict:
    setup_chinese_font()
    dimensions = to_string_list(params.get("dimensions"), "dimensions")
    series_names = to_string_list(params.get("series_names"), "series_names")
    values = np.array(to_matrix(params.get("values"), "values"), dtype=float)

    if len(dimensions) < 3:
        raise ChartValidationError("至少需要 3 个维度")
    if len(series_names) < 1:
        raise ChartValidationError("至少需要 1 个评价对象")
    if values.shape != (len(series_names), len(dimensions)):
        raise ChartValidationError("values 行数必须等于 series_names 数量，列数必须等于 dimensions 数量")
    if np.any(values < 0):
        raise ChartValidationError("values 不能包含负数")

    max_score = _to_positive_number(params.get("max_score"), "max_score", 10)
    if np.any(values > max_score):
        raise ChartValidationError("values 不能大于 max_score")

    title = str(params.get("title", "")).strip()
    legend_title = str(params.get("legend_title", "")).strip()

    angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
    angles += angles[:1]
    colors = ["#FF5733", "#2563eb", "#22c55e", "#f59e0b", "#8b5cf6", "#06b6d4"]

    fig = plt.figure(figsize=(10, 7), facecolor="white")
    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor("white")

    for idx, series_name in enumerate(series_names):
        scores = values[idx].tolist()
        scores += scores[:1]
        ax.plot(
            angles,
            scores,
            color=colors[idx % len(colors)],
            linewidth=2.2,
            label=series_name,
            marker="o",
            markersize=5,
            markeredgecolor="white",
            markeredgewidth=1,
        )
        ax.fill(angles, scores, color=colors[idx % len(colors)], alpha=0.22)

    ax.set_thetagrids(np.degrees(angles[:-1]), dimensions, fontsize=12, fontweight="bold")
    ax.set_rlim(0, max_score)
    tick_step = max_score / 5
    ax.set_rticks([round(tick_step * idx, 2) for idx in range(0, 6)])
    ax.tick_params(axis="y", labelsize=10)
    ax.grid(True, color="#d1d5db", linewidth=1)
    ax.set_title(title if title else "雷达图", fontsize=16, fontweight="bold", pad=24)
    ax.legend(
        title=legend_title if legend_title else None,
        loc="upper right",
        bbox_to_anchor=(1.04, 1.04),
        fontsize=10,
        frameon=True,
        framealpha=0.9,
    )
    ax.spines["polar"].set_linewidth(1)
    ax.spines["polar"].set_edgecolor("#64748b")
    fig.tight_layout()

    totals = values.sum(axis=1)
    best_idx = int(np.argmax(totals))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "维度数": len(dimensions),
            "评价对象数": len(series_names),
            "综合最高对象": series_names[best_idx],
            "综合最高总分": round(float(totals[best_idx]), 4),
            "最高平均分": round(float(totals[best_idx] / len(dimensions)), 4),
        },
    }
