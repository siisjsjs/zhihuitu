"""堆积面积图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, to_matrix, to_string_list, ChartValidationError


def _is_enabled(value, default: bool = True) -> bool:
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip() not in {"0", "false", "False", "否", "不"}


def generate(params: dict) -> dict:
    setup_chinese_font()
    x_values = np.array(to_float_list(params.get("x_values"), "x_values"), dtype=float)
    series_names = to_string_list(params.get("series_names"), "series_names")
    values = np.array(to_matrix(params.get("values"), "values"), dtype=float)

    if x_values.size < 2:
        raise ChartValidationError("至少需要 2 个时间点")
    if len(series_names) < 2:
        raise ChartValidationError("至少需要 2 个堆积系列")
    if values.shape != (x_values.size, len(series_names)):
        raise ChartValidationError("values 行数必须等于 x_values 数量，列数必须等于 series_names 数量")
    if np.any(values < 0):
        raise ChartValidationError("values 不能包含负数")

    totals = values.sum(axis=1)
    if np.any(totals <= 0):
        raise ChartValidationError("每个时间点的合计值必须大于 0")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "时间"
    y_label = str(params.get("y_label", "")).strip()
    legend_title = str(params.get("legend_title", "")).strip()
    source = str(params.get("source", "")).strip()
    show_total_labels = _is_enabled(params.get("show_total_labels"), True)
    normalize_percent = _is_enabled(params.get("normalize_percent"), True)

    plot_values = values / totals[:, None] * 100 if normalize_percent else values
    y_axis_label = y_label or ("占比(%)" if normalize_percent else "数值")

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#8dd3c7", "#ffffb3", "#bebada", "#fb8072", "#80b1d3", "#fdb462", "#b3de69"]
    ax.stackplot(
        x_values,
        plot_values.T,
        labels=series_names,
        colors=[colors[idx % len(colors)] for idx in range(len(series_names))],
        alpha=0.85,
    )

    if show_total_labels:
        label_y = 102 if normalize_percent else float(np.max(totals)) * 1.02
        for idx, x_value in enumerate(x_values):
            x_label_text = int(x_value) if float(x_value).is_integer() else x_value
            ax.text(
                x_value,
                label_y,
                f"总计:{totals[idx]:,.0f}",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                bbox={"facecolor": "white", "alpha": 0.7, "boxstyle": "round,pad=0.3", "edgecolor": "none"},
            )

    ax.set_title(title if title else "堆积面积图", fontsize=16, pad=24, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=14, labelpad=10)
    ax.set_ylabel(y_axis_label, fontsize=14, labelpad=10)
    ax.set_xticks(x_values)
    ax.tick_params(axis="x", labelsize=11)
    ax.tick_params(axis="y", labelsize=11)
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.legend(title=legend_title if legend_title else None, loc="upper right", fontsize=10, frameon=True, framealpha=0.9)
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")

    if normalize_percent:
        ax.set_ylim(0, 108 if show_total_labels else 100)
    else:
        ax.set_ylim(0, float(np.max(totals)) * (1.12 if show_total_labels else 1.05))
    if source:
        fig.text(0.5, 0.02, source, ha="center", fontsize=10, color="gray")
    fig.tight_layout(rect=(0, 0.03 if source else 0, 1, 1))

    last_values = values[-1, :]
    last_total = float(totals[-1])
    max_idx = int(np.argmax(last_values))
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "时间点数": int(x_values.size),
            "系列数": len(series_names),
            "最新总计": round(last_total, 4),
            "最新最大系列": series_names[max_idx],
            "最新最大值": round(float(last_values[max_idx]), 4),
            "最新最大占比": round(float(last_values[max_idx] / last_total * 100), 2),
        },
    }
