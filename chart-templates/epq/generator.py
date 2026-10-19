"""经济生产批量 EPQ 生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_positive_float, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    demand = to_positive_float(params.get("D"), "年需求量 D")
    production = to_positive_float(params.get("P"), "生产率 P")
    setup = to_positive_float(params.get("K"), "生产准备成本 K")
    holding = to_positive_float(params.get("H"), "单位持有成本 H")
    if demand >= production:
        raise ChartValidationError("年需求量 D 必须小于生产率 P")

    epq = float(np.sqrt((2 * demand * setup) / (holding * (1 - (demand / production)))))
    runs = demand / epq
    cycle_month = epq / demand * 12
    max_inventory = epq * (1 - demand / production)
    apc = runs * setup
    ahc = (epq / 2) * (1 - demand / production) * holding
    atc = apc + ahc

    t = np.linspace(0, 12, 600)
    y = np.zeros_like(t)
    for idx, month in enumerate(t):
        in_cycle = month % cycle_month
        prod_stage = (epq / production) * 12
        if in_cycle <= prod_stage:
            y[idx] = max_inventory * (in_cycle / prod_stage) if prod_stage > 0 else 0
        else:
            consume_stage = cycle_month - prod_stage
            y[idx] = max_inventory * max(0, 1 - (in_cycle - prod_stage) / consume_stage) if consume_stage > 0 else 0

    title = str(params.get("title", "")).strip()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(t, y, color="#14b8a6", linewidth=2)
    ax.set_title(title if title else "经济生产量（EPQ）库存水平图", fontsize=16, fontweight="bold")
    ax.set_xlabel("月份")
    ax.set_ylabel("库存水平")
    ax.grid(alpha=0.25)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "最佳生产量 Q": round(epq, 3),
            "年生产批次": round(runs, 3),
            "生产周期(月)": round(cycle_month, 3),
            "最大库存量": round(max_inventory, 3),
            "年准备成本": round(apc, 3),
            "年持有成本": round(ahc, 3),
            "年总成本": round(atc, 3),
        }
    }
