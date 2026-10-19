"""直方图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    values = np.array(to_float_list(params.get("values"), "values"))
    bins = int(float(params.get("bins", 6)))
    bins = max(3, min(30, bins))
    title = str(params.get("title", "")).strip()
    if values.size < 3:
        raise ChartValidationError("values 至少 3 个点")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(values, bins=bins, color="#14b8a6", edgecolor="#0f172a", alpha=0.9)
    ax.set_title(title if title else "直方图", fontsize=16, fontweight="bold")
    ax.set_xlabel("测量值", fontsize=12)
    ax.set_ylabel("频数", fontsize=12)
    ax.grid(alpha=0.2)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "样本数": int(values.size),
            "均值": round(float(np.mean(values)), 4),
            "标准差": round(float(np.std(values, ddof=1)), 4) if values.size > 1 else 0,
            "最小值": round(float(values.min()), 4),
            "最大值": round(float(values.max()), 4),
        },
    }
