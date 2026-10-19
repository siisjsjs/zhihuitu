"""目标偏差图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, control_limits_line, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    reading = np.array(to_float_list(params.get("reading"), "reading"))
    target = np.array(to_float_list(params.get("target"), "target"))
    title = str(params.get("title", "")).strip()
    if reading.size != target.size:
        raise ChartValidationError("reading 与 target 长度必须一致")
    if reading.size < 3:
        raise ChartValidationError("至少需要 3 组数据")

    dev = reading - target
    mr = np.abs(np.diff(dev))
    dev_cl = float(np.mean(dev))
    mr_cl = float(np.mean(mr))

    fig, axs = plt.subplots(2, figsize=(10, 8), sharex=True)
    if title:
        fig.suptitle(title, fontsize=16, fontweight="bold")

    idx_dev = np.arange(1, len(dev) + 1)
    ucl_dev = np.full(len(dev), dev_cl + 2.66 * mr_cl)
    lcl_dev = np.full(len(dev), dev_cl - 2.66 * mr_cl)
    control_limits_line(axs[0], idx_dev, dev, dev_cl, ucl_dev, lcl_dev, "目标偏差图", "目标偏差")

    idx_mr = np.arange(2, len(dev) + 1)
    ucl_mr = np.full(len(mr), 3.267 * mr_cl)
    lcl_mr = np.zeros(len(mr))
    control_limits_line(axs[1], idx_mr, mr, mr_cl, ucl_mr, lcl_mr, "MR 图", "移动极差", bottom_zero=True)

    fig.tight_layout()
    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "样本数": int(reading.size),
            "平均偏差": round(dev_cl, 4),
            "移动极差均值 MR": round(mr_cl, 4),
            "UCL(偏差)": round(float(dev_cl + 2.66 * mr_cl), 4),
            "LCL(偏差)": round(float(dev_cl - 2.66 * mr_cl), 4),
            "UCL(MR)": round(float(3.267 * mr_cl), 4),
        },
    }
