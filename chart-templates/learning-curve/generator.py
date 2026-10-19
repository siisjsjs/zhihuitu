"""学习曲线生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, to_positive_float, ChartValidationError


def _linregress(x, y):
    n = len(x)
    sx = np.sum(x)
    sy = np.sum(y)
    sxy = np.sum(x * y)
    sxx = np.sum(x * x)
    syy = np.sum(y * y)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n
    ss_res = syy - intercept * sy - slope * sxy
    ss_tot = syy - sy * sy / n
    r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0
    return slope, intercept, r_squared


def generate(params: dict) -> dict:
    setup_chinese_font()
    repeat_counts = np.array(to_float_list(params.get("repeat_counts"), "repeat_counts"))
    work_times = np.array(to_float_list(params.get("work_times"), "work_times"))
    predict_n = to_positive_float(params.get("predict_n", 5), "predict_n")

    if repeat_counts.size != work_times.size:
        raise ChartValidationError("repeat_counts 与 work_times 长度必须一致")
    if repeat_counts.size < 2:
        raise ChartValidationError("至少需要 2 组数据点")

    log_x = np.log10(repeat_counts)
    log_y = np.log10(work_times)
    slope, intercept, r_squared = _linregress(log_x, log_y)

    a = 10 ** intercept
    b = slope

    x_pred = np.arange(1, int(predict_n) + 1)
    y_pred = a * x_pred ** b

    learning_rate = 2 ** b

    title = str(params.get("title", "")).strip()
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x_pred, y_pred, color="#2563eb", marker="o", label="学习曲线")
    ax.scatter(repeat_counts, work_times, color="#ef4444", zorder=5, label="实际数据点")
    ax.set_title(title if title else "学习曲线分析", fontsize=16, fontweight="bold")
    ax.set_xlabel("操作重复次数")
    ax.set_ylabel("工时")
    ax.legend()
    ax.grid(True, alpha=0.3)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "公式": f"y = {a:.2f} × x^({b:.4f})",
            "参数 a": round(a, 4),
            "参数 b": round(b, 4),
            "学习率": f"{learning_rate * 100:.2f}%",
            "R²": round(r_squared, 6),
            "第1次工时": round(y_pred[0], 2),
            f"第{int(predict_n)}次工时": round(y_pred[-1], 2),
        }
    }
