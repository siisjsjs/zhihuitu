"""散点图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    x_values = np.array(to_float_list(params.get("x_values"), "x_values"))
    y_values = np.array(to_float_list(params.get("y_values"), "y_values"))
    if x_values.size != y_values.size:
        raise ChartValidationError("x_values 与 y_values 长度必须一致")
    if x_values.size < 2:
        raise ChartValidationError("至少需要 2 组点")

    title = str(params.get("title", "")).strip()
    x_label = str(params.get("x_label", "")).strip()
    y_label = str(params.get("y_label", "")).strip()

    r = float(np.corrcoef(x_values, y_values)[0, 1]) if x_values.size > 1 else float("nan")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.scatter(x_values, y_values, color="#8b5cf6", s=42)
    ax.set_title(title if title else "散点图与相关性")
    ax.set_xlabel(x_label if x_label else "X")
    ax.set_ylabel(y_label if y_label else "Y")
    ax.grid(alpha=0.2)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {"样本点数": int(x_values.size), "皮尔逊相关系数": round(r, 6)}
    }
