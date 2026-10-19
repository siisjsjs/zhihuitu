"""
图表模板共享工具函数
所有 generator.py 可 import 此模块使用公共功能
"""
from __future__ import annotations

import base64
import io
import os
from typing import Any, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


class ChartValidationError(ValueError):
    """图表参数校验异常"""


def setup_chinese_font() -> None:
    preferred_font_files = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simsun.ttf",
    ]
    selected_font_name = None
    for font_file in preferred_font_files:
        if not os.path.exists(font_file):
            continue
        try:
            font_manager.fontManager.addfont(font_file)
            selected_font_name = font_manager.FontProperties(fname=font_file).get_name()
            break
        except Exception:
            continue
    if selected_font_name:
        plt.rcParams["font.family"] = [selected_font_name]
    else:
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [
            "Noto Sans CJK SC", "Noto Serif CJK SC",
            "Microsoft YaHei", "SimHei", "SimSun",
            "PingFang SC", "Hiragino Sans GB", "WenQuanYi Micro Hei",
            "Songti SC",
        ]
    plt.rcParams["axes.unicode_minus"] = False


def to_positive_float(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ChartValidationError(f"{field_name} 必须是数字") from exc
    if number <= 0:
        raise ChartValidationError(f"{field_name} 必须大于 0")
    return number


def to_float_list(value: Any, field_name: str) -> List[float]:
    if isinstance(value, list):
        seq = value
    elif isinstance(value, str):
        seq = [x for x in value.replace("，", ",").replace("\n", ",").split(",") if x.strip()]
    else:
        raise ChartValidationError(f"{field_name} 必须是数组或逗号分隔字符串")
    try:
        return [float(x) for x in seq]
    except Exception as exc:
        raise ChartValidationError(f"{field_name} 包含非数字") from exc


def to_string_list(value: Any, field_name: str) -> List[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    elif isinstance(value, str):
        return [x.strip() for x in value.replace("，", ",").replace("\n", ",").split(",") if x.strip()]
    else:
        raise ChartValidationError(f"{field_name} 必须是数组或逗号分隔字符串")


def to_matrix(value: Any, field_name: str) -> List[List[float]]:
    if isinstance(value, list):
        matrix = value
    elif isinstance(value, str):
        rows = [r for r in value.split(";") if r.strip()]
        matrix = [[float(x) for x in row.replace("，", ",").split(",") if x.strip()] for row in rows]
    else:
        raise ChartValidationError(f"{field_name} 必须是二维数组或 ';' 分组字符串")
    if not matrix or not all(isinstance(row, list) and row for row in matrix):
        raise ChartValidationError(f"{field_name} 不能为空")
    return [[float(x) for x in row] for row in matrix]


def figure_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def control_limits_line(ax, x, y, cl, ucl, lcl, title, ylabel, bottom_zero=False):
    ax.plot(x, y, linestyle="-", marker="o", color="#111827")
    ax.axhline(cl, color="#2563eb", linewidth=1.2, label="CL")
    ax.plot(x, ucl, color="#dc2626", linestyle="--", linewidth=1.1, label="UCL")
    ax.plot(x, lcl, color="#dc2626", linestyle="--", linewidth=1.1, label="LCL")
    ax.set_title(title)
    ax.set_xlabel("组别")
    ax.set_ylabel(ylabel)
    if bottom_zero:
        ax.set_ylim(bottom=0)
    ax.grid(alpha=0.2)
