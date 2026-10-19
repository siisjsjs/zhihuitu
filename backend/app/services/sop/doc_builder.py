"""SOP 文档渲染（计划书 §F6 / M6-M7）。

一工位一页、中英双语。HTML 用 Jinja2 渲染（体积小、永远可用），
PDF 用纯 Python 的 xhtml2pdf（Windows 免 GTK，规避 WeasyPrint 的 libgobject 依赖）。
若环境装好了 WeasyPrint 的原生库，可切 PDF_ENGINE=weasyprint 获得更好的 CSS 排版。
"""
from __future__ import annotations
import io
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.paths import BACKEND_ROOT

TEMPLATE_DIR = BACKEND_ROOT / "templates" / "sop"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_station_html(context: dict) -> str:
    """渲染单工位 SOP 的 HTML 片段（含整页样式，可独立打开）。"""
    tpl = _env.get_template("station.html")
    return tpl.render(**context)


def render_batch_html(stations_ctx: list[dict], meta: dict) -> str:
    """把多个工位拼成一个多页 HTML（每工位 page-break）。"""
    tpl = _env.get_template("batch.html")
    return tpl.render(stations=stations_ctx, meta=meta)


def html_to_pdf_bytes(html: str) -> bytes:
    """HTML → PDF。优先 xhtml2pdf（纯 Python，Windows 友好）。

    返回 PDF 字节；失败时抛异常由调用方处理（降级为只给 HTML）。
    """
    from xhtml2pdf import pisa

    buf = io.BytesIO()
    # encoding 指定 utf-8 以正确渲染中文
    result = pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf 渲染失败：{result.err} 个错误")
    return buf.getvalue()


def merge_pdfs(pdf_bytes_list: list[bytes]) -> bytes:
    """合并多个 PDF 字节为一个（批量 SOP）。"""
    from pypdf import PdfWriter, PdfReader

    writer = PdfWriter()
    for b in pdf_bytes_list:
        reader = PdfReader(io.BytesIO(b))
        for page in reader.pages:
            writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def build_station_context(
    station: dict, style: dict, plan: dict, cut_pieces: list[dict] | None = None
) -> dict:
    """把工位/款式/方案/裁片整理成模板上下文（双语标签在模板里写死）。"""
    return {
        "style": style,
        "plan": plan,
        "station": station,
        "cut_pieces": cut_pieces or [],
    }
