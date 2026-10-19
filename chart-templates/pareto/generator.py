"""帕累托图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    categories = params.get("categories") or []
    values = params.get("values") or []
    if not categories or not values or len(categories) != len(values):
        raise ChartValidationError("帕累托图需要 categories 与 values，且长度一致")
    title = str(params.get("title", "")).strip()
    vals = [float(v) for v in values]
    pairs = sorted(zip(categories, vals), key=lambda x: x[1], reverse=True)
    names = [x[0] for x in pairs]
    nums = np.array([x[1] for x in pairs], dtype=float)
    cumulative = np.cumsum(nums) / max(nums.sum(), 1e-6) * 100

    fig, ax1 = plt.subplots(figsize=(10, 4.8))
    ax1.bar(names, nums, color="#f97316")
    ax1.set_ylabel("频次")
    ax1.tick_params(axis="x", rotation=25)
    ax2 = ax1.twinx()
    ax2.plot(names, cumulative, color="#2563eb", marker="o")
    ax2.axhline(80, color="#dc2626", linestyle="--", linewidth=1)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("累计百分比(%)")
    ax1.set_title(title if title else "帕累托图")

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {"总频次": float(nums.sum()), "最高项": names[0], "最高值": float(nums[0])}
    }
