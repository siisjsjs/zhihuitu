"""装配 SOP 的 Excel 导出（动态行版式）。

布局自上而下、按内容动态增长：
- 1-2 行：标题 + 文档头（文件编号/编制日期/页数/版本号）
- 3-4 行：产品/工序/标准工时/标准产能 + 工序排号/作业类型/人员配置
- BOM：表头 + 每条物料一行（左侧为产品照片区）
- 操作说明：检查工序 / 本工序作业 / 注意事项 / 自检 / 技术要求，
  每段一个标签 + 每行内容自成一行（像“设备及工具”那样逐行增加，不再有固定行数上限）
- 设备及工具：表头 + 每件设备一行
- 审批栏：核准 / 审核 / 部门 / 负责人

仅依赖 openpyxl（requirements 已含）。
"""
from __future__ import annotations

import io
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.paths import LB_UPLOAD_DIR

# —— 通用样式 ——
_THIN = Side(style="thin", color="000000")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_LABEL_FILL = PatternFill("solid", fgColor="F2F2F2")
_FONT = Font(name="宋体", size=10)
_FONT_BOLD = Font(name="宋体", size=10, bold=True)
_TITLE_FONT = Font(name="宋体", size=16, bold=True)

_NCOLS = 16  # A..P

_COL_WIDTHS = {
    "A": 10.0, "B": 8.0, "C": 10.0, "D": 10.0, "E": 10.0,
    "F": 8.5, "G": 8.0, "H": 8.0, "I": 8.0, "J": 8.0, "K": 8.0,
    "L": 8.0, "M": 8.0, "N": 8.0, "O": 8.0, "P": 8.0,
}


def _resolve_image_path(url: str | None) -> Path | None:
    """把 /static/lb/uX/xxx.png 形式的 URL 还原成本地文件路径。"""
    if not url:
        return None
    marker = "/static/lb/"
    idx = url.find(marker)
    if idx == -1:
        return None
    rel = url[idx + len(marker):]
    p = LB_UPLOAD_DIR / rel
    return p if p.exists() else None


def _split_lines(text: str | None) -> list[str]:
    if not text:
        return []
    raw = str(text).replace("\r\n", "\n").replace("\r", "\n")
    return [ln.strip() for ln in raw.split("\n") if ln.strip()]


def _station_process_name(station: dict) -> str:
    """工位的工序名称：优先合并明细的首条，回退工位编码。"""
    detail = station.get("processDetail")
    if isinstance(detail, list) and detail:
        first = detail[0]
        if isinstance(first, dict):
            return first.get("name") or first.get("processName") or station.get("stationCode") or ""
        return str(first)
    return station.get("stationCode") or ""


def _join_detail(station: dict) -> str:
    """无 mainSteps 时，用合并工序明细名拼出编号列表作为本工序作业占位。"""
    detail = station.get("processDetail")
    if not isinstance(detail, list):
        return ""
    names = []
    for d in detail:
        if isinstance(d, dict):
            names.append(d.get("name") or d.get("processName") or "")
        else:
            names.append(str(d))
    return "\n".join(f"{i}.{n}" for i, n in enumerate(filter(None, names), start=1))


def _embed_image(ws, pieces: list[dict], anchor: str) -> None:
    """在照片区嵌入第一张可用的物料参考图（若存在本地文件）。"""
    for p in pieces:
        path = _resolve_image_path(p.get("refImage"))
        if path:
            try:
                from openpyxl.drawing.image import Image as XLImage

                img = XLImage(str(path))
                img.width = min(img.width, 220)
                img.height = min(img.height, 320)
                ws.add_image(img, anchor)
            except Exception:  # noqa: BLE001 图片不是必需，失败静默
                pass
            return


def _col(idx: int) -> str:
    """1->A 的列字母。"""
    return get_column_letter(idx)


def _put(ws, ref: str, value, *, bold=False, fill=False, align=None) -> None:
    cell = ws[ref]
    cell.value = value
    cell.font = _FONT_BOLD if bold else _FONT
    cell.alignment = align or _CENTER
    cell.border = _BORDER
    if fill:
        cell.fill = _LABEL_FILL


def _block(ws, r1: int, c1: int, r2: int, c2: int, value, *, bold=False, fill=False, align=None) -> None:
    """合并 (r1,c1)-(r2,c2) 矩形并写值；同时给区域内所有单元格补边框。"""
    a, b = f"{_col(c1)}{r1}", f"{_col(c2)}{r2}"
    if (r1, c1) != (r2, c2):
        ws.merge_cells(f"{a}:{b}")
    _put(ws, a, value, bold=bold, fill=fill, align=align)
    for rr in range(r1, r2 + 1):
        for cc in range(c1, c2 + 1):
            cell = ws.cell(row=rr, column=cc)
            cell.border = _BORDER
            if cell.font is None or not cell.font.name:
                cell.font = _FONT


def _section_rows(ws, start_row: int, label: str, lines: list[str]) -> int:
    """写一个“逐行增加”的小节：F列标签竖跨整段，G..M 每行一条内容。

    像“设备及工具”那样，有几行内容就占几行；至少占 1 行。
    返回写完后的下一行号。
    """
    n = max(1, len(lines))
    # 标签：F 列竖向合并整段
    _block(ws, start_row, 6, start_row + n - 1, 6, label, bold=True, fill=True)
    for i in range(n):
        r = start_row + i
        text = lines[i] if i < len(lines) else ""
        _block(ws, r, 7, r, 13, text, align=_LEFT)   # G..M 内容
    return start_row + n


def _tech_rows(ws, start_row: int, end_row: int, lines: list[str]) -> None:
    """技术要求列（N..P）：与左侧操作说明并排，逐行写，超出并入最后一行。"""
    span = end_row - start_row + 1
    for i in range(span):
        r = start_row + i
        if i < span - 1:
            text = lines[i] if i < len(lines) else ""
        else:
            text = "\n".join(lines[i:]) if i < len(lines) else ""
        _block(ws, r, 14, r, 16, text, align=_LEFT)  # N..P


def _write_sheet(ws, ctx: dict) -> None:
    """动态行版式：自上而下逐块写，内容多则行数增长。"""
    style = ctx.get("style", {})
    plan = ctx.get("plan", {})
    station = ctx.get("station", {})
    pieces = ctx.get("cut_pieces", []) or []

    ws.sheet_view.showGridLines = False
    for c, w in _COL_WIDTHS.items():
        ws.column_dimensions[c].width = w

    # —— 标题 + 文档头 ——
    _block(ws, 1, 1, 2, 7, "标准作业指导书 (SOP)", bold=True)
    ws["A1"].font = _TITLE_FONT
    ws.row_dimensions[1].height = 24
    _block(ws, 1, 8, 1, 9, "文件编号", bold=True, fill=True)
    _block(ws, 1, 10, 1, 11, "编制日期", bold=True, fill=True)
    _block(ws, 1, 12, 1, 13, "页数", bold=True, fill=True)
    _block(ws, 1, 14, 1, 16, "版本号", bold=True, fill=True)
    _block(ws, 2, 8, 2, 9, station.get("fileNo") or "")
    _block(ws, 2, 10, 2, 11, station.get("createdDate") or style.get("createdDate") or "")
    _block(ws, 2, 12, 2, 13, "1")
    _block(ws, 2, 14, 2, 16, station.get("version") or "A")

    # —— 产品/工序信息 ——
    takt = station.get("stationTakt") or plan.get("takt")
    capacity = ""
    if takt:
        try:
            capacity = round(3600.0 / float(takt))
        except (TypeError, ValueError, ZeroDivisionError):
            capacity = ""
    _block(ws, 3, 1, 4, 2, "产品名称", bold=True, fill=True)
    _block(ws, 3, 3, 4, 5, style.get("name") or "")
    _block(ws, 3, 6, 3, 7, "工序名称", bold=True, fill=True)
    _block(ws, 3, 8, 3, 9, _station_process_name(station))
    _block(ws, 3, 10, 3, 11, "标准工时", bold=True, fill=True)
    _block(ws, 3, 12, 3, 13, f"{takt}s" if takt else "")
    _block(ws, 3, 14, 3, 14, "标准产能/H", bold=True, fill=True)
    _block(ws, 3, 15, 3, 16, capacity)
    _block(ws, 4, 6, 4, 7, "工序排号", bold=True, fill=True)
    _block(ws, 4, 8, 4, 9, station.get("processSeq") or station.get("stationCode") or "")
    _block(ws, 4, 10, 4, 11, "作业类型", bold=True, fill=True)
    _block(ws, 4, 12, 4, 13, station.get("workType") or "")
    _block(ws, 4, 14, 4, 14, "人员配置", bold=True, fill=True)
    _block(ws, 4, 15, 4, 16, station.get("workerCount") or 1)

    # —— BOM：表头 + 每条物料一行；左侧 A 列为照片区 ——
    bom_header = 5
    _block(ws, bom_header, 6, bom_header, 6, "序号", bold=True, fill=True)
    _block(ws, bom_header, 7, bom_header, 9, "材料编号", bold=True, fill=True)
    _block(ws, bom_header, 10, bom_header, 11, "材料名称", bold=True, fill=True)
    _block(ws, bom_header, 12, bom_header, 14, "材料规格", bold=True, fill=True)
    _block(ws, bom_header, 15, bom_header, 16, "数量", bold=True, fill=True)
    n_bom = max(1, len(pieces))
    for i in range(n_bom):
        r = bom_header + 1 + i
        p = pieces[i] if i < len(pieces) else None
        _block(ws, r, 6, r, 6, i + 1)
        _block(ws, r, 7, r, 9, (p.get("pieceCode") if p else "") or "")
        _block(ws, r, 10, r, 11, (p.get("pieceName") if p else "") or "")
        _block(ws, r, 12, r, 14, (p.get("material") or p.get("spec") if p else "") or "", align=_LEFT)
        _block(ws, r, 15, r, 16, (p.get("quantity") if p else "") or "")
    bom_end = bom_header + n_bom  # 最后一行物料的行号

    # 照片区：A..E 跨 BOM 全段
    _block(ws, bom_header, 1, bom_end, 5, "")
    _embed_image(ws, pieces, f"A{bom_header}")

    # —— 操作说明（逐行增加，像设备及工具）——
    op_start = bom_end + 1
    _block(ws, op_start, 6, op_start, 13, "操作说明", bold=True, fill=True)
    _block(ws, op_start, 14, op_start, 16, "技术要求", bold=True, fill=True)

    r = op_start + 1
    r = _section_rows(ws, r, "检查工序", _split_lines(station.get("checkSteps")))
    main_lines = _split_lines(station.get("mainSteps")) or _split_lines(_join_detail(station))
    r = _section_rows(ws, r, "本工序作业", main_lines)
    r = _section_rows(ws, r, "注意事项", _split_lines(station.get("notes")))
    r = _section_rows(ws, r, "自检", _split_lines(station.get("selfCheck")))
    op_end = r - 1
    # 技术要求与整个操作说明并排（N..P），逐行写
    _tech_rows(ws, op_start + 1, op_end, _split_lines(station.get("techReq")))

    # —— 设备及工具：表头 + 每件一行 ——
    eq_label = op_end + 1
    _block(ws, eq_label, 1, eq_label, 5, "设备及工具", bold=True, fill=True)
    eq_header = eq_label + 1
    _block(ws, eq_header, 1, eq_header, 2, "设备、工装名称", bold=True, fill=True)
    _block(ws, eq_header, 3, eq_header, 3, "型号", bold=True, fill=True)
    _block(ws, eq_header, 4, eq_header, 5, "设定条件", bold=True, fill=True)
    equip = station.get("equipment") or []
    n_eq = max(1, len(equip))
    for i in range(n_eq):
        rr = eq_header + 1 + i
        e = equip[i] if i < len(equip) else None
        _block(ws, rr, 1, rr, 2, (e.get("name") if e else "") or "", align=_LEFT)
        _block(ws, rr, 3, rr, 3, (e.get("model") if e else "") or "")
        _block(ws, rr, 4, rr, 5, (e.get("condition") if e else "") or "", align=_LEFT)
    eq_end = eq_header + n_eq

    # 设备区右侧（F..P）大图/备注留白，跨设备段
    _block(ws, eq_label, 6, eq_end, 16, "")

    # —— 审批栏 ——
    appr = eq_end + 1
    _block(ws, appr, 1, appr, 2, "核准", bold=True, fill=True)
    _block(ws, appr, 3, appr, 5, station.get("approver") or "")
    _block(ws, appr, 6, appr, 7, "审核", bold=True, fill=True)
    _block(ws, appr, 8, appr, 10, station.get("reviewer") or "")
    _block(ws, appr, 11, appr, 13, f"部门：{station.get('department') or ''}", align=_LEFT)
    _block(ws, appr, 14, appr, 16, f"负责人：{station.get('ownerName') or ''}", align=_LEFT)


def build_station_xlsx(ctx: dict) -> bytes:
    """按动态版式生成单工位装配 SOP 的 xlsx 字节。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "SOP"
    _write_sheet(ws, ctx)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_batch_xlsx(contexts: list[tuple[str, dict]]) -> bytes:
    """批量：每个工位一个 sheet，合成一个工作簿。contexts=[(station_code, ctx)]。"""
    wb = Workbook()
    wb.remove(wb.active)
    used: set[str] = set()
    for code, ctx in contexts:
        title = (code or "ST")[:28]
        base = title
        n = 1
        while title in used:
            n += 1
            title = f"{base}_{n}"[:31]
        used.add(title)
        ws = wb.create_sheet(title=title)
        _write_sheet(ws, ctx)
    if not wb.sheetnames:
        wb.create_sheet(title="SOP")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

