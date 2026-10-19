"""动素分析图（Therblig Chart）生成器"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import re
from collections import Counter

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Ellipse, PathPatch
from matplotlib.path import Path
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

BORDER = "#777777"
HEADER_BG = "#e8e8e8"
TEXT_COLOR = "#333333"

# 18 个标准动素：代号 -> (中文名称, 类别)  类别: 1 有效 / 2 辅助 / 3 无效
# 图标 path 与 TherbligChart.vue 同源（viewBox 0 0 32 32）
THERBLIGS = {
    "TE": ("伸手", 1), "G": ("握取", 1), "TL": ("移物", 1), "P": ("定位", 1),
    "DA": ("拆卸", 1), "U": ("使用", 1), "A": ("装配", 1), "RL": ("放开", 1),
    "I": ("检查", 1),
    "Sh": ("寻找", 2), "F": ("发现", 2), "St": ("选择", 2), "Pn": ("思考", 2),
    "PP": ("预定位", 2),
    "H": ("持住", 3), "AD": ("可避免延迟", 3), "UD": ("不可避免延迟", 3), "R": ("休息", 3),
}
# 与前端组件同一套 SVG，服务端出图才能画出专属动素记号
THERBLIG_ICONS = {
    "TE": [("path", "M6 8 Q16 28 26 8")],
    "G": [("path", "M6 26 L6 12 Q6 2 16 2 Q26 2 26 12 L26 26")],
    "TL": [("path", "M4 8 Q16 32 28 8"), ("circle", 16, 17, 3)],
    "P": [("circle", 14, 11, 8), ("path", "M22 11 L22 24 Q22 30 10 30")],
    "DA": [("line", 6, 16, 26, 16), ("line", 13, 9, 11, 23), ("line", 21, 9, 19, 23)],
    "U": [("path", "M8 6 L8 20 Q8 28 16 28 Q24 28 24 20 L24 6")],
    "A": [("line", 6, 12, 26, 12), ("line", 6, 20, 26, 20),
          ("line", 12, 6, 12, 26), ("line", 20, 6, 20, 26)],
    "RL": [("path", "M4 24 Q16 0 28 24"), ("circle", 16, 15, 3)],
    "I": [("ellipse", 16, 16, 8, 11)],
    "Sh": [("path", "M4 18 Q16 6 28 18"), ("path", "M4 18 Q16 30 28 18"),
           ("path", "M22 13 Q17 18 22 23")],
    "F": [("ellipse", 16, 16, 12, 8), ("ellipse", 16, 16, 6, 8)],
    "St": [("line", 4, 16, 26, 16), ("polyline", (20, 10, 26, 16, 20, 22))],
    "Pn": [("circle", 14, 7, 5), ("path", "M9 7 L9 28 L24 28"),
           ("path", "M17 10 L20 13 L11 20 L9 16")],
    "PP": [("circle", 16, 9, 4.5), ("circle", 16, 22, 6.5)],
    "H": [("path", "M6 26 L6 14 Q6 4 16 4 Q26 4 26 14 L26 26"),
          ("line", 2, 26, 30, 26)],
    "AD": [("path", "M8 6 L8 22 L21 22"), ("circle", 24, 22, 3)],
    "UD": [("circle", 26, 16, 3), ("path", "M28 14 L14 4 L4 14 L6 16")],
    "R": [("ellipse", 12, 8, 7, 5), ("path", "M12 13 L12 18 L24 18 L24 28")],
}
_UPPER_INDEX = {k.upper(): k for k in THERBLIGS}
_ALIASES = {"D": "UD"}  # 常见简写兼容

CLASS_DOT = {1: "#22c55e", 2: "#f59e0b", 3: "#ef4444"}
CLASS_NAMES = {1: "第一类（有效动素）", 2: "第二类（辅助动素）", 3: "第三类（无效动素）"}
_SVG_TOKEN = re.compile(
    r"[MmLlHhVvCcQqTtSsAaZz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?"
)


def _lookup(code):
    code = str(code or "").strip()
    if not code:
        return None
    up = code.upper()
    up = _ALIASES.get(up, up)
    key = _UPPER_INDEX.get(up)
    if key:
        name, cls = THERBLIGS[key]
        return {"id": key, "name": name, "cls": cls}
    return {"id": code, "name": "", "cls": None}


def _tw(s, fs):
    """估算文本宽度（pt），CJK 按全宽、ASCII 按 0.55 宽"""
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
    if not text:
        return
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, color=color,
            fontweight="bold" if bold else "normal", zorder=3)


def _svg_tokens(d: str):
    for tok in _SVG_TOKEN.findall(d):
        if tok.isalpha():
            yield tok, None
        else:
            yield None, float(tok)


def _svg_path_to_mpl(d: str):
    """把前端 SVG path d 转成 matplotlib Path（viewBox 0 0 32 32）。"""
    verts, codes = [], []
    cx = cy = 0.0
    sx = sy = 0.0
    last_cmd = ""
    tokens = list(_svg_tokens(d))
    i = 0

    def take(n):
        nonlocal i
        out = []
        while len(out) < n and i < len(tokens):
            cmd, val = tokens[i]
            if cmd is not None:
                break
            out.append(val)
            i += 1
        return out if len(out) == n else None

    while i < len(tokens):
        cmd, val = tokens[i]
        if cmd is not None:
            last_cmd = cmd
            i += 1
        elif last_cmd:
            cmd = last_cmd
        else:
            i += 1
            continue
        rel = cmd.islower()
        c = cmd.lower()
        if c == "z":
            verts.append((sx, sy))
            codes.append(Path.CLOSEPOLY)
            cx, cy = sx, sy
            continue
        if c == "m":
            pair = take(2)
            if not pair:
                break
            nx, ny = pair
            if rel:
                nx += cx
                ny += cy
            cx, cy = nx, ny
            sx, sy = nx, ny
            verts.append((cx, cy))
            codes.append(Path.MOVETO)
            last_cmd = "l" if rel else "L"
            continue
        if c == "l":
            pair = take(2)
            if not pair:
                break
            nx, ny = pair
            if rel:
                nx += cx
                ny += cy
            cx, cy = nx, ny
            verts.append((cx, cy))
            codes.append(Path.LINETO)
            continue
        if c == "h":
            vals = take(1)
            if not vals:
                break
            cx = cx + vals[0] if rel else vals[0]
            verts.append((cx, cy))
            codes.append(Path.LINETO)
            continue
        if c == "v":
            vals = take(1)
            if not vals:
                break
            cy = cy + vals[0] if rel else vals[0]
            verts.append((cx, cy))
            codes.append(Path.LINETO)
            continue
        if c == "q":
            pts = take(4)
            if not pts:
                break
            x1, y1, x, y = pts
            if rel:
                x1 += cx
                y1 += cy
                x += cx
                y += cy
            verts.append((x1, y1))
            codes.append(Path.CURVE3)
            verts.append((x, y))
            codes.append(Path.CURVE3)
            cx, cy = x, y
            continue
        if c == "c":
            pts = take(6)
            if not pts:
                break
            x1, y1, x2, y2, x, y = pts
            if rel:
                x1 += cx
                y1 += cy
                x2 += cx
                y2 += cy
                x += cx
                y += cy
            verts.extend([(x1, y1), (x2, y2), (x, y)])
            codes.extend([Path.CURVE4, Path.CURVE4, Path.CURVE4])
            cx, cy = x, y
            continue
        i += 1
    if not verts:
        return None
    return Path(verts, codes)


def _map_xy(px, py, ox, oy, scale):
    return ox + px * scale, oy + py * scale


def _stroke(color, lw):
    return dict(facecolor="none", edgecolor=color, linewidth=lw,
                capstyle="round", joinstyle="round", zorder=4)


def _draw_icon(ax, code, ox, oy, size, color):
    """在 (ox, oy) 处画边长 size 的动素记号，坐标系与前端 SVG 一致。"""
    scale = size / 32.0
    lw = max(1.15, 2.4 * scale)
    for item in THERBLIG_ICONS.get(code, ()):
        kind = item[0]
        if kind == "path":
            path = _svg_path_to_mpl(item[1])
            if path is None:
                continue
            verts = [_map_xy(x, y, ox, oy, scale) for x, y in path.vertices]
            ax.add_patch(PathPatch(Path(verts, path.codes), **_stroke(color, lw)))
        elif kind == "circle":
            _, cx, cy, r = item
            ax.add_patch(Circle(_map_xy(cx, cy, ox, oy, scale), r * scale,
                                **_stroke(color, lw)))
        elif kind == "ellipse":
            _, cx, cy, rx, ry = item
            mx, my = _map_xy(cx, cy, ox, oy, scale)
            ax.add_patch(Ellipse((mx, my), rx * 2 * scale, ry * 2 * scale,
                                 **_stroke(color, lw)))
        elif kind == "line":
            _, x1, y1, x2, y2 = item
            ax.plot(*zip(_map_xy(x1, y1, ox, oy, scale),
                         _map_xy(x2, y2, ox, oy, scale)),
                    color=color, linewidth=lw, solid_capstyle="round", zorder=4)
        elif kind == "polyline":
            pts = [_map_xy(item[1][i], item[1][i + 1], ox, oy, scale)
                   for i in range(0, len(item[1]), 2)]
            ax.plot(*zip(*pts), color=color, linewidth=lw,
                    solid_capstyle="round", solid_joinstyle="round", zorder=4)


def _draw_therblig_chip(ax, x, y, w, h, code):
    """单元格内：专属记号 + 中文名，与前端 TherbligChart 一致。"""
    info = _lookup(code)
    if info is None:
        return
    cx, cy = x + w / 2, y + h / 2
    if info["cls"] is None:
        ax.text(cx, cy, info["id"], ha="center", va="center",
                fontsize=8, color="#666666", zorder=3)
        return
    color = CLASS_DOT[info["cls"]]
    icon = 13.5
    gap = 2.0
    name = info["name"]
    fs = 7.5
    name_w = _tw(name, fs)
    total = icon + gap + name_w
    left = cx - total / 2
    _draw_icon(ax, info["id"], left, cy - icon / 2, icon, color)
    ax.text(left + icon + gap, cy, name, ha="left", va="center",
            fontsize=fs, color=color, fontweight="bold", zorder=3)


def generate(params: dict) -> dict:
    setup_chinese_font()
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")
    raw_steps = params.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ChartValidationError("steps 不能为空，至少需要一个动素步骤")

    steps = []
    for i, s in enumerate(raw_steps):
        if not isinstance(s, dict):
            raise ChartValidationError(f"第 {i + 1} 个步骤必须是对象")
        steps.append({
            "elementWork": str(s.get("elementWork") or "").strip(),
            "leftAction": str(s.get("leftAction") or "").strip(),
            "leftTherblig": str(s.get("leftTherblig") or "").strip(),
            "eyeTherblig": str(s.get("eyeTherblig") or "").strip(),
            "rightTherblig": str(s.get("rightTherblig") or "").strip(),
            "rightAction": str(s.get("rightAction") or "").strip(),
            "improvement": str(s.get("improvement") or "").strip(),
        })
    if not any(s["leftTherblig"] or s["rightTherblig"] or s["eyeTherblig"] for s in steps):
        raise ChartValidationError("所有步骤均未填写动素代号，无法绘制动素分析图")

    # ---- 布局（单位：pt，1 单位 = 1/72 英寸）----
    # 列：序号 | 要素作业 | 左手动作 | 左手 | 眼 | 右手 | 右手动作 | 改善点
    col_w = [34, 100, 132, 78, 78, 78, 132, 92]
    W = sum(col_w)
    col_x = [sum(col_w[:i]) for i in range(len(col_w))]

    fs_cell = 9
    # 每行按需换行并计算行高
    row_lines = []
    row_hs = []
    for s in steps:
        la = _wrap(s["leftAction"], fs_cell, col_w[2] - 10)
        ra = _wrap(s["rightAction"], fs_cell, col_w[6] - 10)
        im = _wrap(s["improvement"], fs_cell, col_w[7] - 10)
        row_lines.append((la, ra, im))
        n = max(len(la), len(ra), len(im))
        row_hs.append(max(30, 14 * n + 12))

    title_h, head1_h, head2_h = 34, 22, 20
    stats_title_h, stats_head_h, stats_row_h = 26, 24, 24
    H = title_h + head1_h + head2_h + sum(row_hs) + stats_title_h + stats_head_h + 3 * stats_row_h

    fig = plt.figure(figsize=(W / 72, H / 72))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    # 标题
    _rect(ax, 0, 0, W, title_h)
    ax.text(W / 2, title_h / 2, "动素分析图", ha="center", va="center",
            fontsize=13, color=TEXT_COLOR, fontweight="bold", zorder=3)

    # 双层表头
    y1 = title_h
    hh = head1_h + head2_h
    headers_span2 = [(0, "序号"), (1, "要素作业"), (2, "左手动作"), (6, "右手动作"), (7, "改善点")]
    for ci, label in headers_span2:
        _rect(ax, col_x[ci], y1, col_w[ci], hh, HEADER_BG)
        _cell_text(ax, col_x[ci], y1, col_w[ci], hh, label, fs=9.5, bold=True)
    sym_x, sym_w = col_x[3], col_w[3] + col_w[4] + col_w[5]
    _rect(ax, sym_x, y1, sym_w, head1_h, HEADER_BG)
    _cell_text(ax, sym_x, y1, sym_w, head1_h, "动素记号", fs=9.5, bold=True)
    for ci, label in [(3, "左手"), (4, "眼"), (5, "右手")]:
        _rect(ax, col_x[ci], y1 + head1_h, col_w[ci], head2_h, HEADER_BG)
        _cell_text(ax, col_x[ci], y1 + head1_h, col_w[ci], head2_h, label, fs=8.5, bold=True)

    # 要素作业合并分组：非空开新组；空白或同名延续上一组
    groups = []
    for i, s in enumerate(steps):
        w = s["elementWork"]
        if groups and (w == "" or w == groups[-1]["label"]):
            groups[-1]["span"] += 1
        else:
            groups.append({"start": i, "span": 1, "label": w})

    # 数据行
    row_y = [title_h + hh]
    for h in row_hs:
        row_y.append(row_y[-1] + h)

    for i, s in enumerate(steps):
        y, h = row_y[i], row_hs[i]
        la, ra, im = row_lines[i]
        _rect(ax, col_x[0], y, col_w[0], h)
        _cell_text(ax, col_x[0], y, col_w[0], h, str(i + 1))
        for ci, lines in [(2, la), (6, ra), (7, im)]:
            _rect(ax, col_x[ci], y, col_w[ci], h)
            _cell_text(ax, col_x[ci], y, col_w[ci], h, "\n".join(lines))
        for ci, key in [(3, "leftTherblig"), (4, "eyeTherblig"), (5, "rightTherblig")]:
            _rect(ax, col_x[ci], y, col_w[ci], h)
            _draw_therblig_chip(ax, col_x[ci], y, col_w[ci], h, s[key])

    # 要素作业列（按组合并绘制）
    for g in groups:
        y = row_y[g["start"]]
        h = sum(row_hs[g["start"]:g["start"] + g["span"]])
        _rect(ax, col_x[1], y, col_w[1], h)
        if g["label"]:
            lines = _wrap(g["label"], fs_cell, col_w[1] - 10)
            _cell_text(ax, col_x[1], y, col_w[1], h, "\n".join(lines))

    # ---- 统计汇总 ----
    class_counts = {"left": Counter(), "eye": Counter(), "right": Counter()}
    code_counts = {"left": Counter(), "eye": Counter(), "right": Counter()}
    for s in steps:
        for hand, key in [("left", "leftTherblig"), ("eye", "eyeTherblig"), ("right", "rightTherblig")]:
            info = _lookup(s[key])
            if info and info["cls"]:
                class_counts[hand][info["cls"]] += 1
                code_counts[hand][f'{info["id"]}{info["name"]}'] += 1

    sy = row_y[-1]
    _rect(ax, 0, sy, W, stats_title_h)
    ax.text(W / 2, sy + stats_title_h / 2, "动素统计汇总", ha="center", va="center",
            fontsize=10.5, color=TEXT_COLOR, fontweight="bold", zorder=3)

    label_w = W - 3 * 100
    scol_w = [label_w, 100, 100, 100]
    scol_x = [sum(scol_w[:i]) for i in range(4)]
    hy = sy + stats_title_h
    for j, label in enumerate(["动素类别", "左手", "眼", "右手"]):
        _rect(ax, scol_x[j], hy, scol_w[j], stats_head_h, HEADER_BG)
        _cell_text(ax, scol_x[j], hy, scol_w[j], stats_head_h, label, fs=9, bold=True)
    for k, cls in enumerate([1, 2, 3]):
        ry = hy + stats_head_h + k * stats_row_h
        _rect(ax, scol_x[0], ry, scol_w[0], stats_row_h)
        name = CLASS_NAMES[cls]
        tx = scol_x[0] + scol_w[0] / 2
        ax.text(tx + 6, ry + stats_row_h / 2, name, ha="center", va="center",
                fontsize=9, color=TEXT_COLOR, zorder=3)
        ax.add_patch(Circle((tx + 6 - _tw(name, 9) / 2 - 9, ry + stats_row_h / 2), 3.6,
                            facecolor=CLASS_DOT[cls], edgecolor="none", zorder=3))
        for j, hand in enumerate(["left", "eye", "right"]):
            _rect(ax, scol_x[j + 1], ry, scol_w[j + 1], stats_row_h)
            _cell_text(ax, scol_x[j + 1], ry, scol_w[j + 1], stats_row_h,
                       str(class_counts[hand][cls]))

    # 外边框
    ax.add_patch(Rectangle((0, 0), W, H, facecolor="none", edgecolor=BORDER,
                           linewidth=1.4, zorder=4))

    # ---- summary ----
    def _dist(counter):
        if not counter:
            return "无"
        return "、".join(f"{k}×{v}" for k, v in counter.items())

    total_all = sum(sum(c.values()) for c in class_counts.values())
    total_by_cls = {cls: sum(c[cls] for c in class_counts.values()) for cls in (1, 2, 3)}
    ineffective_pct = (total_by_cls[3] / total_all * 100) if total_all else 0.0

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "总步数": len(steps),
            "左手动素分布": _dist(code_counts["left"]),
            "眼动素分布": _dist(code_counts["eye"]),
            "右手动素分布": _dist(code_counts["right"]),
            "有效动素数(第一类)": total_by_cls[1],
            "辅助动素数(第二类)": total_by_cls[2],
            "无效动素数(第三类)": total_by_cls[3],
            "无效动素占比": f"{ineffective_pct:.1f}%",
        },
    }
