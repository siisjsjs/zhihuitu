"""热力图生成器（matplotlib，不依赖 seaborn）"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from _utils import setup_chinese_font, figure_to_base64, to_matrix, to_string_list, ChartValidationError


def _demo_data() -> tuple[list[str], list[str], np.ndarray]:
    row_labels = ["站A", "站B", "站C", "站D", "站E", "站F", "站G", "站H"]
    col_labels = [f"{m}月" for m in range(1, 13)]
    values = np.array(
        [
            [45, 50, 65, 90, 120, 180, 220, 210, 160, 95, 60, 55],
            [30, 35, 50, 85, 110, 160, 190, 185, 140, 80, 45, 35],
            [55, 60, 75, 100, 135, 200, 240, 230, 175, 110, 75, 65],
            [25, 30, 45, 75, 100, 140, 170, 165, 125, 70, 40, 30],
            [60, 65, 80, 110, 145, 210, 250, 245, 190, 120, 85, 70],
            [40, 45, 60, 85, 115, 170, 200, 195, 150, 90, 55, 50],
            [35, 40, 55, 80, 105, 150, 180, 175, 135, 75, 50, 40],
            [50, 55, 70, 95, 130, 190, 230, 225, 180, 105, 70, 60],
        ],
        dtype=float,
    )
    return row_labels, col_labels, values


def _parse_bool(value, default: bool) -> bool:
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip() not in {"0", "false", "False", "否"}


def _optional_float(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _effective_color_limits(matrix: np.ndarray, vmin, vmax) -> tuple[float, float]:
    """与数据不交叠或过窄的 vmin/vmax 会导致整块单色；此时回退为矩阵 min/max。"""
    auto_lo = float(np.min(matrix))
    auto_hi = float(np.max(matrix))
    if not np.isfinite(auto_lo) or not np.isfinite(auto_hi) or auto_hi <= auto_lo + 1e-15:
        return auto_lo, auto_hi

    vmin_f = _optional_float(vmin)
    vmax_f = _optional_float(vmax)
    vmin_u = auto_lo if vmin_f is None else vmin_f
    vmax_u = auto_hi if vmax_f is None else vmax_f

    # 用户上下界与数据区间无交集，或 vmax<=vmin → 整张图映射塌缩
    if vmax_u <= vmin_u or vmax_u < auto_lo or vmin_u > auto_hi:
        return auto_lo, auto_hi

    return vmin_u, vmax_u


def generate(params: dict) -> dict:
    setup_chinese_font()
    row_labels = to_string_list(params.get("row_labels"), "row_labels")
    col_labels = to_string_list(params.get("column_labels"), "column_labels")
    raw_values = params.get("values")

    matrix: np.ndarray
    if raw_values is None or (isinstance(raw_values, list) and len(raw_values) == 0) or (isinstance(raw_values, str) and not str(raw_values).strip()):
        matrix = np.array([])
    else:
        matrix = np.array(to_matrix(raw_values, "values"), dtype=float)

    using_demo = False
    if matrix.size == 0 or row_labels == [] or col_labels == []:
        row_labels, col_labels, matrix = _demo_data()
        using_demo = True
    elif matrix.shape != (len(row_labels), len(col_labels)):
        raise ChartValidationError("values 行数须等于气象站数量，列数须等于月份数量")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip() or "月份"
    y_label = str(params.get("y_label", "")).strip() or "气象站"
    cbar_label = str(params.get("cbar_label", "")).strip() or "数值"
    cmap_name = str(params.get("cmap", "YlGnBu")).strip() or "YlGnBu"
    show_annot = _parse_bool(params.get("show_annot"), True)
    vmin = params.get("vmin")
    vmax = params.get("vmax")
    vmin_u, vmax_u = _effective_color_limits(matrix, vmin, vmax)

    fig, ax = plt.subplots(figsize=(10, 7))
    cmap = plt.get_cmap(cmap_name)
    norm = mcolors.Normalize(vmin=vmin_u, vmax=vmax_u)
    mesh = ax.pcolormesh(
        np.arange(matrix.shape[1] + 1),
        np.arange(matrix.shape[0] + 1),
        matrix,
        cmap=cmap,
        norm=norm,
        shading="flat",
        edgecolors="white",
        linewidths=0.6,
    )
    cbar = fig.colorbar(mesh, ax=ax, shrink=0.82, pad=0.02, aspect=28)
    cbar.ax.set_ylabel(cbar_label, fontsize=12, labelpad=12)
    cbar.ax.tick_params(labelsize=10)

    ax.set_xticks(np.arange(matrix.shape[1]) + 0.5)
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=10)
    ax.set_yticks(np.arange(matrix.shape[0]) + 0.5)
    ax.set_yticklabels(row_labels, rotation=0, fontsize=10)
    ax.invert_yaxis()

    ax.set_title(title if title else "热力图", fontsize=16, fontweight="bold", pad=16)
    ax.set_xlabel(x_label, fontsize=13, labelpad=8)
    ax.set_ylabel(y_label, fontsize=13, labelpad=8)
    ax.set_xlim(0, matrix.shape[1])
    ax.set_ylim(matrix.shape[0], 0)
    ax.grid(False)

    if show_annot:
        all_int = bool(np.all(np.mod(matrix, 1) < 1e-9))
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                v = matrix[i, j]
                txt = f"{int(round(v))}" if all_int else f"{v:.1f}"
                ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center", fontsize=9, color="#0f172a")

    for spine in ax.spines.values():
        spine.set_linewidth(1)
        spine.set_edgecolor("#64748b")

    fig.tight_layout()

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "行数": int(matrix.shape[0]),
            "列数": int(matrix.shape[1]),
            "最小值": round(float(matrix.min()), 4),
            "最大值": round(float(matrix.max()), 4),
            "均值": round(float(matrix.mean()), 4),
            "使用演示数据": using_demo,
        },
    }
