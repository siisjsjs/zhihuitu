"""经济订货量 EOQ 生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_positive_float


def generate(params: dict) -> dict:
    setup_chinese_font()
    s_cost = to_positive_float(params.get("S"), "订货成本 S")
    demand = to_positive_float(params.get("D"), "年需求量 D")
    holding = to_positive_float(params.get("H"), "单位持有成本 H")

    eoq = float(np.sqrt(2 * s_cost * demand / holding))
    order_times = demand / eoq
    cycle_month = 12 / order_times
    aoc = order_times * s_cost
    ahc = (eoq / 2) * holding
    atc = aoc + ahc

    periods = [0.0]
    levels = [eoq]
    current = 0.0
    while current < 12:
        current = min(12, current + cycle_month)
        periods.extend([current, current])
        levels.extend([eoq, 0.0])

    title = str(params.get("title", "")).strip()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(periods, levels, color="#2563eb", linewidth=2)
    ax.set_title(title if title else "经济订货量（EOQ）库存水平图", fontsize=16, fontweight="bold")
    ax.set_xlabel("月份")
    ax.set_ylabel("库存水平")
    ax.grid(alpha=0.25)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "最佳订货量 Q": round(eoq, 3),
            "年订货次数": round(order_times, 3),
            "订货周期(月)": round(cycle_month, 3),
            "年订货成本": round(aoc, 3),
            "年持有成本": round(ahc, 3),
            "年总成本": round(atc, 3),
        }
    }
