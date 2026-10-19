"""设备综合效率 OEE 生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_positive_float, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    total_time = to_positive_float(params.get("A"), "总可用时间 A")
    run_time = to_positive_float(params.get("B"), "运行时间 B")
    capacity = to_positive_float(params.get("C"), "生产能力 C")
    actual = to_positive_float(params.get("D"), "实际产量 D")
    output = to_positive_float(params.get("E"), "产品产出 E")
    good = to_positive_float(params.get("F"), "实际良品数 F")

    if run_time > total_time:
        raise ChartValidationError("运行时间 B 不能大于总可用时间 A")
    if actual > capacity:
        raise ChartValidationError("实际产量 D 不能大于生产能力 C")
    if output != actual:
        raise ChartValidationError("产品产出 E 需等于实际产量 D")
    if good > output:
        raise ChartValidationError("实际良品数 F 不能大于产品产出 E")

    availability = run_time / total_time
    performance = actual / capacity
    quality = good / output
    oee = availability * performance * quality
    good_pct = oee * 100
    loss_pct = 100 - good_pct

    title = str(params.get("title", "")).strip()
    fig, ax = plt.subplots(figsize=(10, 5))

    labels = ["可用率", "性能率", "质量率", "OEE"]
    values = [availability * 100, performance * 100, quality * 100, oee * 100]
    colors = ["#3b82f6", "#14b8a6", "#f59e0b", "#22c55e" if oee >= 0.85 else "#ef4444"]

    bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="white", linewidth=2)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=12, fontweight="bold")

    ax.axhline(85, linestyle="dashed", color="#64748b", linewidth=1, label="世界级 OEE (85%)")
    ax.set_ylim(0, 110)
    ax.set_title(title if title else "设备综合效率（OEE）分析", fontsize=16, fontweight="bold")
    ax.set_ylabel("百分比 (%)")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.2, axis="y")

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "可用率": f"{availability * 100:.2f}%",
            "性能率": f"{performance * 100:.2f}%",
            "质量率": f"{quality * 100:.2f}%",
            "OEE": f"{oee * 100:.2f}%",
            "损失率": f"{loss_pct:.2f}%",
            "停机时间": f"{total_time - run_time:.0f} 分钟",
            "不良品数": f"{output - good:.0f} 件",
        }
    }
