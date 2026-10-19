"""山积图（Yamazumi Chart）生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from _utils import setup_chinese_font, figure_to_base64, to_string_list, to_matrix, ChartValidationError


HATCH_PATTERNS = [
    '///',
    '\\\\\\',
    '...',
    '---',
    '|||',
    'xxx',
    'ooo',
    '++',
    '**',
    'OO',
    '//',
    '\\\\',
    '..',
    '--',
    '||',
]


def generate(params: dict) -> dict:
    setup_chinese_font()

    process_names = to_string_list(params.get("process_names"), "process_names")
    element_names = to_string_list(params.get("element_names"), "element_names")
    element_times = to_matrix(params.get("element_times"), "element_times")

    n_proc = len(process_names)
    n_elem = len(element_names)

    if n_proc < 2:
        raise ChartValidationError("至少需要 2 个工序")
    if n_elem < 1:
        raise ChartValidationError("至少需要 1 个元素")
    if len(element_times) != n_proc:
        raise ChartValidationError(
            f"工序名称有 {n_proc} 个，但元素时间有 {len(element_times)} 行，数量必须一致"
        )

    for row in element_times:
        while len(row) < n_elem:
            row.append(0.0)

    takt_time = params.get("takt_time")
    if takt_time is not None:
        try:
            takt_time = float(takt_time)
        except (TypeError, ValueError):
            takt_time = None

    title = str(params.get("title", "")).strip()
    data = np.array([row[:n_elem] for row in element_times], dtype=float)
    totals = data.sum(axis=1)

    fig_width = max(8, n_proc * 1.0 + 3)
    fig_height = 7
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    x = np.arange(n_proc)
    bar_width = 0.55
    bottoms = np.zeros(n_proc)

    for j in range(n_elem):
        col_data = data[:, j]
        hatch = HATCH_PATTERNS[j % len(HATCH_PATTERNS)]
        ax.bar(
            x, col_data, bar_width,
            bottom=bottoms,
            color='white',
            edgecolor='black',
            linewidth=0.8,
            hatch=hatch,
        )
        bottoms += col_data

    for i, total in enumerate(totals):
        label_text = f"{int(total)}s" if total == int(total) else f"{total:.1f}s"
        ax.text(x[i], total + totals.max() * 0.015, label_text,
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    if takt_time is not None and takt_time > 0:
        ax.axhline(y=takt_time, color='red', linestyle='--', linewidth=1.5,
                   label=f'节拍时间: {takt_time:.0f}s')

    ax.set_xlabel('工序编号', fontsize=12)
    ax.set_ylabel('标准时间', fontsize=12)
    ax.set_title(title if title else '山积图', fontsize=14, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(process_names, fontsize=10)
    ax.set_ylim(0, totals.max() * 1.15)

    y_max_tick = int(np.ceil(totals.max() / 10) * 10)
    ax.set_yticks(np.arange(0, y_max_tick + 1, max(10, y_max_tick // 8 // 5 * 5 or 10)))
    ax.yaxis.set_tick_params(labelsize=10)

    legend_patches = [
        mpatches.Patch(
            facecolor='white', edgecolor='black',
            hatch=HATCH_PATTERNS[j % len(HATCH_PATTERNS)],
            label=element_names[j]
        )
        for j in range(n_elem)
    ]
    ax.legend(
        handles=legend_patches,
        title='元素编号',
        loc='upper right',
        fontsize=9,
        title_fontsize=10,
        frameon=True,
        edgecolor='black',
        fancybox=False,
        borderpad=0.6,
        labelspacing=0.4,
        handlelength=1.8,
        handleheight=1.2,
    )

    ax.spines['top'].set_visible(True)
    ax.spines['right'].set_visible(True)
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

    ax.grid(False)
    fig.tight_layout()

    bottleneck_idx = int(np.argmax(totals))
    min_idx = int(np.argmin(totals))

    summary = {
        "工序数": n_proc,
        "元素数": n_elem,
        "最大工序时间": f"{totals[bottleneck_idx]:.1f}s ({process_names[bottleneck_idx]})",
        "最小工序时间": f"{totals[min_idx]:.1f}s ({process_names[min_idx]})",
        "平均工序时间": f"{totals.mean():.1f}s",
        "总时间": f"{totals.sum():.1f}s",
    }
    if takt_time and takt_time > 0:
        over_takt = [process_names[i] for i in range(n_proc) if totals[i] > takt_time]
        summary["超节拍工序"] = ", ".join(over_takt) if over_takt else "无"

    return {
        "image_base64": figure_to_base64(fig),
        "summary": summary,
    }
