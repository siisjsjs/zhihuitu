"""鱼骨图生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError


def _parse_causes(params: dict) -> dict:
    branch_keys = ["人员", "机器", "材料", "方法", "环境", "测量"]
    branches = {}
    for key in branch_keys:
        raw = params.get(key)
        if raw:
            if isinstance(raw, list):
                causes = [str(c).strip() for c in raw if str(c).strip()]
            elif isinstance(raw, str):
                causes = [c.strip() for c in raw.replace("，", ",").replace("\n", ",").split(",") if c.strip()]
            else:
                causes = [str(raw).strip()] if str(raw).strip() else []
            if causes:
                branches[key] = causes
    return branches


def generate(params: dict) -> dict:
    setup_chinese_font()
    problem = str(params.get("problem", "")).strip()
    if not problem:
        raise ChartValidationError("problem 不能为空")

    title = str(params.get("title", "")).strip()
    branches = _parse_causes(params)
    if not branches:
        raise ChartValidationError("至少需要在一个分支（人员/机器/材料/方法/环境/测量）中填写原因")

    total_causes = sum(len(v) for v in branches.values())
    branch_names = list(branches.keys())
    num = len(branch_names)

    # --- adaptive sizing ---
    max_causes = max(len(v) for v in branches.values())
    all_texts = [c for v in branches.values() for c in v]
    max_text_len = max(len(t) for t in all_texts) if all_texts else 4

    if max_causes <= 3 and max_text_len <= 8:
        sub_font = 14
        sub_pad = 0.5
        cat_font = 17
        fig_h = 9
    elif max_causes <= 4 and max_text_len <= 12:
        sub_font = 12
        sub_pad = 0.4
        cat_font = 15
        fig_h = 10
    else:
        sub_font = 11
        sub_pad = 0.35
        cat_font = 14
        fig_h = 11

    fig, ax = plt.subplots(figsize=(16, fig_h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.02)

    spine_y = 0.50
    spine_x0 = 0.03
    spine_x1 = 0.75

    ax.text(0.98, spine_y, problem,
            fontsize=36, fontweight="bold", va="center", ha="right")
    ax.annotate("", xy=(spine_x1, spine_y), xytext=(spine_x0, spine_y),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=2.5,
                                mutation_scale=22))

    if title:
        ax.text(0.5, 0.97, title, fontsize=24, fontweight="bold",
                ha="center", va="top", transform=ax.transAxes)

    # --- branch layout ---
    branch_dy = 0.42
    branch_slope = 0.32

    cat_box = dict(boxstyle="square,pad=0.6", facecolor="white",
                   edgecolor="black", linewidth=1.2)
    sub_box = dict(boxstyle=f"square,pad={sub_pad}", facecolor="white",
                   edgecolor="black", linewidth=1.0)
    branch_arrow = dict(arrowstyle="-|>", color="black", lw=2.0, mutation_scale=16)
    cause_arrow = dict(arrowstyle="-|>", color="black", lw=1.2, mutation_scale=14)

    for i, name in enumerate(branch_names):
        causes = branches[name]
        direction = 1 if i % 2 == 0 else -1

        x_spine = spine_x0 + (spine_x1 - spine_x0) * (i + 1) / (num + 1)
        dx = branch_slope * branch_dy
        tip_x = x_spine - dx
        tip_y = spine_y + direction * branch_dy

        ax.annotate("", xy=(x_spine, spine_y), xytext=(tip_x, tip_y),
                    arrowprops=branch_arrow)
        ax.text(tip_x, tip_y, name, fontsize=cat_font, fontweight="bold",
                ha="center", va="center", bbox=cat_box, zorder=5)

        n_causes = len(causes)
        for j, cause in enumerate(causes):
            frac = (j + 1) / (n_causes + 1)
            bx = tip_x + frac * (x_spine - tip_x)
            by = tip_y + frac * (spine_y - tip_y)

            arrow_len = 0.045
            ax.annotate("", xy=(bx, by), xytext=(bx - arrow_len, by),
                        arrowprops=cause_arrow)
            ax.text(bx - arrow_len - 0.004, by, cause, fontsize=sub_font,
                    ha="right", va="center", bbox=sub_box)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {"问题": problem, "分支数": len(branches), "总原因数": total_causes},
    }
