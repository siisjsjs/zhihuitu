"""I-MR 控制图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, control_limits_line, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    x = np.array(to_float_list(params.get("values"), "values"))
    title = str(params.get("title", "")).strip()
    if x.size < 3:
        raise ChartValidationError("values 至少 3 个")
    mr = np.abs(np.diff(x))
    xbar = float(np.mean(x))
    mrbar = float(np.mean(mr))
    fig, axs = plt.subplots(2, figsize=(10, 8), sharex=True)
    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold")
    idx_x = np.arange(1, len(x) + 1)
    idx_mr = np.arange(2, len(x) + 1)

    ucl_x = np.full(len(x), xbar + 2.66 * mrbar)
    lcl_x = np.full(len(x), np.maximum(0, xbar - 2.66 * mrbar))
    control_limits_line(axs[0], idx_x, x, xbar, ucl_x, lcl_x, "个体值图", "数值")

    ucl_mr = np.full(len(mr), 3.267 * mrbar)
    lcl_mr = np.zeros_like(mr)
    control_limits_line(axs[1], idx_mr, mr, mrbar, ucl_mr, lcl_mr, "mR 图", "移动极差", bottom_zero=True)

    fig.tight_layout()
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "样本数": int(x.size),
            "均值": round(xbar, 4),
            "移动极差均值 MR̄": round(mrbar, 4),
            "UCL(I)": round(float(xbar + 2.66 * mrbar), 4),
            "LCL(I)": round(float(max(0, xbar - 2.66 * mrbar)), 4),
            "UCL(MR)": round(float(3.267 * mrbar), 4),
        },
    }
