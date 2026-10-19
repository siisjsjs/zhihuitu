"""DPMO 控制图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, to_positive_float, control_limits_line


def generate(params: dict) -> dict:
    setup_chinese_font()
    defects = np.array(to_float_list(params.get("defects_found"), "defects_found"))
    sample_size = to_positive_float(params.get("sample_size"), "sample_size")
    opportunities = to_positive_float(params.get("opportunities"), "opportunities")
    title = str(params.get("title", "")).strip()

    dpmo = defects / sample_size / opportunities * 1_000_000
    cl = float(np.mean(dpmo))

    mr = np.abs(np.diff(dpmo))
    mr_bar = float(np.mean(mr)) if mr.size > 0 else 0
    ucl = cl + 2.66 * mr_bar
    lcl = max(0, cl - 2.66 * mr_bar)

    ucl_arr = np.full(dpmo.shape, ucl)
    lcl_arr = np.full(dpmo.shape, lcl)
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(1, len(dpmo) + 1)
    control_limits_line(ax, x, dpmo, cl, ucl_arr, lcl_arr,
                        title if title else "DPMO 控制图", "DPMO", bottom_zero=True)

    sigma_table = [(3.4, 6), (233, 5), (6210, 4), (66807, 3), (308538, 2)]
    sigma_level = 1
    for threshold, level in sigma_table:
        if cl <= threshold:
            sigma_level = level
            break

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "批次数": int(defects.size),
            "样本量": int(sample_size),
            "缺陷机会数": int(opportunities),
            "平均 DPMO": round(cl, 2),
            "UCL": round(ucl, 2),
            "LCL": round(lcl, 2),
            "Sigma 水平": f"≈ {sigma_level}σ",
        },
    }
