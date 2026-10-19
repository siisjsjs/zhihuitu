"""技术路线图生成器（服务端 matplotlib 静态出图）"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

STAGE_COLORS = ["#6c8ebf", "#d79b00", "#82b366", "#9673a6", "#b85450", "#2E75B6"]

# 版式常量（单位：英寸，坐标系 1 单位 = 1 英寸）
LABEL_W = 1.9       # 左侧阶段色带标签宽
CONTENT_W = 10.2    # 右侧泳道内容区宽
GAP_X = 0.25        # 标签与内容区间距
MARGIN = 0.35
TITLE_H = 0.7
STAGE_PAD = 0.35    # 泳道内边距
NODE_GAP_X = 0.55   # 节点水平间距
ROW_GAP = 0.6       # 节点行间距（留出箭头空间）
STAGE_GAP = 0.35    # 泳道之间间距

LABEL_FS = 10.5
DETAIL_FS = 8.5
STAGE_FS = 11.5
TITLE_FS = 16

LABEL_LH = 0.21     # label 行高（英寸）
DETAIL_LH = 0.165   # detail 行高
SEP_H = 0.12        # label 与 detail 之间分隔区高
PAD_V = 0.14        # 节点框上下内边距
PAD_H = 0.22        # 节点框左右内边距
NODE_W_MIN = 1.7
NODE_W_MAX = 3.1
MAX_DETAIL_LINES = 6

# 节点三种样式的底色/边框（default 用阶段色描边）
STYLE_FILLS = {"model": "#dae8fc", "result": "#d5e8d4"}
STYLE_EDGES = {"model": "#4472a8", "result": "#5a8f4d"}


def _char_w(ch: str, fs: float) -> float:
    """近似字符宽度（英寸）：CJK 全角约等于字号，ASCII 约 0.56 倍"""
    return (fs / 72.0) if ord(ch) > 127 else (0.56 * fs / 72.0)


def _text_w(text: str, fs: float) -> float:
    return sum(_char_w(ch, fs) for ch in text)


def _truncate(text: str, fs: float, max_w: float) -> str:
    if _text_w(text, fs) <= max_w:
        return text
    out, w = [], 0.0
    ell = _char_w("…", fs)
    for ch in text:
        cw = _char_w(ch, fs)
        if w + cw + ell > max_w:
            break
        out.append(ch)
        w += cw
    return "".join(out) + "…"


def _wrap(text: str, fs: float, max_w: float):
    """按估算宽度把一行文本折成多行"""
    lines, cur, w = [], [], 0.0
    for ch in text:
        cw = _char_w(ch, fs)
        if cur and w + cw > max_w:
            lines.append("".join(cur))
            cur, w = [], 0.0
        cur.append(ch)
        w += cw
    if cur:
        lines.append("".join(cur))
    return lines or [""]


def _parse_stages(raw):
    if not isinstance(raw, list) or not raw:
        raise ChartValidationError("stages 阶段列表不能为空，至少需要一个阶段")
    stages = []
    for i, s in enumerate(raw):
        if not isinstance(s, dict):
            raise ChartValidationError(f"第 {i + 1} 个阶段必须是对象")
        name = str(s.get("name") or f"第{i + 1}阶段")
        color = str(s.get("color") or STAGE_COLORS[i % len(STAGE_COLORS)]).strip()
        nodes = []
        for j, n in enumerate(s.get("nodes") or []):
            if not isinstance(n, dict):
                raise ChartValidationError(f"阶段「{name.splitlines()[0]}」的第 {j + 1} 个节点必须是对象")
            label = str(n.get("label") or "").strip()
            if not label:
                raise ChartValidationError(f"阶段「{name.splitlines()[0]}」的第 {j + 1} 个节点缺少 label")
            nodes.append({
                "id": str(n.get("id") or f"s{i}_n{j}"),
                "label": label,
                "detail": str(n.get("detail") or ""),
                "style": str(n.get("style") or "default"),
            })
        if not nodes:
            raise ChartValidationError(f"阶段「{name.splitlines()[0]}」至少需要一个节点")
        conns = []
        for c in (s.get("connections") or []):
            if isinstance(c, dict) and c.get("from") and c.get("to"):
                conns.append({"from": str(c["from"]), "to": str(c["to"])})
        stages.append({"name": name, "color": color, "nodes": nodes, "connections": conns})
    return stages


def _layout_node_text(node):
    """计算节点文本行与所需宽高，返回 (label_lines, detail_lines, w, h)"""
    inner_max = NODE_W_MAX - 2 * PAD_H
    label_lines = _wrap(node["label"], LABEL_FS, inner_max)
    detail_lines = []
    for ln in node["detail"].split("\n"):
        ln = ln.strip()
        if ln:
            detail_lines.append(_truncate(ln, DETAIL_FS, inner_max))
    if len(detail_lines) > MAX_DETAIL_LINES:
        detail_lines = detail_lines[:MAX_DETAIL_LINES - 1] + ["……"]

    content_w = max(
        [_text_w(l, LABEL_FS) for l in label_lines]
        + [_text_w(l, DETAIL_FS) for l in detail_lines]
        + [0.0]
    )
    w = min(max(content_w + 2 * PAD_H, NODE_W_MIN), NODE_W_MAX)
    h = 2 * PAD_V + len(label_lines) * LABEL_LH
    if detail_lines:
        h += SEP_H + len(detail_lines) * DETAIL_LH
    h = max(h, 0.52)
    return label_lines, detail_lines, w, h


def generate(params: dict) -> dict:
    setup_chinese_font()
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")

    title = str(params.get("title") or "技术路线图").strip()
    stages = _parse_stages(params.get("stages"))

    total_w = MARGIN * 2 + LABEL_W + GAP_X + CONTENT_W
    content_x = MARGIN + LABEL_W + GAP_X
    avail_w = CONTENT_W - 2 * STAGE_PAD

    # ── 第一遍：逐阶段做网格布局，算出所有节点的绝对位置 ──
    cur_y = MARGIN + TITLE_H + 0.15
    stage_geoms = []   # (stage, y_top, height)
    node_boxes = {}    # id -> dict(x, y, w, h, label_lines, detail_lines, style, color)
    for stage in stages:
        measured = [_layout_node_text(n) for n in stage["nodes"]]
        uw = max(m[2] for m in measured)
        uh = max(m[3] for m in measured)
        per_row = max(1, min(3, int((avail_w + NODE_GAP_X) // (uw + NODE_GAP_X))))
        n_rows = (len(stage["nodes"]) + per_row - 1) // per_row

        stage_h = 2 * STAGE_PAD + n_rows * uh + (n_rows - 1) * ROW_GAP
        y0 = cur_y + STAGE_PAD
        for idx, (node, m) in enumerate(zip(stage["nodes"], measured)):
            ri, ci = divmod(idx, per_row)
            n_in_row = min(per_row, len(stage["nodes"]) - ri * per_row)
            row_w = n_in_row * uw + (n_in_row - 1) * NODE_GAP_X
            x0 = content_x + STAGE_PAD + (avail_w - row_w) / 2
            node_boxes[node["id"]] = {
                "x": x0 + ci * (uw + NODE_GAP_X),
                "y": y0 + ri * (uh + ROW_GAP),
                "w": uw, "h": uh,
                "label_lines": m[0], "detail_lines": m[1],
                "style": node["style"], "color": stage["color"],
            }
        stage_geoms.append((stage, cur_y, stage_h))
        cur_y += stage_h + STAGE_GAP

    total_h = cur_y - STAGE_GAP + MARGIN

    # ── 绘制（y 轴向下） ──
    fig = plt.figure(figsize=(total_w, total_h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, total_w)
    ax.set_ylim(total_h, 0)
    ax.axis("off")

    ax.text(total_w / 2, MARGIN + TITLE_H / 2, title,
            ha="center", va="center", fontsize=TITLE_FS, fontweight="bold",
            color="#1f2937", wrap=True)

    for stage, sy, sh in stage_geoms:
        color = stage["color"]
        # 阶段标签色带（虚线边框）
        ax.add_patch(FancyBboxPatch(
            (MARGIN, sy), LABEL_W, sh,
            boxstyle="round,pad=0,rounding_size=0.06",
            facecolor="#f7f8fa", edgecolor=color, linewidth=1.4, linestyle=(0, (4, 3)),
            mutation_aspect=1, zorder=2))
        ax.text(MARGIN + LABEL_W / 2, sy + sh / 2, stage["name"],
                ha="center", va="center", fontsize=STAGE_FS, fontweight="bold",
                color=color, linespacing=1.5, zorder=3)
        # 泳道底色
        ax.add_patch(FancyBboxPatch(
            (content_x, sy), CONTENT_W, sh,
            boxstyle="round,pad=0,rounding_size=0.08",
            facecolor=color, alpha=0.08, edgecolor="none", zorder=1))
        ax.add_patch(FancyBboxPatch(
            (content_x, sy), CONTENT_W, sh,
            boxstyle="round,pad=0,rounding_size=0.08",
            facecolor="none", edgecolor=color, linewidth=1.0, alpha=0.55, zorder=2))

    # 节点框与文字
    for nb in node_boxes.values():
        style = nb["style"]
        face = STYLE_FILLS.get(style, "#ffffff")
        edge = STYLE_EDGES.get(style, nb["color"])
        rounding = 0.1 if style == "result" else 0.035
        ax.add_patch(FancyBboxPatch(
            (nb["x"], nb["y"]), nb["w"], nb["h"],
            boxstyle=f"round,pad=0,rounding_size={rounding}",
            facecolor=face, edgecolor=edge, linewidth=1.3, zorder=4))

        cx = nb["x"] + nb["w"] / 2
        n_label = len(nb["label_lines"])
        n_detail = len(nb["detail_lines"])
        block_h = n_label * LABEL_LH + ((SEP_H + n_detail * DETAIL_LH) if n_detail else 0)
        ty = nb["y"] + (nb["h"] - block_h) / 2
        for ln in nb["label_lines"]:
            ax.text(cx, ty + LABEL_LH / 2, ln, ha="center", va="center",
                    fontsize=LABEL_FS, fontweight="bold", color="#1f2937", zorder=5)
            ty += LABEL_LH
        if n_detail:
            sep_half = min(nb["w"] * 0.36, 1.0)
            ax.plot([cx - sep_half, cx + sep_half], [ty + SEP_H / 2] * 2,
                    color=edge, linewidth=0.7, alpha=0.6, zorder=5)
            ty += SEP_H
            for ln in nb["detail_lines"]:
                ax.text(cx, ty + DETAIL_LH / 2, ln, ha="center", va="center",
                        fontsize=DETAIL_FS, color="#4b5563", zorder=5)
                ty += DETAIL_LH

    # 连接箭头
    conn_drawn = 0
    for stage, _, _ in stage_geoms:
        for c in stage["connections"]:
            a = node_boxes.get(c["from"])
            b = node_boxes.get(c["to"])
            if a is None or b is None:
                continue
            acx, acy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2
            bcx, bcy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
            same_row = abs(acy - bcy) < 0.05
            adjacent = abs(bcx - acx) <= (a["w"] + b["w"]) / 2 + NODE_GAP_X + 0.05
            if same_row and not adjacent:
                # 同行跨节点：从顶边出发，弧线越过中间节点
                p0 = (acx, a["y"])
                p1 = (bcx, b["y"])
                d = max(abs(bcx - acx), 0.1)
                rad = -0.5 / d if bcx > acx else 0.5 / d
            elif same_row:
                if bcx > acx:
                    p0 = (a["x"] + a["w"], acy)
                    p1 = (b["x"], bcy)
                else:
                    p0 = (a["x"], acy)
                    p1 = (b["x"] + b["w"], bcy)
                rad = 0.0
            elif bcy > acy:
                p0 = (acx, a["y"] + a["h"])
                p1 = (bcx, b["y"])
                rad = 0.12 if abs(bcx - acx) > 0.3 else 0.0
            else:
                p0 = (acx, a["y"])
                p1 = (bcx, b["y"] + b["h"])
                rad = 0.12 if abs(bcx - acx) > 0.3 else 0.0
            ax.add_patch(FancyArrowPatch(
                p0, p1, arrowstyle="-|>", mutation_scale=13,
                connectionstyle=f"arc3,rad={rad}",
                color=stage["color"], linewidth=1.5,
                shrinkA=2, shrinkB=2, zorder=3))
            conn_drawn += 1

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "阶段数": len(stages),
            "节点总数": sum(len(s["nodes"]) for s in stages),
            "连接数": conn_drawn,
        },
    }
