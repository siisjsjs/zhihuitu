"""密度散点图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from _utils import setup_chinese_font, figure_to_base64, to_float_list, ChartValidationError


def _parse_number(value, field_name: str, default: float) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ChartValidationError(f"{field_name} 必须是数字") from exc


def _parse_excel_text(text: str) -> tuple[list[float], list[float]]:
    x_values: list[float] = []
    y_values: list[float] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = [part for part in re.split(r"[\t,，;；\s]+", line) if part]
        if len(parts) < 2:
            continue
        try:
            x = float(parts[0])
            y = float(parts[1])
        except ValueError:
            # Allow a header row such as "年龄 消费金额".
            continue
        x_values.append(x)
        y_values.append(y)
    return x_values, y_values


def _generate_sample_data(sample_size: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(42)
    group_sizes = [
        int(sample_size * 0.2),
        int(sample_size * 0.3),
        int(sample_size * 0.3),
    ]
    group_sizes.append(sample_size - sum(group_sizes))

    ages = np.concatenate([
        rng.integers(18, 26, size=group_sizes[0]),
        rng.integers(26, 36, size=group_sizes[1]),
        rng.integers(36, 46, size=group_sizes[2]),
        rng.integers(46, 61, size=group_sizes[3]),
    ]).astype(float)
    amounts = np.concatenate([
        rng.normal(1400, 400, group_sizes[0]),
        rng.normal(2500, 600, group_sizes[1]),
        rng.normal(3000, 600, group_sizes[2]),
        rng.normal(2000, 600, group_sizes[3]),
    ])
    amounts = np.clip(amounts, 0, 5000)

    if sample_size >= 20:
        zero_indices = rng.choice(sample_size, max(1, sample_size // 200), replace=False)
        amounts[zero_indices] = 0
        available = np.setdiff1d(np.arange(sample_size), zero_indices)
        high_indices = rng.choice(available, max(1, sample_size // 300), replace=False)
        amounts[high_indices] = rng.uniform(4500, 5000, size=high_indices.size)
    return ages, np.round(amounts, 2)


def generate(params: dict) -> dict:
    setup_chinese_font()
    data_text = str(params.get("data_text", "")).strip()
    if data_text:
        x_values, y_values = _parse_excel_text(data_text)
    else:
        x_values = to_float_list(params.get("x_values"), "x_values") if params.get("x_values") else []
        y_values = to_float_list(params.get("y_values"), "y_values") if params.get("y_values") else []

    if x_values and y_values:
        x = np.array(x_values, dtype=float)
        y = np.array(y_values, dtype=float)
    else:
        # 无 Excel/无粘贴数据时使用固定规模的演示分布，保证模板预览可用；不向用户暴露“样本量”参数
        demo_size = 1000
        x, y = _generate_sample_data(demo_size)

    if x.size != y.size:
        raise ChartValidationError("x_values 与 y_values 长度必须一致")
    if x.size < 20:
        raise ChartValidationError("密度散点图至少需要 20 个数据点")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "X"
    y_label = str(params.get("y_label", "")).strip() or "Y"
    bins = int(max(10, min(80, _parse_number(params.get("bins"), "bins", 35))))
    point_alpha = max(0.02, min(0.5, _parse_number(params.get("point_alpha"), "point_alpha", 0.12)))

    fig, ax = plt.subplots(figsize=(10, 7))
    hist = ax.hist2d(x, y, bins=bins, cmap="Blues", alpha=0.82)
    counts, x_edges, y_edges = hist[0], hist[1], hist[2]
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    if np.count_nonzero(counts) > 3:
        levels = np.linspace(0, counts.max(), 6)[1:]
        ax.contour(x_centers, y_centers, counts.T, levels=levels, colors="#1d4ed8", linewidths=0.7, alpha=0.75)

    ax.scatter(x, y, alpha=point_alpha, color="#0f172a", s=10, edgecolors="none")
    cbar = fig.colorbar(hist[3], ax=ax, pad=0.02)
    cbar.set_label("数据密度", fontsize=12)
    cbar.ax.tick_params(labelsize=10)

    ax.set_title(title if title else "密度散点图", fontsize=16, pad=20, fontweight="bold")
    ax.set_xlabel(x_label, fontsize=14, labelpad=10)
    ax.set_ylabel(y_label, fontsize=14, labelpad=10)
    ax.grid(linestyle="--", alpha=0.55, color="gray")
    ax.legend(
        handles=[
            Patch(facecolor="#93c5fd", edgecolor="#1d4ed8", alpha=0.82, label="数据分布密度"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor="#0f172a", markersize=6, alpha=0.5, label="数据点"),
        ],
        loc="upper right",
        fontsize=10,
        frameon=True,
        framealpha=0.9,
    )
    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")
    fig.tight_layout()

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "样本数": int(x.size),
            "X均值": round(float(np.mean(x)), 4),
            "Y均值": round(float(np.mean(y)), 4),
            "X范围": f"{round(float(np.min(x)), 4)} - {round(float(np.max(x)), 4)}",
            "Y范围": f"{round(float(np.min(y)), 4)} - {round(float(np.max(y)), 4)}",
        },
    }
