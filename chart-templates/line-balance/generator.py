"""产线平衡分析生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_string_list, to_float_list, ChartValidationError


def generate(params: dict) -> dict:
    setup_chinese_font()
    station_names = to_string_list(params.get("station_names"), "station_names")
    station_times = to_float_list(params.get("station_times"), "station_times")

    if len(station_names) != len(station_times):
        raise ChartValidationError("station_names 与 station_times 长度必须一致")
    if len(station_times) < 2:
        raise ChartValidationError("至少需要 2 个工位")

    total_time = sum(station_times)
    bottleneck_time = max(station_times)
    bottleneck_idx = station_times.index(bottleneck_time)
    average_time = total_time / len(station_times)
    balance_rate = (average_time / bottleneck_time) * 100
    num_stations = len(station_times)

    title = str(params.get("title", "")).strip()
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.bar(range(num_stations), station_times, color="steelblue", alpha=0.7,
                  edgecolor="black", linewidth=1.5)
    bars[bottleneck_idx].set_color("red")
    bars[bottleneck_idx].set_alpha(0.8)

    for i, (bar, time_val) in enumerate(zip(bars, station_times)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height,
                f"{time_val:.2f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.axhline(y=average_time, color="green", linestyle="--", linewidth=2,
               label=f"平均时间: {average_time:.2f}")
    ax.axhline(y=bottleneck_time, color="red", linestyle="--", linewidth=2,
               label=f"瓶颈时间: {bottleneck_time:.2f}")
    ax.plot([], [], ' ', label=f"线平衡率: {balance_rate:.2f}%")

    ax.set_xlabel("工位")
    ax.set_ylabel("时间")
    ax.set_title(title if title else "生产线平衡分析图", fontsize=16, fontweight="bold")
    ax.set_xticks(range(num_stations))
    ax.set_xticklabels(station_names)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3, linestyle="--", axis="y")
    ax.set_ylim(0, bottleneck_time * 1.2)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "瓶颈工位": station_names[bottleneck_idx],
            "瓶颈时间": bottleneck_time,
            "平均时间": round(average_time, 2),
            "线平衡率": f"{balance_rate:.2f}%",
            "工位数": num_stations,
        }
    }
