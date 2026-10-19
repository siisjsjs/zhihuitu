"""双手作业分析图生成器（服务端 matplotlib 版，版式对齐 TwoHandChart.vue 圆点连线风格）"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

BORDER = "#8a8a8a"
HEADER_BG = "#e8e8e8"
LABEL_BG = "#f5f5f5"
TOTAL_BG = "#fafafa"
DOT_COLOR = "#333333"
TEXT = "#333333"

PT2U = 100.0 / 72.0

SYMBOL_KEYS = ["operation", "transport", "delay", "hold"]
# 注：前端用 "⇨"，但常见中文字体（如微软雅黑）缺少该字形，服务端用 "→" 等价表示搬运
SYMBOL_DISPLAY = {"operation": "○", "transport": "→", "delay": "D", "hold": "▽"}
SYMBOL_LABEL = {"operation": "操作", "transport": "搬运", "delay": "等待", "hold": "持握"}
# 兼容旧数据的符号名
_SYMBOL_MIGRATE = {"operation": "operation", "transport": "transport",
                   "delay": "delay", "hold": "hold", "wait": "delay", "inspect": "hold"}


def _char_w(ch: str, fontsize: float) -> float:
    return fontsize * PT2U * (1.0 if ord(ch) > 0x2E7F else 0.58)


def _wrap(text: str, max_w: float, fontsize: float):
    lines = []
    for raw in str(text).split("\n"):
        cur, w = "", 0.0
        for ch in raw:
            cw = _char_w(ch, fontsize)
            if cur and w + cw > max_w:
                lines.append(cur)
                cur, w = ch, cw
            else:
                cur += ch
                w += cw
        lines.append(cur)
    return lines or [""]


def _cell(ax, x, y, w, h, text="", fill="white", fontsize=10, bold=False,
          color=TEXT, ha="center", wrap=False, lw=0.9):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=BORDER,
                           linewidth=lw, zorder=1))
    text = "" if text is None else str(text)
    if text:
        if wrap:
            text = "\n".join(_wrap(text, w - 12, fontsize))
        tx = x + w / 2 if ha == "center" else x + 6
        ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fontsize,
                color=color, fontweight="bold" if bold else "normal",
                linespacing=1.35, zorder=2)


def _norm_symbol(value, field: str):
    key = _SYMBOL_MIGRATE.get(str(value).strip().lower())
    if key is None:
        raise ChartValidationError(
            f"{field} 的取值 \"{value}\" 无效，只能是 operation/transport/delay/hold")
    return key


def generate(params: dict) -> dict:
    setup_chinese_font()
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")

    header = params.get("headerInfo") or {}
    if not isinstance(header, dict):
        raise ChartValidationError("headerInfo 必须是对象")
    station = str(header.get("stationName", "") or "—")
    improvement = str(header.get("improvement", "") or "现行")
    start_state = str(header.get("startState", "") or "—")
    end_state = str(header.get("endState", "") or "—")
    researcher = str(header.get("researcher", "") or "—")
    date = str(header.get("date", "") or "—")
    method = str(header.get("method", "") or "—")

    raw_steps = params.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ChartValidationError("steps（作业步骤）不能为空")
    steps = []
    for i, s in enumerate(raw_steps):
        if not isinstance(s, dict):
            raise ChartValidationError(f"steps 第 {i + 1} 项必须是对象")
        steps.append({
            "leftDesc": str(s.get("leftDesc", "") or ""),
            "leftSymbol": _norm_symbol(s.get("leftSymbol", "operation"), f"steps 第 {i + 1} 项的 leftSymbol"),
            "rightSymbol": _norm_symbol(s.get("rightSymbol", "operation"), f"steps 第 {i + 1} 项的 rightSymbol"),
            "rightDesc": str(s.get("rightDesc", "") or ""),
        })
    n = len(steps)

    # ── 统计 ──
    left_cnt = {k: 0 for k in SYMBOL_KEYS}
    right_cnt = {k: 0 for k in SYMBOL_KEYS}
    for s in steps:
        left_cnt[s["leftSymbol"]] += 1
        right_cnt[s["rightSymbol"]] += 1

    # ── 列布局：左手描述 | 4符号 | 4符号 | 右手描述 ──
    desc_w, sym_w = 176.0, 44.0
    x_ldesc = 0.0
    x_lsym = desc_w
    x_rsym = desc_w + sym_w * 4
    x_rdesc = desc_w + sym_w * 8
    total_w = desc_w * 2 + sym_w * 8

    # ── 行高 ──
    fs_body = 9.5
    heights = []
    for s in steps:
        lines = max(len(_wrap(s["leftDesc"] or "—", desc_w - 12, fs_body)),
                    len(_wrap(s["rightDesc"] or "—", desc_w - 12, fs_body)))
        heights.append(max(34.0, lines * fs_body * PT2U * 1.45 + 12))

    title_h, info_h, head1_h, head2_h = 42.0, 27.0, 28.0, 27.0
    stats_head_h, stats_row_h, total_row_h = 26.0, 25.0, 27.0
    total_h = (title_h + info_h * 3 + head1_h + head2_h + sum(heights)
               + stats_head_h + stats_row_h * 4 + total_row_h)

    fig = plt.figure(figsize=(total_w / 100.0, total_h / 100.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-1, total_w + 1)
    ax.set_ylim(total_h + 1, -1)
    ax.axis("off")

    y = 0.0
    _cell(ax, 0, y, total_w, title_h, "双手作业分析图", fontsize=15, bold=True)
    y += title_h

    # 信息区（三行）
    k_w = 82.0
    v2_w = (total_w - k_w * 2) * 0.32
    v1_w = total_w - k_w * 2 - v2_w
    for k1, v1, k2, v2 in (("工站名称", station, "改善现场", improvement),
                           ("开始状态", start_state, "结束状态", end_state)):
        _cell(ax, 0, y, k_w, info_h, k1, fill=LABEL_BG, bold=True)
        _cell(ax, k_w, y, v1_w, info_h, v1)
        _cell(ax, k_w + v1_w, y, k_w, info_h, k2, fill=LABEL_BG, bold=True)
        _cell(ax, k_w * 2 + v1_w, y, v2_w, info_h, v2)
        y += info_h
    seg_v = (total_w - k_w * 3) / 3.0
    xx = 0.0
    for k_txt, v_txt in (("研究者", researcher), ("日期", date), ("作业方式", method)):
        _cell(ax, xx, y, k_w, info_h, k_txt, fill=LABEL_BG, bold=True)
        xx += k_w
        _cell(ax, xx, y, seg_v, info_h, v_txt, fontsize=9)
        xx += seg_v
    y += info_h

    # 主表表头
    _cell(ax, x_ldesc, y, desc_w, head1_h + head2_h, "左手", fill=HEADER_BG, bold=True, fontsize=11)
    _cell(ax, x_lsym, y, sym_w * 4, head1_h, "符号", fill=HEADER_BG, bold=True, fontsize=10)
    _cell(ax, x_rsym, y, sym_w * 4, head1_h, "符号", fill=HEADER_BG, bold=True, fontsize=10)
    _cell(ax, x_rdesc, y, desc_w, head1_h + head2_h, "右手", fill=HEADER_BG, bold=True, fontsize=11)
    for side_x in (x_lsym, x_rsym):
        for j, key in enumerate(SYMBOL_KEYS):
            _cell(ax, side_x + sym_w * j, y + head1_h, sym_w, head2_h,
                  SYMBOL_DISPLAY[key], fill=HEADER_BG, bold=True, fontsize=12)
    y += head1_h + head2_h

    # 数据区：描述 + 空符号格
    row_y = [y]
    for h in heights:
        row_y.append(row_y[-1] + h)
    for i, s in enumerate(steps):
        _cell(ax, x_ldesc, row_y[i], desc_w, heights[i], s["leftDesc"] or "—",
              fontsize=fs_body, wrap=True)
        _cell(ax, x_rdesc, row_y[i], desc_w, heights[i], s["rightDesc"] or "—",
              fontsize=fs_body, wrap=True)
        for side_x in (x_lsym, x_rsym):
            for j in range(4):
                _cell(ax, side_x + sym_w * j, row_y[i], sym_w, heights[i])

    # 圆点与连线
    def _dot_points(side_key, side_x):
        pts = []
        for i, s in enumerate(steps):
            j = SYMBOL_KEYS.index(s[side_key])
            pts.append((side_x + sym_w * j + sym_w / 2, row_y[i] + heights[i] / 2))
        return pts

    for side_key, side_x in (("leftSymbol", x_lsym), ("rightSymbol", x_rsym)):
        pts = _dot_points(side_key, side_x)
        if len(pts) >= 2:
            ax.plot([p[0] for p in pts], [p[1] for p in pts],
                    color=DOT_COLOR, linewidth=1.8, solid_capstyle="round", zorder=3)
        for px, py in pts:
            ax.add_patch(Circle((px, py), 5.0, facecolor=DOT_COLOR, edgecolor="none", zorder=4))
    y = row_y[-1]

    # 统计表：统计内容 | 符号 | 左手 | 右手
    fr = [0.30, 0.20, 0.25, 0.25]
    sw = [f * total_w for f in fr]
    sx = [sum(sw[:k]) for k in range(4)]
    for k, head in enumerate(["统计内容", "符号", "左手", "右手"]):
        _cell(ax, sx[k], y, sw[k], stats_head_h, head, fill=HEADER_BG, bold=True, fontsize=10)
    y += stats_head_h
    _cell(ax, sx[0], y, sw[0], stats_row_h * 4, "次数", bold=True, fontsize=10)
    for idx, key in enumerate(SYMBOL_KEYS):
        ry = y + stats_row_h * idx
        _cell(ax, sx[1], ry, sw[1], stats_row_h,
              f"{SYMBOL_DISPLAY[key]} {SYMBOL_LABEL[key]}", bold=True, fontsize=9.5)
        _cell(ax, sx[2], ry, sw[2], stats_row_h, str(left_cnt[key]), fontsize=9.5)
        _cell(ax, sx[3], ry, sw[3], stats_row_h, str(right_cnt[key]), fontsize=9.5)
    y += stats_row_h * 4
    _cell(ax, sx[0], y, sw[0], total_row_h, "合计", fill=TOTAL_BG, bold=True, fontsize=10)
    _cell(ax, sx[1], y, sw[1], total_row_h, "", fill=TOTAL_BG)
    _cell(ax, sx[2], y, sw[2], total_row_h, str(n), fill=TOTAL_BG, bold=True, fontsize=10)
    _cell(ax, sx[3], y, sw[3], total_row_h, str(n), fill=TOTAL_BG, bold=True, fontsize=10)

    summary = {"总步数": n}
    for key in SYMBOL_KEYS:
        summary[f"左手-{SYMBOL_LABEL[key]}({SYMBOL_DISPLAY[key]})"] = left_cnt[key]
    for key in SYMBOL_KEYS:
        summary[f"右手-{SYMBOL_LABEL[key]}({SYMBOL_DISPLAY[key]})"] = right_cnt[key]

    return {"image_base64": figure_to_base64(fig), "summary": summary}
