"""过程能力分析生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, to_float_list, ChartValidationError


def _normal_pdf(x, mu, sigma):
    return (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def _to_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ChartValidationError(f"{field_name} 必须是数字")


def generate(params: dict) -> dict:
    setup_chinese_font()
    data = np.array(to_float_list(params.get("data"), "data"))
    lsl = _to_float(params.get("LSL"), "LSL")
    usl = _to_float(params.get("USL"), "USL")
    target = float(params.get("target", (lsl + usl) / 2))
    title = str(params.get("title", "")).strip()
    if usl <= lsl:
        raise ChartValidationError("USL 必须大于 LSL")
    if data.size < 3:
        raise ChartValidationError("data 至少 3 个点")

    mu = float(np.mean(data))
    sigma = float(np.std(data, ddof=1)) if data.size > 1 else 1e-6
    sigma = max(sigma, 1e-12)
    cp = (usl - lsl) / (6 * sigma)
    cpk = min((usl - mu) / (3 * sigma), (mu - lsl) / (3 * sigma))
    ppu = (usl - mu) / (3 * sigma)
    ppl = (mu - lsl) / (3 * sigma)

    if cp >= 1.33:
        level = "优秀 (Cp≥1.33)"
    elif cp >= 1.0:
        level = "合格 (1.0≤Cp<1.33)"
    else:
        level = "不足 (Cp<1.0)"

    fig, ax = plt.subplots(figsize=(10, 5))

    n_bins = min(20, max(6, data.size // 2))
    ax.hist(data, bins=n_bins, density=True, color="#bfdbfe", edgecolor="#1e40af",
            alpha=0.85, linewidth=0.8, zorder=2)

    spread = max(usl - lsl, 6 * sigma)
    x_min = min(lsl, mu - 4 * sigma) - 0.05 * spread
    x_max = max(usl, mu + 4 * sigma) + 0.05 * spread
    x = np.linspace(x_min, x_max, 500)
    y = _normal_pdf(x, mu, sigma)
    ax.plot(x, y, color="#2563eb", linewidth=2.2, label="拟合正态分布", zorder=3)

    ax.axvline(lsl, color="#dc2626", linestyle="--", linewidth=2, label=f"LSL = {lsl}", zorder=4)
    ax.axvline(usl, color="#dc2626", linestyle="--", linewidth=2, label=f"USL = {usl}", zorder=4)
    ax.axvline(target, color="#16a34a", linestyle="-.", linewidth=1.5, label=f"目标值 = {target}", zorder=4)
    ax.axvline(mu, color="#2563eb", linestyle="-", linewidth=1.5, alpha=0.7, label=f"均值 = {mu:.4f}", zorder=4)

    ax.set_title(title if title else "过程能力分析", fontsize=16, fontweight="bold", pad=12)
    ax.set_xlabel("测量值", fontsize=12)
    ax.set_ylabel("概率密度", fontsize=12)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
    ax.grid(alpha=0.15, zorder=0)
    ax.set_xlim(x_min, x_max)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "样本数": int(data.size),
            "均值": round(mu, 4),
            "标准差": round(sigma, 4),
            "规格下限 LSL": lsl,
            "规格上限 USL": usl,
            "目标值": target,
            "Cp": round(cp, 4),
            "Cpk": round(cpk, 4),
            "Ppu": round(ppu, 4),
            "Ppl": round(ppl, 4),
            "判定": level,
        },
    }
