"""流程程序图（Process Flow Chart）生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

BORDER = "#777777"
HEADER_BG = "#e8e8e8"
LABEL_BG = "#f5f5f5"
TEXT_COLOR = "#333333"
LINE_COLOR = "#ef4444"
SYM_ON = "#1f2937"
SYM_OFF = "#c9ced6"

# 工序系列列顺序（与 Vue 组件一致）
SYMBOL_ORDER = ["processing", "inspection", "transport", "waiting", "storage"]
SYMBOL_HEAD = {"processing": "操作", "inspection": "检查", "transport": "搬运",
               "waiting": "等待", "storage": "储存"}
SYMBOL_STAT = {"processing": "操作 ○", "inspection": "检查 □", "transport": "搬运 →",
               "waiting": "等待 D", "storage": "储存 ▽"}


def _tw(s, fs):
    return sum(fs * (1.0 if ord(ch) > 0x2E7F else 0.55) for ch in str(s))


def _wrap(s, fs, max_w):
    s = str(s or "")
    if not s:
        return [""]
    lines, cur, w = [], "", 0.0
    for ch in s:
        cw = fs * (1.0 if ord(ch) > 0x2E7F else 0.55)
        if cur and w + cw > max_w:
            lines.append(cur)
            cur, w = ch, cw
        else:
            cur += ch
            w += cw
    lines.append(cur)
    return lines


def _rect(ax, x, y, w, h, bg=None, lw=0.8):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=bg if bg else "white",
                           edgecolor=BORDER, linewidth=lw, zorder=1))


def _cell_text(ax, x, y, w, h, text, fs=9, bold=False, color=TEXT_COLOR):
    if text is None or text == "":
        return
    ax.text(x + w / 2, y + h / 2, str(text), ha="center", va="center",
            fontsize=fs, color=color,
            fontweight="bold" if bold else "normal", zorder=3)


def _draw_symbol(ax, sym, cx, cy, selected):
    color = SYM_ON if selected else SYM_OFF
    lw = 1.6 if selected else 1.0
    if sym == "processing":
        ax.add_patch(Circle((cx, cy), 6.2, fill=False, edgecolor=color, linewidth=lw, zorder=4))
    elif sym == "inspection":
        ax.add_patch(Rectangle((cx - 5.6, cy - 5.6), 11.2, 11.2, fill=False,
                               edgecolor=color, linewidth=lw, zorder=4))
    elif sym == "transport":
        ax.annotate("", xy=(cx + 7.5, cy), xytext=(cx - 7.5, cy),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                    mutation_scale=11), zorder=4)
    elif sym == "waiting":
        ax.text(cx, cy, "D", ha="center", va="center", fontsize=11, color=color,
                fontweight="bold" if selected else "normal", zorder=4)
    elif sym == "storage":
        ax.add_patch(Polygon([(cx - 6.2, cy - 4.8), (cx + 6.2, cy - 4.8), (cx, cy + 6.2)],
                             closed=True, fill=False, edgecolor=color, linewidth=lw, zorder=4))


def _fmt(v):
    return int(v) if float(v) == int(v) else round(float(v), 1)


def generate(params: dict) -> dict:
    setup_chinese_font()
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")

    header = params.get("headerInfo") or {}
    if not isinstance(header, dict):
        raise ChartValidationError("headerInfo 必须是对象")

    raw_steps = params.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ChartValidationError("steps 不能为空，至少需要一个流程步骤")

    steps = []
    for i, s in enumerate(raw_steps):
        if not isinstance(s, dict):
            raise ChartValidationError(f"第 {i + 1} 个步骤必须是对象")
        sym = str(s.get("symbol") or "").strip()
        if sym not in SYMBOL_ORDER:
            raise ChartValidationError(
                f"第 {i + 1} 个步骤的 symbol 无效：{sym or '（空）'}，"
                f"可选值为 processing/inspection/transport/waiting/storage")
        try:
            t = float(s.get("time") or 0)
            d = float(s.get("distance") or 0)
        except (TypeError, ValueError):
            raise ChartValidationError(f"第 {i + 1} 个步骤的 time/distance 必须是数字")
        if t < 0 or d < 0:
            raise ChartValidationError(f"第 {i + 1} 个步骤的 time/distance 不能为负数")
        steps.append({
            "content": str(s.get("content") or "").strip(),
            "time": t,
            "distance": d,
            "symbol": sym,
            "remarks": str(s.get("remarks") or "").strip(),
        })

    # ---- 统计 ----
    counts = {k: 0 for k in SYMBOL_ORDER}
    time_by = {k: 0.0 for k in SYMBOL_ORDER}
    dist_by = {k: 0.0 for k in SYMBOL_ORDER}
    for s in steps:
        counts[s["symbol"]] += 1
        time_by[s["symbol"]] += s["time"]
        dist_by[s["symbol"]] += s["distance"]
    total_time = sum(time_by.values())
    total_dist = sum(dist_by.values())

    # ---- 布局（单位：pt）----
    # 列：序号 | 工作说明 | 时间/s | 距离/m | 5 个工序符号列 | 备注
    col_w = [30, 160, 52, 52, 54, 54, 54, 54, 54, 92]
    W = sum(col_w)
    col_x = [sum(col_w[:i]) for i in range(len(col_w))]
    SYM_COLS = [4, 5, 6, 7, 8]

    fs_cell = 9
    title_h = 34
    info_rows = 7
    info_row_h = 26
    head_section_h = info_rows * info_row_h  # 182
    left_w = round(W * 0.62)
    right_w = W - left_w

    head1_h, head2_h = 22, 20
    row_lines = []
    row_hs = []
    for s in steps:
        c = _wrap(s["content"], fs_cell, col_w[1] - 10)
        r = _wrap(s["remarks"], fs_cell, col_w[9] - 10)
        row_lines.append((c, r))
        row_hs.append(max(28, 14 * max(len(c), len(r)) + 10))

    H = title_h + head_section_h + head1_h + head2_h + sum(row_hs)

    fig = plt.figure(figsize=(W / 72, H / 72))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    # 标题
    _rect(ax, 0, 0, W, title_h)
    ax.text(W / 2, title_h / 2, "流程程序图", ha="center", va="center",
            fontsize=13, color=TEXT_COLOR, fontweight="bold", zorder=3)

    # ---- 顶部：左侧基本信息 + 右侧统计表 ----
    y0 = title_h
    info_items = [
        ("工作名称", header.get("workName")), ("开始", header.get("start")),
        ("结束", header.get("end")), ("研究者", header.get("researcher")),
        ("审阅者", header.get("reviewer")), ("日期", header.get("date")),
        ("版本", header.get("version")),
    ]
    k_w = 78
    for i, (k, v) in enumerate(info_items):
        ry = y0 + i * info_row_h
        _rect(ax, 0, ry, k_w, info_row_h, LABEL_BG)
        _cell_text(ax, 0, ry, k_w, info_row_h, k, bold=True)
        _rect(ax, k_w, ry, left_w - k_w, info_row_h)
        vv = str(v).strip() if v is not None and str(v).strip() else "—"
        _cell_text(ax, k_w, ry, left_w - k_w, info_row_h, vv)

    # 右侧统计表：标题 + 表头 + 5 类 + 合计
    st_title_h, st_head_h = 26, 26
    st_row_h = (head_section_h - st_title_h - st_head_h) / 6.0
    sx = left_w
    _rect(ax, sx, y0, right_w, st_title_h, HEADER_BG)
    _cell_text(ax, sx, y0, right_w, st_title_h, "统计表", fs=10, bold=True)
    st_col_w = [right_w * 0.32, right_w * 0.2, right_w * 0.25, right_w * 0.23]
    st_col_x = [sx + sum(st_col_w[:i]) for i in range(4)]
    hy = y0 + st_title_h
    for j, label in enumerate(["项别", "次数", "时间/s", "距离/m"]):
        _rect(ax, st_col_x[j], hy, st_col_w[j], st_head_h, HEADER_BG)
        _cell_text(ax, st_col_x[j], hy, st_col_w[j], st_head_h, label, fs=8.5, bold=True)
    stat_rows = [(SYMBOL_STAT[k], counts[k], _fmt(time_by[k]), _fmt(dist_by[k]))
                 for k in SYMBOL_ORDER]
    stat_rows.append(("合计", len(steps), _fmt(total_time), _fmt(total_dist)))
    for r, row in enumerate(stat_rows):
        ry = hy + st_head_h + r * st_row_h
        bold = r == len(stat_rows) - 1
        for j, v in enumerate(row):
            _rect(ax, st_col_x[j], ry, st_col_w[j], st_row_h,
                  LABEL_BG if bold else None)
            _cell_text(ax, st_col_x[j], ry, st_col_w[j], st_row_h, v, fs=8.5, bold=bold)

    # ---- 工序主表表头（双层）----
    y1 = y0 + head_section_h
    hh = head1_h + head2_h
    for ci, label in [(0, "序号"), (1, "工作说明"), (2, "时间/s"), (3, "距离/m"), (9, "备注")]:
        _rect(ax, col_x[ci], y1, col_w[ci], hh, HEADER_BG)
        _cell_text(ax, col_x[ci], y1, col_w[ci], hh, label, fs=9, bold=True)
    series_x, series_w = col_x[4], sum(col_w[4:9])
    _rect(ax, series_x, y1, series_w, head1_h, HEADER_BG)
    _cell_text(ax, series_x, y1, series_w, head1_h, "工序系列", fs=9, bold=True)
    for j, ci in enumerate(SYM_COLS):
        _rect(ax, col_x[ci], y1 + head1_h, col_w[ci], head2_h, HEADER_BG)
        _cell_text(ax, col_x[ci], y1 + head1_h, col_w[ci], head2_h,
                   SYMBOL_HEAD[SYMBOL_ORDER[j]], fs=8.5, bold=True)

    # ---- 数据行 ----
    row_y = [y1 + hh]
    for h in row_hs:
        row_y.append(row_y[-1] + h)

    line_pts = []
    for i, s in enumerate(steps):
        y, h = row_y[i], row_hs[i]
        c_lines, r_lines = row_lines[i]
        _rect(ax, col_x[0], y, col_w[0], h)
        _cell_text(ax, col_x[0], y, col_w[0], h, str(i + 1))
        _rect(ax, col_x[1], y, col_w[1], h)
        _cell_text(ax, col_x[1], y, col_w[1], h, "\n".join(c_lines))
        _rect(ax, col_x[2], y, col_w[2], h)
        _cell_text(ax, col_x[2], y, col_w[2], h, _fmt(s["time"]))
        _rect(ax, col_x[3], y, col_w[3], h)
        _cell_text(ax, col_x[3], y, col_w[3], h, _fmt(s["distance"]))
        for j, ci in enumerate(SYM_COLS):
            _rect(ax, col_x[ci], y, col_w[ci], h)
            sym = SYMBOL_ORDER[j]
            cx, cy = col_x[ci] + col_w[ci] / 2, y + h / 2
            selected = s["symbol"] == sym
            _draw_symbol(ax, sym, cx, cy, selected)
            if selected:
                line_pts.append((cx, cy))
        _rect(ax, col_x[9], y, col_w[9], h)
        _cell_text(ax, col_x[9], y, col_w[9], h, "\n".join(r_lines))

    # 经典锯齿连线：连接相邻步骤所选符号中心
    if len(line_pts) >= 2:
        ax.plot([p[0] for p in line_pts], [p[1] for p in line_pts],
                color=LINE_COLOR, linewidth=1.8, solid_joinstyle="miter",
                solid_capstyle="butt", zorder=5)

    # 外边框
    ax.add_patch(Rectangle((0, 0), W, H, facecolor="none", edgecolor=BORDER,
                           linewidth=1.4, zorder=6))

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "步骤总数": len(steps),
            "操作(○)次数": counts["processing"],
            "检查(□)次数": counts["inspection"],
            "搬运(→)次数": counts["transport"],
            "等待(D)次数": counts["waiting"],
            "储存(▽)次数": counts["storage"],
            "总时间(s)": _fmt(total_time),
            "总距离(m)": _fmt(total_dist),
        },
    }
