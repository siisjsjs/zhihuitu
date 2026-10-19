"""c 控制图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, control_limits_line


def generate(params: dict) -> dict:
    setup_chinese_font()
    c = np.array(to_float_list(params.get("defects"), "defects"))
    title = str(params.get("title", "")).strip()
    cbar = float(np.mean(c))
    sigma = np.sqrt(max(cbar, 0))
    ucl = cbar + 3 * sigma
    lcl = max(0, cbar - 3 * sigma)
    ucl_arr = np.full(c.shape, ucl)
    lcl_arr = np.full(c.shape, lcl)
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(1, len(c) + 1)
    control_limits_line(ax, x, c, cbar, ucl_arr, lcl_arr, title if title else "c 控制图", "缺陷数", bottom_zero=True)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "样本数": int(c.size),
            "总缺陷数": int(c.sum()),
            "平均缺陷数 c̄": round(cbar, 4),
            "UCL": round(ucl, 4),
            "LCL": round(lcl, 4),
        },
    }
