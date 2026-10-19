"""工艺程序图（IE 方法研究）服务端 matplotlib 生成器

版式贴近经典 IE 工艺程序图：右侧垂直主干串联 ○加工 / □检验 符号，
左侧平行分支线末端水平汇入主干；顶部标题 + 表头信息 + 汇总统计表。
坐标算法与 buildMxGraphXml.ts 保持一致（布局单位 ≈ px，y 轴向下）。
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

SCALE = 100.0          # 布局单位 → 英寸（100 单位 = 1 英寸）
STEP_PITCH = 88        # 相邻步骤中心间距
MERGE_GAP = 44         # 汇入点处主干额外间距
NODE_OP = 58           # ○ 加工符号直径
NODE_IN = 52           # □ 检验符号边长
ROW_H = 28             # 表头/汇总表行高

EDGE_COLOR = "#000000"


def _fmt_num(v) -> str:
    f = float(v)
    return str(int(f)) if f == int(f) else str(round(f, 2))


def _norm_step(raw, where: str) -> dict:
    if not isinstance(raw, dict):
        raise ChartValidationError(f"{where} 中的步骤必须是对象")
    kind = str(raw.get("kind", "operation") or "operation")
    if kind not in ("operation", "inspection"):
        raise ChartValidationError(f"{where} 中步骤的 kind 只能是 operation 或 inspection")
    try:
        time_min = float(raw.get("timeMin", 0) or 0)
    except (TypeError, ValueError):
        raise ChartValidationError(f"{where} 中步骤的 timeMin 必须是数字")
    return {
        "kind": kind,
        "badge": str(raw.get("badge", "") or ""),
        "timeMin": time_min,
        "label": str(raw.get("label", "") or ""),
    }


def _parse(params: dict) -> dict:
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")
    raw_main = params.get("mainSteps")
    if not isinstance(raw_main, list) or not raw_main:
        raise ChartValidationError("缺少主工艺线步骤 mainSteps")
    main_steps = [_norm_step(s, "mainSteps") for s in raw_main]

    header_raw = params.get("header") or {}
    if not isinstance(header_raw, dict):
        header_raw = {}
    header = {
        "productName": str(header_raw.get("productName", "") or ""),
        "department": str(header_raw.get("department", "") or ""),
        "researcher": str(header_raw.get("researcher", "") or ""),
        "date": str(header_raw.get("date", "") or ""),
    }

    summary_rows = []
    for r in params.get("summaryRows") or []:
        if not isinstance(r, dict):
            continue
        try:
            summary_rows.append({
                "label": str(r.get("label", "") or ""),
                "count": float(r.get("count", 0) or 0),
                "time": float(r.get("time", 0) or 0),
            })
        except (TypeError, ValueError):
            raise ChartValidationError("summaryRows 中 count/time 必须是数字")
    if not summary_rows:
        op_steps = [s for s in main_steps if s["kind"] == "operation"]
        in_steps = [s for s in main_steps if s["kind"] == "inspection"]
        summary_rows = [
            {"label": "加工", "count": len(op_steps), "time": sum(s["timeMin"] for s in op_steps)},
            {"label": "检验", "count": len(in_steps), "time": sum(s["timeMin"] for s in in_steps)},
        ]

    branches = []
    for b in params.get("branches") or []:
        if not isinstance(b, dict):
            continue
        steps = [_norm_step(s, "branches") for s in (b.get("steps") or [])]
        if not steps:
            continue
        try:
            merge_idx = int(b.get("mergeAfterMainIndex", 0) or 0)
        except (TypeError, ValueError):
            raise ChartValidationError("branches 中 mergeAfterMainIndex 必须是整数")
        branches.append({
            "title": str(b.get("title", "") or ""),
            "materialLine": str(b.get("materialLine", "") or ""),
            "steps": steps,
            "mergeLabel": str(b.get("mergeLabel", "") or ""),
            "mergeAfterMainIndex": max(0, min(merge_idx, len(main_steps) - 2)) if len(main_steps) >= 2 else 0,
            "column": "middle" if b.get("column") == "middle" else "left",
        })

    return {
        "header": header,
        "summaryRows": summary_rows,
        "mainTitle": str(params.get("mainTitle", "") or ""),
        "mainMaterialLine": str(params.get("mainMaterialLine", "") or ""),
        "mainSteps": main_steps,
        "branches": branches,
    }


def _arrow(ax, x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=EDGE_COLOR, lw=1.1,
                                shrinkA=0, shrinkB=0, mutation_scale=12))


def _place_step(ax, cx, cy, step):
    """画一个步骤符号：形内序号、左侧时间、右侧说明。返回 (top, bottom)。"""
    if step["kind"] == "operation":
        r = NODE_OP / 2
        ax.add_patch(Circle((cx, cy), r, facecolor="white", edgecolor=EDGE_COLOR, lw=1.4, zorder=3))
        half = r
    else:
        s = NODE_IN
        ax.add_patch(Rectangle((cx - s / 2, cy - s / 2), s, s,
                               facecolor="white", edgecolor=EDGE_COLOR, lw=1.4, zorder=3))
        half = s / 2
    ax.text(cx, cy, step["badge"], ha="center", va="center", fontsize=12,
            fontweight="bold", zorder=4)
    ax.text(cx - half - 8, cy, f'{_fmt_num(step["timeMin"])}min',
            ha="right", va="center", fontsize=10)
    ax.text(cx + half + 8, cy, step["label"], ha="left", va="center", fontsize=10)
    return cy - half, cy + half


def _banner(ax, cx, y_top, title, material):
    """列顶标题框 + 材料虚线。返回 (首步骤中心 y, 材料线锚点 y 或 None)。"""
    if title:
        ax.add_patch(Rectangle((cx - 78, y_top), 156, 28, facecolor="#f5f5f5",
                               edgecolor=EDGE_COLOR, lw=1.0, zorder=3))
        ax.text(cx, y_top + 14, title, ha="center", va="center", fontsize=11,
                fontweight="bold", zorder=4)
    mat_y = None
    if material:
        mat_y = y_top + 50
        ax.plot([cx - 80, cx], [mat_y, mat_y], color=EDGE_COLOR, lw=1.0,
                linestyle=(0, (6, 3)))
        ax.text(cx - 40, mat_y - 6, material, ha="center", va="bottom", fontsize=9)
    return y_top + 80 + 32, mat_y


def generate(params: dict) -> dict:
    setup_chinese_font()
    p = _parse(params)

    main_steps = p["mainSteps"]
    branches = p["branches"]
    nb = len(branches)

    # —— 水平布局（与 buildMxGraphXml.ts 一致）——
    col_gap = max(180, 220 - (nb - 1) * 10)
    left_margin = 60
    main_x = left_margin + nb * col_gap + (100 if nb > 0 else 160)
    frame_x, frame_y = 10, 4
    frame_w = max(main_x + 30 + 120 + 10 - frame_x, 600)
    branch_x = {i: left_margin + k * col_gap + 80 for k, i in enumerate(range(nb))}

    # —— 表头区 ——
    title_y = frame_y + 4
    hy = title_y + 36
    summary_rows = p["summaryRows"]
    header_rows = max(4, len(summary_rows) + 2)
    header_h = ROW_H * header_rows
    diagram_top = hy + header_h + 24

    # —— 主干步骤 y 坐标（汇入点处加 MERGE_GAP）——
    merge_set = {b["mergeAfterMainIndex"] for b in branches} if len(main_steps) >= 2 else set()
    main_first_cy = diagram_top + 80 + 32
    main_cys = []
    cy = main_first_cy
    for i in range(len(main_steps)):
        main_cys.append(cy)
        cy += STEP_PITCH
        if i in merge_set:
            cy += MERGE_GAP

    def node_half(step):
        return (NODE_OP if step["kind"] == "operation" else NODE_IN) / 2

    def merge_y(mi):
        lo = min(mi, len(main_steps) - 1)
        hi = lo + 1
        if hi >= len(main_steps):
            return main_cys[lo] + node_half(main_steps[lo]) + 24
        return (main_cys[lo] + node_half(main_steps[lo]) + main_cys[hi] - node_half(main_steps[hi])) / 2

    max_content_y = main_cys[-1] + node_half(main_steps[-1]) + 40
    for mi in merge_set:
        max_content_y = max(max_content_y, merge_y(mi) + 40)
    frame_h = max(400, max_content_y + 20 - frame_y)

    # —— 画布 ——
    total_w = frame_w + frame_x * 2
    total_h = frame_h + frame_y * 2 + 8
    fig, ax = plt.subplots(figsize=(total_w / SCALE, total_h / SCALE))
    ax.set_xlim(0, total_w)
    ax.set_ylim(total_h, 0)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.add_patch(FancyBboxPatch((frame_x, frame_y), frame_w, frame_h,
                                boxstyle="round,pad=0,rounding_size=8",
                                facecolor="white", edgecolor=EDGE_COLOR, lw=1.2, zorder=0))

    # —— 总标题 ——
    ax.text(frame_x + frame_w / 2, title_y + 16, "工艺程序图", ha="center", va="center",
            fontsize=16, fontweight="bold")

    # —— 左侧表头信息 ——
    h = p["header"]
    left_w = round(frame_w * 0.58)
    right_w = frame_w - left_w
    label_w = 88
    info = [("制品名称：", h["productName"]), ("工作部门：", h["department"]),
            ("研究者：", h["researcher"] or "—"), ("日期：", h["date"])]
    for i, (lab, val) in enumerate(info):
        ry = hy + i * ROW_H
        ax.add_patch(Rectangle((frame_x, ry), label_w, ROW_H, facecolor="#f8fafc",
                               edgecolor="#94a3b8", lw=0.8))
        ax.text(frame_x + 8, ry + ROW_H / 2, lab, ha="left", va="center",
                fontsize=10, fontweight="bold")
        ax.add_patch(Rectangle((frame_x + label_w, ry), left_w - label_w, ROW_H,
                               facecolor="white", edgecolor="#94a3b8", lw=0.8))
        ax.text(frame_x + label_w + 10, ry + ROW_H / 2, val, ha="left", va="center", fontsize=10)

    # —— 右侧汇总统计表 ——
    rx0 = frame_x + left_w
    col_ws = [round(right_w * 0.4), round(right_w * 0.3)]
    col_ws.append(right_w - sum(col_ws))
    total_count = sum(r["count"] for r in summary_rows)
    total_time = sum(r["time"] for r in summary_rows)
    table_rows = [(["内容", "次数", "时间"], "#f1f5f9", True)]
    for r in summary_rows:
        table_rows.append(([r["label"], _fmt_num(r["count"]), _fmt_num(r["time"])], "white", False))
    table_rows.append((["总和", _fmt_num(total_count), _fmt_num(total_time)], "#f1f5f9", True))
    for ri, (vals, fill, bold) in enumerate(table_rows):
        ry = hy + ri * ROW_H
        cx0 = rx0
        for ci in range(3):
            ax.add_patch(Rectangle((cx0, ry), col_ws[ci], ROW_H, facecolor=fill,
                                   edgecolor="#94a3b8", lw=0.8))
            ax.text(cx0 + col_ws[ci] / 2, ry + ROW_H / 2, vals[ci], ha="center", va="center",
                    fontsize=10, fontweight="bold" if bold else "normal")
            cx0 += col_ws[ci]

    # —— 主干 ——
    _, main_mat_y = _banner(ax, main_x, diagram_top, p["mainTitle"], p["mainMaterialLine"])
    prev_bottom = None
    for i, step in enumerate(main_steps):
        top, bottom = _place_step(ax, main_x, main_cys[i], step)
        if i == 0:
            if main_mat_y is not None:
                _arrow(ax, main_x, main_mat_y, main_x, top)
        else:
            _arrow(ax, main_x, prev_bottom, main_x, top)
        prev_bottom = bottom

    # —— 分支 + 汇入 ——
    for bi, br in enumerate(branches):
        bx = branch_x[bi]
        _, mat_y = _banner(ax, bx, diagram_top, br["title"], br["materialLine"])
        bcy = main_first_cy
        b_prev_bottom = None
        last_bottom = None
        for j, step in enumerate(br["steps"]):
            top, bottom = _place_step(ax, bx, bcy, step)
            if j == 0:
                if mat_y is not None:
                    _arrow(ax, bx, mat_y, bx, top)
            else:
                _arrow(ax, bx, b_prev_bottom, bx, top)
            b_prev_bottom = bottom
            last_bottom = bottom
            bcy += STEP_PITCH
        my = merge_y(br["mergeAfterMainIndex"])
        ax.plot([bx, bx], [last_bottom, my], color=EDGE_COLOR, lw=1.1)
        _arrow(ax, bx, my, main_x - 4, my)
        if br["mergeLabel"]:
            ax.text(bx + 6, my - 6, br["mergeLabel"], ha="left", va="bottom",
                    fontsize=9, style="italic")

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "步骤总数": len(main_steps) + sum(len(b["steps"]) for b in branches),
            "分支数": nb,
            "加工次数": _fmt_num(next((r["count"] for r in summary_rows if r["label"] == "加工"), 0)),
            "加工总时间(min)": _fmt_num(next((r["time"] for r in summary_rows if r["label"] == "加工"), 0)),
            "检验次数": _fmt_num(next((r["count"] for r in summary_rows if r["label"] == "检验"), 0)),
            "检验总时间(min)": _fmt_num(next((r["time"] for r in summary_rows if r["label"] == "检验"), 0)),
            "总时间(min)": _fmt_num(total_time),
        },
    }
