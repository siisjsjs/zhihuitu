"""价值流程图（VSM）服务端 matplotlib 生成器

标准精益 VSM 三区版式（坐标算法参照 vsmLayout.ts，做了合理简化：卡车用粗物流箭头代替）：
  信息流（上）：供应商 / 生产控制 / 客户 工厂图标 + 锯齿电子信息流 + 计划下达箭头
  物料流（中）：工序框（按 next 有向图分列分车道）+ 数据小格 + 库存三角 ▽ + 推动粗箭头 + 改善爆炸点
  时间线（下）：阶梯线（上凸=库存天数、下凹=工序 C/T）+ 右端汇总 + 节拍/汇总框
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyArrow
from _utils import setup_chinese_font, figure_to_base64, ChartValidationError

SCALE = 100.0        # 布局单位 → 英寸
PROC_W = 150
PROC_H = 54
PROC_PITCH = 300     # 相邻工序列中心间距
MATERIAL_Y = 300     # 首车道工序框顶 Y
DATA_ROW_H = 22
DATA_ROWS = 5        # C/T、C/O、人数、可用率、良品率
TRI_HALF = 24
INFO_TOP = 56
CONTROL_W = 180
ENDBOX_W = 150
ENDBOX_H = 64
FIRST_PROC_CX = 480
END_OFFSET = 380     # 供应商/客户中心距最近工序列中心
KAIZEN_LIFT = 64
LANE_PITCH = PROC_H + 30 + DATA_ROW_H * DATA_ROWS + KAIZEN_LIFT + 40

EDGE = "#111111"


def _num(v, default=0.0):
    try:
        n = float(v)
        return n if math.isfinite(n) else default
    except (TypeError, ValueError):
        return default


def _fmt(v):
    f = float(v)
    return str(int(f)) if f == int(f) else str(round(f, 2))


def _fmt_min(m):
    m = _num(m)
    if not m:
        return "0"
    if m >= 60:
        h, r = int(m // 60), m % 60
        return f"{h}h{_fmt(r)}min" if r else f"{h}h"
    return f"{_fmt(m)}min"


def _parse(params: dict) -> dict:
    if not isinstance(params, dict):
        raise ChartValidationError("参数必须是对象")
    raw_procs = params.get("processes")
    if not isinstance(raw_procs, list) or not raw_procs:
        raise ChartValidationError("缺少工序数据 processes")
    procs = []
    for i, s in enumerate(raw_procs):
        if not isinstance(s, dict):
            raise ChartValidationError("processes 中每个工序必须是对象")
        procs.append({
            "id": str(s.get("id") or f"p{i + 1}"),
            "name": str(s.get("name") or f"工序{i + 1}"),
            "cycleTime": _num(s.get("cycleTime")),
            "changeover": _num(s.get("changeover")),
            "operators": _num(s.get("operators"), 1),
            "uptime": _num(s.get("uptime"), 100),
            "firstYield": _num(s.get("firstYield"), 100),
            "next": [str(x) for x in s.get("next") or []],
        })
    valid_ids = {s["id"] for s in procs}
    for s in procs:
        s["next"] = [nx for nx in s["next"] if nx in valid_ids and nx != s["id"]]

    n = len(procs)
    clamp = lambda v: max(-1, min(int(_num(v, -1)), n))
    inventories = [{
        "afterIndex": clamp(iv.get("afterIndex")),
        "qty": _num(iv.get("qty")),
        "days": _num(iv.get("days")),
        "invType": iv.get("invType") if iv.get("invType") in ("inventory", "supermarket", "fifo") else "inventory",
    } for iv in params.get("inventories") or [] if isinstance(iv, dict)]
    info_flows = [{
        "toId": str(f.get("toId") or ""),
        "label": str(f.get("label") or ""),
    } for f in params.get("infoFlows") or [] if isinstance(f, dict)]
    kaizens = [{
        "afterIndex": clamp(k.get("afterIndex")),
        "label": str(k.get("label") or ""),
    } for k in params.get("kaizens") or [] if isinstance(k, dict)]

    cust = params.get("customer") or {}
    supp = params.get("supplier") or {}
    ctrl = params.get("control") or {}
    return {
        "title": str(params.get("title") or "价值流程图"),
        "customer": {
            "name": str(cust.get("name") or "客户"),
            "dailyDemand": _num(cust.get("dailyDemand")),
            "unit": str(cust.get("unit") or "件"),
            "deliveryFreq": str(cust.get("deliveryFreq") or ""),
            "infoLabel": str(cust.get("infoLabel") or "月客户订单"),
        },
        "supplier": {
            "name": str(supp.get("name") or "供应商"),
            "deliveryFreq": str(supp.get("deliveryFreq") or ""),
            "infoLabel": str(supp.get("infoLabel") or "月采购订单"),
        },
        "control": {"name": str(ctrl.get("name") or "生产控制 / MRP")},
        "processes": procs,
        "inventories": inventories,
        "infoFlows": info_flows,
        "kaizens": kaizens,
        "workingTimePerDay": _num(params.get("workingTimePerDay")),
        "showTakt": params.get("showTakt") is not False,
    }


# ---------------- 图元绘制 ----------------

def _factory_box(ax, cx, y, w, h, label):
    """VSM 工厂图标：矩形 + 锯齿屋顶"""
    x = cx - w / 2
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#f8fafc", edgecolor=EDGE, lw=1.4, zorder=3))
    roof_h, teeth = 14, 3
    tw = w / teeth
    pts = [(x, y)]
    for t in range(teeth):
        pts.append((x + t * tw + tw * 0.55, y - roof_h))
        pts.append((x + (t + 1) * tw, y))
    ax.add_patch(Polygon(pts, closed=True, facecolor="#e2e8f0", edgecolor=EDGE, lw=1.2, zorder=3))
    ax.text(cx, y + h / 2, label, ha="center", va="center", fontsize=11, fontweight="bold", zorder=4)


def _plain_box(ax, cx, y, w, h, label, fill="#ffffff", fontsize=11, bold=True):
    ax.add_patch(Rectangle((cx - w / 2, y), w, h, facecolor=fill, edgecolor=EDGE, lw=1.4, zorder=3))
    ax.text(cx, y + h / 2, label, ha="center", va="center", fontsize=fontsize,
            fontweight="bold" if bold else "normal", zorder=4)


def _lightning_pts(x1, x2, y, amp=6):
    span = abs(x2 - x1)
    if span < 24:
        return []
    d = 1 if x2 >= x1 else -1
    teeth = max(3, round(span / 42))
    step = span / teeth
    return [(x1 + d * step * i, y + (-amp if i % 2 == 1 else amp)) for i in range(1, teeth)]


def _polyline_arrow(ax, pts, lw=1.6, color=EDGE, zorder=2):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=lw, zorder=zorder, solid_joinstyle="miter")
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                shrinkA=0, shrinkB=0, mutation_scale=15), zorder=zorder)


def _push_arrow(ax, x1, x2, y):
    """推动式物流粗箭头（白底斜纹）"""
    body = max(x2 - x1 - 16, 8)
    ax.add_patch(FancyArrow(x1, y, body + 16, 0, width=12, head_width=24, head_length=16,
                            length_includes_head=True, facecolor="white", edgecolor=EDGE,
                            lw=1.3, hatch="////", zorder=2))


def _inventory_tri(ax, cx, mid_y, qty, days, inv_type):
    tip_y = mid_y - 4
    top_y = tip_y - TRI_HALF * 2
    ax.add_patch(Polygon([(cx - TRI_HALF, top_y), (cx + TRI_HALF, top_y), (cx, tip_y)],
                         closed=True, facecolor="#fff7ed", edgecolor=EDGE, lw=1.3, zorder=3))
    mark = {"inventory": "I", "supermarket": "超市", "fifo": "FIFO"}[inv_type]
    ax.text(cx, top_y + TRI_HALF * 0.62, mark, ha="center", va="center",
            fontsize=10, fontweight="bold", zorder=4)
    lines = []
    if qty:
        lines.append(f"{_fmt(qty)}件")
    if days:
        lines.append(f"{_fmt(days)}天")
    if lines:
        ax.text(cx, mid_y + 12, "\n".join(lines), ha="center", va="top", fontsize=9, zorder=4)


def _kaizen_burst(ax, cx, cy, label):
    n, r_out, r_in = 12, 48, 30
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi / n * i - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    ax.add_patch(Polygon(pts, closed=True, facecolor="#fef08a", edgecolor="#b45309",
                         lw=1.4, zorder=5))
    text = label
    if len(text) > 4:
        mid = (len(text) + 1) // 2
        text = text[:mid] + "\n" + text[mid:]
    ax.text(cx, cy, text, ha="center", va="center", fontsize=8.5, zorder=6, color="#7c2d12")


# ---------------- 主入口 ----------------

def generate(params: dict) -> dict:
    setup_chinese_font()
    p = _parse(params)
    procs = p["processes"]
    n_proc = len(procs)
    idx_of = {s["id"]: i for i, s in enumerate(procs)}

    # —— 有向图 / 列深度 / 车道 ——
    has_graph = any(s["next"] for s in procs)
    succ = {s["id"]: [] for s in procs}
    pred = {s["id"]: [] for s in procs}
    if has_graph:
        for s in procs:
            for nx in s["next"]:
                succ[s["id"]].append(nx)
                pred[nx].append(s["id"])
    else:
        for i in range(n_proc - 1):
            succ[procs[i]["id"]].append(procs[i + 1]["id"])
            pred[procs[i + 1]["id"]].append(procs[i]["id"])

    depth_memo, visiting = {}, set()

    def depth_of(pid):
        if pid in depth_memo:
            return depth_memo[pid]
        if pid in visiting:
            return 0
        visiting.add(pid)
        d = max((depth_of(u) + 1 for u in pred[pid]), default=0)
        visiting.discard(pid)
        depth_memo[pid] = d
        return d

    for s in procs:
        depth_of(s["id"])
    max_depth = max(depth_memo.values())
    by_depth = {}
    for s in procs:
        by_depth.setdefault(depth_memo[s["id"]], []).append(s["id"])
    lane_of = {pid: k for ids in by_depth.values() for k, pid in enumerate(ids)}

    col_cx = lambda d: FIRST_PROC_CX + d * PROC_PITCH
    proc_cx = lambda pid: col_cx(depth_memo[pid])
    proc_top = lambda pid: MATERIAL_Y + lane_of[pid] * LANE_PITCH
    roots = [s["id"] for s in procs if not pred[s["id"]]]
    leaves = [s["id"] for s in procs if not succ[s["id"]]]
    last_cx = col_cx(max_depth)
    customer_cx = last_cx + END_OFFSET
    supplier_cx = FIRST_PROC_CX - END_OFFSET
    control_cx = (supplier_cx + customer_cx) / 2
    base_tri_y = MATERIAL_Y + PROC_H / 2

    max_lane = max(lane_of.values())
    proc_band_bottom = MATERIAL_Y + max_lane * LANE_PITCH + PROC_H
    timeline_y = proc_band_bottom + 30 + DATA_ROW_H * DATA_ROWS + 100

    # —— 汇总计算（关键路径 = 沿途 C/T 之和最大）——
    va_tail, best_next = {}, {}
    for s in sorted(procs, key=lambda x: -depth_memo[x["id"]]):
        best, best_id = -1.0, ""
        for v in succ[s["id"]]:
            t = va_tail.get(v, 0.0)
            if t > best:
                best, best_id = t, v
        if best_id:
            best_next[s["id"]] = best_id
        va_tail[s["id"]] = s["cycleTime"] + (best if best >= 0 else 0)
    head = max(roots, key=lambda r: va_tail.get(r, 0), default=procs[0]["id"])
    crit = []
    cur = head
    while cur:
        crit.append(procs[idx_of[cur]])
        cur = best_next.get(cur, "")
    va_sec = sum(s["cycleTime"] for s in crit)
    lead_days = sum(iv["days"] for iv in p["inventories"])
    va_days = va_sec / 86400.0
    total_days = lead_days + va_days
    pce = (va_days / total_days * 100) if total_days > 0 else 0.0
    takt = (p["workingTimePerDay"] / p["customer"]["dailyDemand"]
            if p["showTakt"] and p["customer"]["dailyDemand"] > 0 and p["workingTimePerDay"] > 0 else None)

    # —— 画布范围 ——
    side_w = 140
    min_x = supplier_cx - ENDBOX_W / 2 - side_w - 20
    max_x = max(customer_cx + ENDBOX_W / 2 + side_w + 20, customer_cx - ENDBOX_W / 2 + 240)
    min_y, max_y = -70, timeline_y + 170
    fig, ax = plt.subplots(figsize=((max_x - min_x) / SCALE, (max_y - min_y) / SCALE))
    ax.set_xlim(min_x, max_x)
    ax.set_ylim(max_y, min_y)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text((min_x + max_x) / 2, min_y + 24, p["title"], ha="center", va="center",
            fontsize=17, fontweight="bold")

    # ===== 信息流区（上）=====
    _factory_box(ax, supplier_cx, INFO_TOP, ENDBOX_W, ENDBOX_H, p["supplier"]["name"])
    _factory_box(ax, customer_cx, INFO_TOP, ENDBOX_W, ENDBOX_H, p["customer"]["name"])
    _plain_box(ax, control_cx, INFO_TOP, CONTROL_W, ENDBOX_H, p["control"]["name"], fill="#eff6ff")

    cust_info = "  ".join(x for x in [
        f'{_fmt(p["customer"]["dailyDemand"])} {p["customer"]["unit"]}/天' if p["customer"]["dailyDemand"] else "",
        p["customer"]["deliveryFreq"]] if x)
    if cust_info:
        ax.text(customer_cx + ENDBOX_W / 2 + 12, INFO_TOP + ENDBOX_H / 2, cust_info,
                ha="left", va="center", fontsize=10)
    if p["supplier"]["deliveryFreq"]:
        ax.text(supplier_cx - ENDBOX_W / 2 - 12, INFO_TOP + ENDBOX_H / 2,
                p["supplier"]["deliveryFreq"], ha="right", va="center", fontsize=10)

    # 主干信息流：控制 → 供应商（采购订单）；客户 → 控制（客户订单），锯齿电子信息流
    info_lane_y = INFO_TOP - 30
    sup_lane_x = control_cx - 36
    pts = [(sup_lane_x, INFO_TOP), (sup_lane_x, info_lane_y)]
    pts += _lightning_pts(sup_lane_x, supplier_cx, info_lane_y)
    pts += [(supplier_cx, info_lane_y), (supplier_cx, INFO_TOP - 14)]
    _polyline_arrow(ax, pts, lw=1.6)
    ax.text((sup_lane_x + supplier_cx) / 2, info_lane_y - 12, p["supplier"]["infoLabel"],
            ha="center", va="bottom", fontsize=10)
    cus_lane_x = control_cx + 36
    pts = [(customer_cx, INFO_TOP - 14), (customer_cx, info_lane_y)]
    pts += _lightning_pts(customer_cx, cus_lane_x, info_lane_y)
    pts += [(cus_lane_x, info_lane_y), (cus_lane_x, INFO_TOP)]
    _polyline_arrow(ax, pts, lw=1.6)
    ax.text((cus_lane_x + customer_cx) / 2, info_lane_y - 12, p["customer"]["infoLabel"],
            ha="center", va="bottom", fontsize=10)

    # 控制 → 工序：计划下达箭头
    control_bottom = INFO_TOP + ENDBOX_H
    for f in p["infoFlows"]:
        if f["toId"] not in idx_of:
            continue
        tx, ty = proc_cx(f["toId"]), proc_top(f["toId"])
        # 落点偏向控制框一侧，避开工序正上方的改善爆炸点
        land_x = tx + (PROC_W / 2 - 25) * (1 if control_cx > tx else -1) if control_cx != tx else tx
        _polyline_arrow(ax, [(control_cx, control_bottom), (land_x, ty)], lw=1.3)
        mx, my_ = (control_cx + land_x) / 2, (control_bottom + ty) / 2
        ax.text(mx, my_, f["label"], ha="center", va="center", fontsize=9.5,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#94a3b8", lw=0.7),
                zorder=6)

    # ===== 物料流区（中）=====
    for s in procs:
        cx, top = proc_cx(s["id"]), proc_top(s["id"])
        _plain_box(ax, cx, top, PROC_W, PROC_H, s["name"], fill="#f0f9ff", fontsize=12)
        rows = [("C/T", f'{_fmt(s["cycleTime"])}s'),
                ("C/O", _fmt_min(s["changeover"])),
                ("人数", f'{_fmt(s["operators"])}人'),
                ("可用率", f'{_fmt(s["uptime"])}%'),
                ("良品率", f'{_fmt(s["firstYield"])}%')]
        ty = top + PROC_H + 16
        for ri, (k, v) in enumerate(rows):
            ry = ty + ri * DATA_ROW_H
            ax.add_patch(Rectangle((cx - PROC_W / 2, ry), PROC_W, DATA_ROW_H,
                                   facecolor="white", edgecolor=EDGE, lw=0.9, zorder=3))
            ax.text(cx - PROC_W / 2 + 8, ry + DATA_ROW_H / 2, k, ha="left", va="center",
                    fontsize=8.5, zorder=4)
            ax.text(cx + PROC_W / 2 - 8, ry + DATA_ROW_H / 2, v, ha="right", va="center",
                    fontsize=8.5, fontweight="bold", zorder=4)
        # 工序框与数据格之间的竖线连接
        ax.plot([cx, cx], [top + PROC_H, ty], color=EDGE, lw=0.9, zorder=2)

    # 库存三角
    for iv in p["inventories"]:
        if iv["afterIndex"] < 0:
            tri_cx = (supplier_cx + ENDBOX_W / 2 + col_cx(0) - PROC_W / 2) / 2
            mid_y = base_tri_y
        elif iv["afterIndex"] >= n_proc - 1:
            tri_cx = (last_cx + PROC_W / 2 + customer_cx - ENDBOX_W / 2) / 2
            mid_y = base_tri_y
        else:
            here = procs[iv["afterIndex"]]
            d = depth_memo[here["id"]]
            tri_cx = (col_cx(d) + col_cx(d + 1)) / 2
            mid_y = proc_top(here["id"]) + PROC_H / 2
        _inventory_tri(ax, tri_cx, mid_y, iv["qty"], iv["days"], iv["invType"])

    # 工序间推动箭头（同车道用粗斜纹箭头；跨车道走贴源框的垂直通道）
    cross_lane = 0
    for u in procs:
        for v in succ[u["id"]]:
            ux = proc_cx(u["id"]) + PROC_W / 2
            uy = proc_top(u["id"]) + PROC_H / 2
            vx = proc_cx(v) - PROC_W / 2
            vy = proc_top(v) + PROC_H / 2
            if uy == vy:
                _push_arrow(ax, ux + 4, vx - 4, uy)
            else:
                ch_x = ux + 24 + (cross_lane % 3) * 10
                cross_lane += 1
                _polyline_arrow(ax, [(ux, uy), (ch_x, uy), (ch_x, vy), (vx - 4, vy)], lw=2.2)

    # 供应商 → 首工序、末工序 → 客户 物流
    sup_bottom = INFO_TOP + ENDBOX_H
    for r in roots:
        rx, ry = proc_cx(r) - PROC_W / 2, proc_top(r) + PROC_H / 2
        pts = [(supplier_cx, sup_bottom), (supplier_cx, ry)] if ry == base_tri_y else \
              [(supplier_cx, sup_bottom), (supplier_cx, base_tri_y),
               ((supplier_cx + rx) / 2, base_tri_y), ((supplier_cx + rx) / 2, ry)]
        pts.append((rx - 4, ry))
        _polyline_arrow(ax, pts, lw=2.2)
    for lf in leaves:
        lx, ly = proc_cx(lf) + PROC_W / 2, proc_top(lf) + PROC_H / 2
        if ly == base_tri_y:
            pts = [(lx, ly), (customer_cx, base_tri_y), (customer_cx, sup_bottom + 4)]
        else:
            mid = (lx + customer_cx) / 2
            pts = [(lx, ly), (mid, ly), (mid, base_tri_y), (customer_cx, base_tri_y),
                   (customer_cx, sup_bottom + 4)]
        _polyline_arrow(ax, pts, lw=2.2)

    # 改善爆炸点
    for k in p["kaizens"]:
        if k["afterIndex"] < 0:
            kx, ky = (supplier_cx + col_cx(0)) / 2, MATERIAL_Y - KAIZEN_LIFT
        elif k["afterIndex"] >= n_proc:
            kx, ky = customer_cx, MATERIAL_Y - KAIZEN_LIFT
        else:
            here = procs[min(k["afterIndex"], n_proc - 1)]
            kx, ky = proc_cx(here["id"]), proc_top(here["id"]) - KAIZEN_LIFT
        _kaizen_burst(ax, kx, ky, k["label"])

    # ===== 时间线区（下）=====
    gap = PROC_PITCH - PROC_W
    y_hi, y_lo = timeline_y, timeline_y + 36
    segs = []  # (宽, 是否上凸, 标签)
    lead = next((iv for iv in p["inventories"] if iv["afterIndex"] == -1), None)
    if lead:
        segs.append((gap, True, f'{_fmt(lead["days"])}天'))
    for s in crit:
        segs.append((PROC_W, False, f'{_fmt(s["cycleTime"])}s'))
        iv = next((iv for iv in p["inventories"] if iv["afterIndex"] == idx_of[s["id"]]), None)
        if iv:
            segs.append((gap, True, f'{_fmt(iv["days"])}天'))
    start_x = col_cx(0) - PROC_W / 2 - (gap if lead else 0)
    x = start_x
    prev_y = None
    for w, high, lab in segs:
        yy = y_hi if high else y_lo
        if prev_y is not None and prev_y != yy:
            ax.plot([x, x], [prev_y, yy], color=EDGE, lw=1.5)
        ax.plot([x, x + w], [yy, yy], color=EDGE, lw=1.5)
        if high:
            ax.text(x + w / 2, yy - 8, lab, ha="center", va="bottom", fontsize=10)
        else:
            ax.text(x + w / 2, yy + 10, lab, ha="center", va="top", fontsize=10)
        x += w
        prev_y = yy
    end_x = x + 18
    ax.text(end_x, y_hi + 2, f"{_fmt(lead_days)}天", ha="left", va="center",
            fontsize=11, fontweight="bold")
    ax.text(end_x, y_lo + 16, f"{_fmt(va_sec)}秒", ha="left", va="center",
            fontsize=11, fontweight="bold")
    ax.text(start_x, y_hi - 34, "生产周期 / 增值时间", ha="left", va="bottom",
            fontsize=9, color="#64748b")

    # 节拍框（左下）与汇总框（右下）
    box_y = timeline_y + 70
    if takt is not None:
        _plain_box(ax, supplier_cx - ENDBOX_W / 2 + 95, box_y, 190, 56,
                   f"节拍时间 Takt\n{takt:.1f} 秒/件", fill="#ecfdf5", fontsize=11)
    pce_txt = f"{pce:.2f}%" if pce >= 0.01 else f"{pce:.4f}%"
    sum_label = (f"增值时间：{_fmt(va_sec)} 秒\n生产周期：{total_days:.2f} 天\n"
                 f"生产周期效率 PCE：{pce_txt}")
    _plain_box(ax, customer_cx - ENDBOX_W / 2 + 115, box_y, 250, 76, sum_label,
               fill="#fefce8", fontsize=10.5)

    return {
        "image_base64": figure_to_base64(fig),
        "summary": {
            "工序数": n_proc,
            "总增值时间(秒)": _fmt(va_sec),
            "库存总天数(天)": _fmt(lead_days),
            "生产周期(天)": round(total_days, 2),
            "PCE(%)": round(pce, 4),
            "节拍时间(秒/件)": round(takt, 1) if takt is not None else "—",
        },
    }
