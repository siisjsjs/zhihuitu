"""X̄-R 控制图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_matrix, control_limits_line, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    subgroups = to_matrix(params.get("subgroups"), "subgroups")
    title = str(params.get("title", "")).strip()
    n = len(subgroups[0])
    if n < 2:
        raise ChartValidationError("Xbar-R 图每组样本量必须 >= 2")
    if any(len(g) != n for g in subgroups):
        raise ChartValidationError("subgroups 每组长度必须一致")
    arr = np.array(subgroups, dtype=float)
    xbar = arr.mean(axis=1)
    r = arr.max(axis=1) - arr.min(axis=1)
    a2 = {2: 1.88, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}.get(n, 0.577)
    d3 = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}.get(n, 0)
    d4 = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}.get(n, 2.114)
    xbarbar, rbar = float(np.mean(xbar)), float(np.mean(r))
    fig, axs = plt.subplots(2, figsize=(10, 8), sharex=True)
    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold")
    x = np.arange(1, len(xbar) + 1)

    ucl_x = np.full(len(x), xbarbar + a2 * rbar)
    lcl_x = np.full(len(x), np.maximum(0, xbarbar - a2 * rbar))
    control_limits_line(axs[0], x, xbar, xbarbar, ucl_x, lcl_x, "X̄ 图", "均值")

    ucl_r = np.full(len(x), d4 * rbar)
    lcl_r = np.full(len(x), d3 * rbar)
    control_limits_line(axs[1], x, r, rbar, ucl_r, lcl_r, "R 图", "极差", bottom_zero=True)

    fig.tight_layout()
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "组数": len(subgroups),
            "子组大小": n,
            "总均值 X̄̄": round(xbarbar, 4),
            "平均极差 R̄": round(rbar, 4),
            "UCL(X̄)": round(float(xbarbar + a2 * rbar), 4),
            "LCL(X̄)": round(float(max(0, xbarbar - a2 * rbar)), 4),
            "UCL(R)": round(float(d4 * rbar), 4),
            "LCL(R)": round(float(d3 * rbar), 4),
        },
    }
