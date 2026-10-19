"""p 控制图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, control_limits_line, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    defects = np.array(to_float_list(params.get("defects"), "defects"))
    n = np.array(to_float_list(params.get("group_size"), "group_size"))
    title = str(params.get("title", "")).strip()
    if defects.size != n.size:
        raise ChartValidationError("defects 与 group_size 长度必须一致")
    p = defects / n
    pbar = defects.sum() / n.sum()
    ucl = pbar + 3 * np.sqrt(np.maximum(pbar * (1 - pbar) / n, 0))
    lcl = np.maximum(0, pbar - 3 * np.sqrt(np.maximum(pbar * (1 - pbar) / n, 0)))
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(1, len(p) + 1)
    control_limits_line(ax, x, p, pbar, ucl, lcl, title if title else "p 控制图", "不合格品率", bottom_zero=True)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "批次数": int(defects.size),
            "总检验数": int(n.sum()),
            "总不合格数": int(defects.sum()),
            "平均不合格率 p̄": round(float(pbar), 4),
            "UCL": round(float(ucl.mean()), 4),
            "LCL": round(float(lcl.mean()), 4),
        },
    }
