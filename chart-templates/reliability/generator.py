"""可靠性分析生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, ChartValidationError


def _normal_pdf(x, mu, sigma):
    return (1.0 / (sigma * math.sqrt(2 * math.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def generate(params: dict) -> dict:
    setup_chinese_font()
    times = params.get("failure_times")
    if not times:
        raise ChartValidationError("请提供失效时间数据 failure_times")
    y = np.array(to_float_list(times, "failure_times"))
    if y.size < 5:
        raise ChartValidationError("failure_times 至少 5 个点")

    mu = float(np.mean(y))
    sigma = float(np.std(y, ddof=1)) if y.size > 1 else 1.0
    median = float(np.median(y))
    min_val = float(np.min(y))
    max_val = float(np.max(y))

    title = str(params.get("title", "")).strip()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(y, bins=min(20, max(5, y.size // 2)), color="#93c5fd", edgecolor="#1e40af", alpha=0.85)

    x_fit = np.linspace(min_val - sigma, max_val + sigma, 300)
    pdf = _normal_pdf(x_fit, mu, max(sigma, 1e-6))
    ax2 = ax.twinx()
    ax2.plot(x_fit, pdf, color="#2563eb", linewidth=2, label="正态拟合")
    ax2.set_ylabel("密度")
    ax2.legend(loc="upper right")

    ax.set_title(title if title else "可靠性分析（失效时间分布）", fontsize=16, fontweight="bold")
    ax.set_xlabel("失效时间")
    ax.set_ylabel("频次")
    ax.grid(True, alpha=0.2)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "样本数": int(y.size),
            "平均寿命": round(mu, 2),
            "中位数": round(median, 2),
            "标准差": round(sigma, 2),
            "最短寿命": round(min_val, 2),
            "最长寿命": round(max_val, 2),
            "极差": round(max_val - min_val, 2),
        }
    }
