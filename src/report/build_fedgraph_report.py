"""
Sinh báo cáo chính thức FedGraph (BaoCao_FedGraph.docx) theo đúng định dạng chuẩn
của BaoCaoPBL7_DinhDangChuan.pdf (ĐH Bách khoa - ĐH Đà Nẵng, Khoa CNTT).

PHIÊN BẢN NÂNG CẤP V2 (~45-60 trang):
1. Khắc phục triệt để lỗi hiển thị và thụt lề TOC / LOF / LOT:
   - Định nghĩa trực tiếp style tích hợp sẵn `TOC1`, `TOC2`, `TOC3`, `TableofFigures`
     trong `styles.xml` (KHÔNG dùng add_style("toc 1") vốn sinh `TOC11`) với
     `firstLine="0"`, `jc="left"`, tab chấm phải `8787 dxa` (`15.5 cm`).
   - Bọc các trường `MỤC LỤC`, `DANH MỤC HÌNH ẢNH`, `DANH MỤC BẢNG BIỂU` trong
     `<w:sdt><w:sdtPr><w:docPartObj>...</w:docPartObj></w:sdtPr><w:sdtContent>...</w:sdtContent></w:sdt>`.
   - Hỗ trợ `--word-update` gọi `WINWORD.EXE` COM (`DisplayAlerts=0`,
     `TablesOfContents.Update()`, `TablesOfFigures.Update()`, `Fields.Update()`, `Save()`),
     sau đó chạy bước hậu xử lý XML trên `.docx`:
     + Xóa toàn bộ `<w:webHidden/>` khỏi các run trong TOC/LOF/LOT.
     + Ép `Times New Roman` + `#000000` cho toàn bộ run trong `<w:sdtContent>`.
     + Khôi phục `<w:updateFields w:val="true"/>` trong `word/settings.xml`.
     + Vá `word/theme/theme1.xml` sang `Times New Roman`.
2. Bổ sung Chương 5 chuyên sâu về Demo & Hệ thống Web Full-Stack với 5 ảnh chụp màn
   hình thực tế (`results_v3/demo_screenshots/demo_01..05.png` -> Hình 7..11).
3. Đào sâu lý thuyết toán học, Related Work, pipeline V3, giả mã thuật toán, và
   phân tích lỗi/nút thắt cổ chai ở Chương 1..6.
4. Toàn bộ số liệu đọc trực tiếp từ artifacts/v3, results_v3, results/v3, results/reco_main.json.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor
from lxml import etree as ET


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DOCX = ROOT / "maubaocao" / "BaoCaoPBL7.docx"
FIG_DIR = ROOT / "results_v3" / "report_figures"
DEMO_DIR = ROOT / "results_v3" / "demo_screenshots"
OUT_DOCX = ROOT / "BaoCao_FedGraph.docx"

META_PATH = ROOT / "artifacts" / "v3" / "meta.json"
CUDA_METRICS_PATH = ROOT / "results_v3" / "notebook_metrics.json"
CPU_METRICS_PATH = ROOT / "results" / "v3" / "notebook_metrics.json"
ABLATION_CSV_PATH = ROOT / "results_v3" / "ablation_results.csv"
SWEEP_CSV_PATH = ROOT / "results_v3" / "sweep_results.csv"
LOCAL_ONLY_PATH = ROOT / "results_v3" / "local_only_v3.json"
MEDAJOB_PATH = ROOT / "results" / "reco_main.json"

BLACK = RGBColor(0x00, 0x00, 0x00)
USABLE_WIDTH_CM = 15.5
RIGHT_TAB_DXA = 8787  # 15.5 cm * 566.929 dxa/cm
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


# =====================================================================
# 1. Nạp dữ liệu kiểm chứng từ repository
# =====================================================================
def load_ground_truth() -> dict[str, Any]:
    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    with open(CUDA_METRICS_PATH, encoding="utf-8") as f:
        cuda = json.load(f)
    with open(CPU_METRICS_PATH, encoding="utf-8") as f:
        cpu = json.load(f)
    with open(LOCAL_ONLY_PATH, encoding="utf-8") as f:
        local_only = json.load(f)
    with open(MEDAJOB_PATH, encoding="utf-8") as f:
        medajob = json.load(f)
    with open(ABLATION_CSV_PATH, encoding="utf-8-sig", newline="") as f:
        ablation = list(csv.DictReader(f))
    with open(SWEEP_CSV_PATH, encoding="utf-8-sig", newline="") as f:
        sweep = list(csv.DictReader(f))

    return {
        "meta": meta,
        "cuda": cuda,
        "cpu": cpu,
        "local_only": local_only,
        "medajob": medajob,
        "ablation": ablation,
        "sweep": sweep,
    }


def extract_cover_logos(template_path: Path) -> tuple[bytes, bytes]:
    with zipfile.ZipFile(template_path, "r") as zf:
        img1 = zf.read("word/media/image1.png")
        img2 = zf.read("word/media/image2.png")
    return img1, img2


def fi(n: int | float) -> str:
    return f"{int(n):,}".replace(",", ".")


def f4(v: float | str) -> str:
    return f"{float(v):.4f}"


def f2(v: float | str) -> str:
    return f"{float(v):.2f}"


# =====================================================================
# 2. Tiện ích XML chuẩn hóa Times New Roman, #000000 & Built-in TOC Styles
# =====================================================================
def _set_rfonts(rPr: OxmlElement, font_name: str = "Times New Roman") -> None:
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), font_name)
    for theme_attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if qn(theme_attr) in rFonts.attrib:
            del rFonts.attrib[qn(theme_attr)]


def _set_run_font(
    run,
    name: str = "Times New Roman",
    size_pt: float | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
    underline: bool | None = None,
) -> None:
    run.font.name = name
    run.font.color.rgb = BLACK
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if underline is not None:
        run.underline = underline
    rPr = run._r.get_or_add_rPr()
    _set_rfonts(rPr, name)
    color = rPr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rPr.append(color)
    color.set(qn("w:val"), "000000")
    if qn("w:themeColor") in color.attrib:
        del color.attrib[qn("w:themeColor")]


def _configure_style(
    style,
    size_pt: float,
    bold: bool = False,
    italic: bool = False,
    all_caps: bool = False,
    font_name: str = "Times New Roman",
) -> None:
    style.font.name = font_name
    style.font.size = Pt(size_pt)
    style.font.bold = bold
    style.font.italic = italic
    style.font.all_caps = all_caps
    style.font.color.rgb = BLACK
    rPr = style.element.get_or_add_rPr()
    _set_rfonts(rPr, font_name)
    color = rPr.find(qn("w:color"))
    if color is None:
        color = OxmlElement("w:color")
        rPr.append(color)
    color.set(qn("w:val"), "000000")
    if qn("w:themeColor") in color.attrib:
        del color.attrib[qn("w:themeColor")]


def _set_doc_defaults(doc: Document) -> None:
    styles_el = doc.styles.element
    docDefaults = styles_el.find(qn("w:docDefaults"))
    if docDefaults is None:
        docDefaults = OxmlElement("w:docDefaults")
        styles_el.insert(0, docDefaults)
    rPrDefault = docDefaults.find(qn("w:rPrDefault"))
    if rPrDefault is None:
        rPrDefault = OxmlElement("w:rPrDefault")
        docDefaults.insert(0, rPrDefault)
    rPr = rPrDefault.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        rPrDefault.append(rPr)
    _set_rfonts(rPr, "Times New Roman")
    sz = rPr.find(qn("w:sz"))
    if sz is None:
        sz = OxmlElement("w:sz")
        rPr.append(sz)
    sz.set(qn("w:val"), "26")
    szCs = rPr.find(qn("w:szCs"))
    if szCs is None:
        szCs = OxmlElement("w:szCs")
        rPr.append(szCs)
    szCs.set(qn("w:val"), "26")
    col = rPr.find(qn("w:color"))
    if col is None:
        col = OxmlElement("w:color")
        rPr.append(col)
    col.set(qn("w:val"), "000000")


def _get_or_add_style(doc: Document, name: str, stype=WD_STYLE_TYPE.PARAGRAPH):
    try:
        return doc.styles[name]
    except KeyError:
        return doc.styles.add_style(name, stype)


def _upsert_builtin_toc_style(
    styles_el,
    style_id: str,
    style_name: str,
    left_dxa: int,
    bold: bool = False,
) -> None:
    """Định nghĩa trực tiếp styleId tích hợp của Word (TOC1, TOC2, TOC3, TableofFigures)
    trong styles.xml để Word dùng đúng style này khi Update(), tránh sinh TOC11 hoặc
    kế thừa firstLine=567 (1.0 cm) từ Normal."""
    for existing in list(styles_el.findall(qn("w:style"))):
        if existing.get(qn("w:styleId")) == style_id:
            styles_el.remove(existing)

    b_xml = "<w:b/><w:bCs/>" if bold else ""
    xml = f"""
    <w:style {nsdecls("w")} w:type="paragraph" w:styleId="{style_id}">
      <w:name w:val="{style_name}"/>
      <w:basedOn w:val="Normal"/>
      <w:next w:val="Normal"/>
      <w:uiPriority w:val="39"/>
      <w:unhideWhenUsed/>
      <w:pPr>
        <w:tabs>
          <w:tab w:val="right" w:leader="dot" w:pos="{RIGHT_TAB_DXA}"/>
        </w:tabs>
        <w:spacing w:before="0" w:after="60" w:line="360" w:lineRule="auto"/>
        <w:ind w:left="{left_dxa}" w:firstLine="0"/>
        <w:jc w:val="left"/>
      </w:pPr>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
        {b_xml}
        <w:color w:val="000000"/>
        <w:sz w:val="26"/>
        <w:szCs w:val="26"/>
      </w:rPr>
    </w:style>
    """
    styles_el.append(parse_xml(xml))


def setup_styles(doc: Document) -> None:
    _set_doc_defaults(doc)

    normal = doc.styles["Normal"]
    _configure_style(normal, 13.0, bold=False, italic=False)
    npf = normal.paragraph_format
    npf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    npf.first_line_indent = Cm(1.0)
    npf.line_spacing = 1.5
    npf.space_before = Pt(0)
    npf.space_after = Pt(6)

    h1 = doc.styles["Heading 1"]
    _configure_style(h1, 16.0, bold=True, all_caps=True)
    h1pf = h1.paragraph_format
    h1pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h1pf.first_line_indent = Cm(0)
    h1pf.left_indent = Cm(0)
    h1pf.line_spacing = 1.5
    h1pf.space_before = Pt(12)
    h1pf.space_after = Pt(6)
    h1pf.keep_with_next = True
    h1pf.keep_together = True
    h1pf.page_break_before = True

    h2 = doc.styles["Heading 2"]
    _configure_style(h2, 14.0, bold=True)
    h2pf = h2.paragraph_format
    h2pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h2pf.first_line_indent = Cm(0)
    h2pf.left_indent = Cm(0)
    h2pf.line_spacing = 1.5
    h2pf.space_before = Pt(12)
    h2pf.space_after = Pt(6)
    h2pf.keep_with_next = True

    h3 = doc.styles["Heading 3"]
    _configure_style(h3, 13.0, bold=True)
    h3pf = h3.paragraph_format
    h3pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h3pf.first_line_indent = Cm(0)
    h3pf.left_indent = Cm(0)
    h3pf.line_spacing = 1.5
    h3pf.space_before = Pt(8)
    h3pf.space_after = Pt(4)
    h3pf.keep_with_next = True

    cap = _get_or_add_style(doc, "Caption", WD_STYLE_TYPE.PARAGRAPH)
    _configure_style(cap, 13.0, bold=True, italic=True)
    cpf = cap.paragraph_format
    cpf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cpf.first_line_indent = Cm(0)
    cpf.left_indent = Cm(0)
    cpf.line_spacing = 1.3
    cpf.space_before = Pt(4)
    cpf.space_after = Pt(6)

    front = _get_or_add_style(doc, "FrontTitle", WD_STYLE_TYPE.PARAGRAPH)
    _configure_style(front, 16.0, bold=True, all_caps=True)
    fpf = front.paragraph_format
    fpf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fpf.first_line_indent = Cm(0)
    fpf.line_spacing = 1.5
    fpf.space_before = Pt(0)
    fpf.space_after = Pt(12)
    fpf.keep_with_next = True

    # Định nghĩa thẳng TOC1..3 & TableofFigures với styleId chuẩn của Word
    styles_el = doc.styles.element
    _upsert_builtin_toc_style(styles_el, "TOC1", "toc 1", left_dxa=0, bold=False)
    _upsert_builtin_toc_style(styles_el, "TOC2", "toc 2", left_dxa=283, bold=False)
    _upsert_builtin_toc_style(styles_el, "TOC3", "toc 3", left_dxa=567, bold=False)
    _upsert_builtin_toc_style(
        styles_el, "TableofFigures", "table of figures", left_dxa=0, bold=False
    )

    for hname in ("Hyperlink", "FollowedHyperlink"):
        hst = _get_or_add_style(doc, hname, WD_STYLE_TYPE.CHARACTER)
        _configure_style(hst, 13.0, bold=False, italic=False)
        hst.font.underline = False


def add_complex_field(
    paragraph,
    instr: str,
    placeholder: str = "",
    size_pt: float = 13.0,
    bold: bool = False,
    italic: bool = False,
    dirty: bool = False,
) -> None:
    r_begin = paragraph.add_run()
    _set_run_font(r_begin, size_pt=size_pt, bold=bold, italic=italic)
    fb = OxmlElement("w:fldChar")
    fb.set(qn("w:fldCharType"), "begin")
    if dirty:
        fb.set(qn("w:dirty"), "true")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    fs = OxmlElement("w:fldChar")
    fs.set(qn("w:fldCharType"), "separate")
    r_begin._r.extend([fb, it, fs])

    r_val = paragraph.add_run(placeholder)
    _set_run_font(r_val, size_pt=size_pt, bold=bold, italic=italic)

    r_end = paragraph.add_run()
    _set_run_font(r_end, size_pt=size_pt, bold=bold, italic=italic)
    fe = OxmlElement("w:fldChar")
    fe.set(qn("w:fldCharType"), "end")
    r_end._r.append(fe)


def add_sdt_toc_block(
    doc: Document,
    gallery_name: str,
    style_id: str,
    instr: str,
    placeholder: str,
) -> None:
    """Chèn khối <w:sdt> chuẩn Word chứa trường TOC/LOF/LOT."""
    sdt_xml = f"""
    <w:sdt {nsdecls("w")}>
      <w:sdtPr>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
          <w:color w:val="000000"/>
          <w:sz w:val="26"/>
          <w:szCs w:val="26"/>
        </w:rPr>
        <w:docPartObj>
          <w:docPartGallery w:val="{gallery_name}"/>
          <w:docPartUnique/>
        </w:docPartObj>
      </w:sdtPr>
      <w:sdtContent>
        <w:p>
          <w:pPr>
            <w:pStyle w:val="{style_id}"/>
            <w:ind w:left="0" w:firstLine="0"/>
            <w:jc w:val="left"/>
          </w:pPr>
          <w:r>
            <w:rPr>
              <w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
              <w:color w:val="000000"/>
              <w:sz w:val="26"/>
              <w:szCs w:val="26"/>
            </w:rPr>
            <w:fldChar w:fldCharType="begin" w:dirty="true"/>
          </w:r>
          <w:r>
            <w:rPr>
              <w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
              <w:color w:val="000000"/>
              <w:sz w:val="26"/>
              <w:szCs w:val="26"/>
            </w:rPr>
            <w:instrText xml:space="preserve"> {instr} </w:instrText>
          </w:r>
          <w:r>
            <w:rPr>
              <w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
              <w:color w:val="000000"/>
              <w:sz w:val="26"/>
              <w:szCs w:val="26"/>
            </w:rPr>
            <w:fldChar w:fldCharType="separate"/>
          </w:r>
          <w:r>
            <w:rPr>
              <w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
              <w:color w:val="000000"/>
              <w:sz w:val="26"/>
              <w:szCs w:val="26"/>
            </w:rPr>
            <w:t>{placeholder}</w:t>
          </w:r>
          <w:r>
            <w:rPr>
              <w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
              <w:color w:val="000000"/>
              <w:sz w:val="26"/>
              <w:szCs w:val="26"/>
            </w:rPr>
            <w:fldChar w:fldCharType="end"/>
          </w:r>
        </w:p>
      </w:sdtContent>
    </w:sdt>
    """
    p_anchor = doc.add_paragraph()
    p_anchor._element.addnext(parse_xml(sdt_xml))
    p_anchor._element.getparent().remove(p_anchor._element)


def _enable_update_fields(doc: Document) -> None:
    settings = doc.settings.element
    uf = settings.find(qn("w:updateFields"))
    if uf is None:
        uf = OxmlElement("w:updateFields")
        settings.append(uf)
    uf.set(qn("w:val"), "true")


def _configure_section_geometry(section) -> None:
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.5)
    section.right_margin = Cm(2.0)
    section.gutter = Cm(0.0)
    section.header_distance = Cm(1.27)
    section.footer_distance = Cm(1.27)


def _set_section_pg_num_start(section, start: int = 1) -> None:
    sectPr = section._sectPr
    pgNumType = sectPr.find(qn("w:pgNumType"))
    if pgNumType is None:
        pgNumType = OxmlElement("w:pgNumType")
        sectPr.append(pgNumType)
    pgNumType.set(qn("w:fmt"), "decimal")
    pgNumType.set(qn("w:start"), str(start))


def _set_table_borders(table, border_sz: int = 4, none: bool = False) -> None:
    tblPr = table._tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    if none:
        xml = (
            f'<w:tblBorders {nsdecls("w")}>'
            '<w:top w:val="none"/><w:left w:val="none"/>'
            '<w:bottom w:val="none"/><w:right w:val="none"/>'
            '<w:insideH w:val="none"/><w:insideV w:val="none"/>'
            "</w:tblBorders>"
        )
    else:
        xml = (
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="{border_sz}" w:space="0" w:color="000000"/>'
            f'<w:left w:val="single" w:sz="{border_sz}" w:space="0" w:color="000000"/>'
            f'<w:bottom w:val="single" w:sz="{border_sz}" w:space="0" w:color="000000"/>'
            f'<w:right w:val="single" w:sz="{border_sz}" w:space="0" w:color="000000"/>'
            f'<w:insideH w:val="single" w:sz="{border_sz}" w:space="0" w:color="000000"/>'
            f'<w:insideV w:val="single" w:sz="{border_sz}" w:space="0" w:color="000000"/>'
            "</w:tblBorders>"
        )
    tblPr.append(parse_xml(xml))


def _set_fixed_table_layout(table, widths_cm: list[float]) -> None:
    table.autofit = False
    tblPr = table._tbl.tblPr
    old_w = tblPr.find(qn("w:tblW"))
    if old_w is not None:
        tblPr.remove(old_w)
    total_dxa = int(round(sum(widths_cm) * 567.0))
    tblPr.append(parse_xml(f'<w:tblW {nsdecls("w")} w:w="{total_dxa}" w:type="dxa"/>'))

    old_l = tblPr.find(qn("w:tblLayout"))
    if old_l is not None:
        tblPr.remove(old_l)
    tblPr.append(parse_xml(f'<w:tblLayout {nsdecls("w")} w:type="fixed"/>'))

    tblGrid = table._tbl.tblGrid
    if tblGrid is not None:
        for gc in list(tblGrid):
            tblGrid.remove(gc)
        for w in widths_cm:
            gc = OxmlElement("w:gridCol")
            gc.set(qn("w:w"), str(int(round(w * 567.0))))
            tblGrid.append(gc)


def _set_cell_margins(cell, top: int = 70, bottom: int = 70, left: int = 100, right: int = 100) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    old = tcPr.find(qn("w:tcMar"))
    if old is not None:
        tcPr.remove(old)
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        "</w:tcMar>"
    )
    tcPr.append(tcMar)


def _set_row_header_and_cant_split(row, is_header: bool = False) -> None:
    trPr = row._tr.get_or_add_trPr()
    cs = OxmlElement("w:cantSplit")
    trPr.append(cs)
    if is_header:
        th = OxmlElement("w:tblHeader")
        trPr.append(th)


# =====================================================================
# 3. Hậu xử lý XML sau khi Word COM lưu file
# =====================================================================
def postprocess_docx_xml(docx_path: Path) -> dict[str, int]:
    """Chạy pass zipfile XML trên BaoCao_FedGraph.docx sau Word COM:
    1. Xóa <w:webHidden/> khỏi tất cả run trong TOC/LOF/LOT (<w:sdtContent>).
    2. Ép Times New Roman + #000000 + sz=26 trong <w:sdtContent> và gỡ firstLine trên
       các đoạn TOC1..3 / TableofFigures.
    3. Bảo đảm TOC1..3 & TableofFigures trong styles.xml vẫn giữ firstLine="0" & jc="left".
    4. Khôi phục <w:updateFields w:val="true"/> trong word/settings.xml.
    5. Vá theme1.xml sang Times New Roman.
    """
    removed_webhidden = 0
    ns = {"w": W_NS}
    tmp_path = docx_path.with_suffix(".tmp.docx")

    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(
        tmp_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                root = ET.fromstring(data)
                for wh in root.xpath(".//w:webHidden", namespaces=ns):
                    parent = wh.getparent()
                    if parent is not None:
                        parent.remove(wh)
                        removed_webhidden += 1
                # Bảo đảm mọi đoạn & run bên trong <w:sdtContent> giữ font/color/align chuẩn
                for sdt_c in root.xpath(".//w:sdtContent", namespaces=ns):
                    for p in sdt_c.xpath(".//w:p", namespaces=ns):
                        pPr = p.find(f"{{{W_NS}}}pPr")
                        if pPr is not None:
                            ind = pPr.find(f"{{{W_NS}}}ind")
                            if ind is not None:
                                ind.set(f"{{{W_NS}}}firstLine", "0")
                            jc = pPr.find(f"{{{W_NS}}}jc")
                            if jc is not None:
                                jc.set(f"{{{W_NS}}}val", "left")
                    for r in sdt_c.xpath(".//w:r", namespaces=ns):
                        rPr = r.find(f"{{{W_NS}}}rPr")
                        if rPr is None:
                            rPr = ET.Element(f"{{{W_NS}}}rPr")
                            r.insert(0, rPr)
                        _set_rfonts(rPr, "Times New Roman")
                        col = rPr.find(f"{{{W_NS}}}color")
                        if col is None:
                            col = ET.SubElement(rPr, f"{{{W_NS}}}color")
                        col.set(f"{{{W_NS}}}val", "000000")
                        if f"{{{W_NS}}}themeColor" in col.attrib:
                            del col.attrib[f"{{{W_NS}}}themeColor"]
                data = ET.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

            elif item.filename == "word/styles.xml":
                sroot = ET.fromstring(data)
                toc_map = {"TOC1": 0, "TOC2": 283, "TOC3": 567, "TableofFigures": 0}
                for st in sroot.xpath(".//w:style", namespaces=ns):
                    sid = st.get(f"{{{W_NS}}}styleId")
                    if sid in toc_map:
                        pPr = st.find(f"{{{W_NS}}}pPr")
                        if pPr is None:
                            pPr = ET.SubElement(st, f"{{{W_NS}}}pPr")
                        ind = pPr.find(f"{{{W_NS}}}ind")
                        if ind is None:
                            ind = ET.SubElement(pPr, f"{{{W_NS}}}ind")
                        ind.set(f"{{{W_NS}}}left", str(toc_map[sid]))
                        ind.set(f"{{{W_NS}}}firstLine", "0")
                        jc = pPr.find(f"{{{W_NS}}}jc")
                        if jc is None:
                            jc = ET.SubElement(pPr, f"{{{W_NS}}}jc")
                        jc.set(f"{{{W_NS}}}val", "left")
                        rPr = st.find(f"{{{W_NS}}}rPr")
                        if rPr is None:
                            rPr = ET.SubElement(st, f"{{{W_NS}}}rPr")
                        _set_rfonts(rPr, "Times New Roman")
                        col = rPr.find(f"{{{W_NS}}}color")
                        if col is None:
                            col = ET.SubElement(rPr, f"{{{W_NS}}}color")
                        col.set(f"{{{W_NS}}}val", "000000")
                data = ET.tostring(sroot, xml_declaration=True, encoding="UTF-8", standalone=True)

            elif item.filename == "word/settings.xml":
                stroot = ET.fromstring(data)
                uf = stroot.find(f"{{{W_NS}}}updateFields")
                if uf is None:
                    uf = ET.SubElement(stroot, f"{{{W_NS}}}updateFields")
                uf.set(f"{{{W_NS}}}val", "true")
                data = ET.tostring(stroot, xml_declaration=True, encoding="UTF-8", standalone=True)

            elif item.filename == "word/theme/theme1.xml":
                txt = data.decode("utf-8")
                txt = re.sub(
                    r'typeface="(Calibri Light|Calibri|Cambria)"',
                    'typeface="Times New Roman"',
                    txt,
                )
                data = txt.encode("utf-8")

            zout.writestr(item, data)

    tmp_path.replace(docx_path)
    return {"removed_webhidden": removed_webhidden}


def update_fields_via_word_com(docx_path: Path, qa_pdf_dir: Path | None = None) -> dict[str, Any]:
    """Cập nhật toàn bộ TOC/LOF/LOT/SEQ fields qua WINWORD.EXE COM (PowerShell),
    chạy hậu xử lý XML, và tùy chọn xuất PDF kiểm tra đọc-chỉ (không lưu đè .docx)."""
    docx_abs = str(docx_path.resolve())
    ps_update = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $null
try {{
    $doc = $word.Documents.Open('{docx_abs}', $false, $false)
    foreach ($toc in $doc.TablesOfContents) {{ $toc.Update() }}
    foreach ($tof in $doc.TablesOfFigures) {{ $tof.Update() }}
    [void]$doc.Fields.Update()
    $doc.Repaginate()
    foreach ($toc in $doc.TablesOfContents) {{ $toc.Update() }}
    foreach ($tof in $doc.TablesOfFigures) {{ $tof.Update() }}
    $nToc = $doc.TablesOfContents.Count
    $nTof = $doc.TablesOfFigures.Count
    $doc.Save()
    $doc.Close(0)
    $doc = $null
    Write-Output "WORD_COM_COUNTS:$nToc`:$nTof"
}} finally {{
    if ($doc -ne $null) {{ try {{ $doc.Close(0) }} catch {{}} }}
    if ($word -ne $null) {{ try {{ $word.Quit(0) }} catch {{}} }}
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}}
"""
    res = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_update],
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    n_toc, n_tof = 0, 0
    for line in res.stdout.splitlines():
        if line.startswith("WORD_COM_COUNTS:"):
            parts = line.split(":")
            if len(parts) == 3:
                n_toc, n_tof = int(parts[1]), int(parts[2])

    time.sleep(0.5)
    xml_stats = postprocess_docx_xml(docx_path)

    pdf_path = None
    if qa_pdf_dir is not None:
        qa_pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = qa_pdf_dir / "BaoCao_FedGraph.pdf"
        pdf_abs = str(pdf_path.resolve())
        ps_pdf = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $null
try {{
    $doc = $word.Documents.Open('{docx_abs}', $false, $true)
    $doc.ExportAsFixedFormat('{pdf_abs}', 17, $false, 0, 0, 1, 1, 0, $true, $true, 1)
    $doc.Close(0)
    $doc = $null
}} finally {{
    if ($doc -ne $null) {{ try {{ $doc.Close(0) }} catch {{}} }}
    if ($word -ne $null) {{ try {{ $word.Quit(0) }} catch {{}} }}
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}}
"""
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_pdf],
            capture_output=True,
            text=True,
            check=True,
            timeout=180,
        )

    return {
        "word_toc_count": n_toc,
        "word_tof_count": n_tof,
        **xml_stats,
        "qa_pdf": str(pdf_path) if pdf_path else None,
    }


# =====================================================================
# 4. Lớp xây dựng báo cáo
# =====================================================================
class FedGraphReportBuilder:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.doc = Document()
        setup_styles(self.doc)
        _configure_section_geometry(self.doc.sections[0])
        self.doc.sections[0].different_first_page_header_footer = False
        self.fig_count = 0
        self.tab_count = 0
        self.eq_count = 0
        self.alg_count = 0
        self.inline_citations: set[int] = set()

    # --- Trang bìa (Section 0) ---------------------------------------
    def build_cover_page(self) -> None:
        img1, img2 = extract_cover_logos(TEMPLATE_DOCX)

        hdr_tbl = self.doc.add_table(rows=1, cols=3)
        hdr_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(hdr_tbl, none=True)
        widths = [2.75, 10.0, 2.75]
        _set_fixed_table_layout(hdr_tbl, widths)
        row = hdr_tbl.rows[0]
        _set_row_header_and_cant_split(row)

        c0 = row.cells[0]
        c0.width = Cm(widths[0])
        c0.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _set_cell_margins(c0, 20, 20, 20, 20)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.first_line_indent = Cm(0)
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        p0.add_run().add_picture(io.BytesIO(img1), width=Cm(2.50), height=Cm(2.49))

        c1 = row.cells[1]
        c1.width = Cm(widths[1])
        c1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _set_cell_margins(c1, 20, 20, 40, 40)

        p_uni = c1.paragraphs[0]
        p_uni.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_uni.paragraph_format.first_line_indent = Cm(0)
        p_uni.paragraph_format.line_spacing = 1.2
        p_uni.paragraph_format.space_before = Pt(0)
        p_uni.paragraph_format.space_after = Pt(4)
        r_uni = p_uni.add_run("Đại học Bách khoa, Đại học Đà Nẵng (DUT)")
        _set_run_font(r_uni, size_pt=13.5, bold=True)

        p_fac = c1.add_paragraph()
        p_fac.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fac.paragraph_format.first_line_indent = Cm(0)
        p_fac.paragraph_format.line_spacing = 1.2
        p_fac.paragraph_format.space_before = Pt(0)
        p_fac.paragraph_format.space_after = Pt(0)
        r_fac = p_fac.add_run("KHOA CÔNG NGHỆ THÔNG TIN")
        _set_run_font(r_fac, size_pt=16.0, bold=True)

        c2 = row.cells[2]
        c2.width = Cm(widths[2])
        c2.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _set_cell_margins(c2, 20, 20, 20, 20)
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.first_line_indent = Cm(0)
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(0)
        p2.add_run().add_picture(io.BytesIO(img2), width=Cm(2.40), height=Cm(2.41))

        def _cover_p(
            text: str,
            size_pt: float,
            bold: bool = True,
            space_before: float = 0,
            space_after: float = 6,
            line_spacing: float = 1.35,
        ) -> None:
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            p.paragraph_format.line_spacing = line_spacing
            p.paragraph_format.space_before = Pt(space_before)
            p.paragraph_format.space_after = Pt(space_after)
            r = p.add_run(text)
            _set_run_font(r, size_pt=size_pt, bold=bold)

        _cover_p("BÁO CÁO", 20.0, bold=True, space_before=48, space_after=8)
        _cover_p("Đồ án cuối kỳ — DSS", 19.0, bold=True, space_before=0, space_after=36)
        _cover_p("Tên Đề Tài:", 16.0, bold=True, space_before=0, space_after=10)
        _cover_p(
            "FedGraph: Hệ thống gợi ý việc làm bảo vệ quyền riêng tư\n"
            "sử dụng LightGCN và Học liên kết đa silo\n"
            "(Cross-Silo Federated Learning)",
            16.0,
            bold=True,
            space_before=0,
            space_after=72,
            line_spacing=1.4,
        )

        _cover_p(
            "Giảng viên hướng dẫn:    [Họ và tên Giảng viên hướng dẫn]",
            14.0,
            bold=True,
            space_before=0,
            space_after=14,
        )

        stu_tbl = self.doc.add_table(rows=3, cols=3)
        stu_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(stu_tbl, border_sz=4, none=False)
        stu_widths = [5.5, 4.5, 5.5]
        _set_fixed_table_layout(stu_tbl, stu_widths)

        stu_rows = [
            ["HỌ VÀ TÊN", "Lớp Học Phần", "Mã Sinh Viên"],
            ["Phan Gia Bảo", "—", "102220265"],
            ["Nguyễn Văn Chương", "—", "102220267"],
        ]
        for r_idx, r_data in enumerate(stu_rows):
            row_obj = stu_tbl.rows[r_idx]
            _set_row_header_and_cant_split(row_obj, is_header=(r_idx == 0))
            for c_idx, val in enumerate(r_data):
                cell = row_obj.cells[c_idx]
                cell.width = Cm(stu_widths[c_idx])
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                _set_cell_margins(cell, 90, 90, 80, 80)
                cp = cell.paragraphs[0]
                cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cp.paragraph_format.first_line_indent = Cm(0)
                cp.paragraph_format.line_spacing = 1.2
                cp.paragraph_format.space_before = Pt(0)
                cp.paragraph_format.space_after = Pt(0)
                cr = cp.add_run(val)
                _set_run_font(cr, size_pt=13.0, bold=(r_idx == 0))

        _cover_p("ĐÀ NẴNG, 11/2026", 14.0, bold=False, space_before=66, space_after=0)

    # --- Chuyển sang Section 1 (Front matter + Body) -----------------
    def start_main_section(self) -> None:
        sec1 = self.doc.add_section(WD_SECTION.NEW_PAGE)
        _configure_section_geometry(sec1)
        _set_section_pg_num_start(sec1, start=1)
        sec1.different_first_page_header_footer = False

        sec1.header.is_linked_to_previous = False
        sec1.footer.is_linked_to_previous = False

        hp = sec1.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        hp.paragraph_format.first_line_indent = Cm(0)
        hp.paragraph_format.space_before = Pt(0)
        hp.paragraph_format.space_after = Pt(0)
        hr = hp.add_run("Báo Cáo Đồ Án Cuối Kỳ — DSS")
        _set_run_font(hr, size_pt=10.0, italic=True)

        for p_old in list(sec1.footer.paragraphs):
            p_old._element.getparent().remove(p_old._element)
        ftbl = sec1.footer.add_table(rows=1, cols=2, width=Cm(USABLE_WIDTH_CM))
        ftbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(ftbl, none=True)
        fwidths = [12.5, 3.0]
        _set_fixed_table_layout(ftbl, fwidths)
        frow = ftbl.rows[0]
        _set_row_header_and_cant_split(frow)
        fc0, fc1 = frow.cells[0], frow.cells[1]
        fc0.width, fc1.width = Cm(fwidths[0]), Cm(fwidths[1])
        _set_cell_margins(fc0, 0, 0, 0, 0)
        _set_cell_margins(fc1, 0, 0, 0, 0)

        fp0 = fc0.paragraphs[0]
        fp0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        fp0.paragraph_format.first_line_indent = Cm(0)
        fp0.paragraph_format.space_before = Pt(0)
        fp0.paragraph_format.space_after = Pt(0)
        fr_left = fp0.add_run("Phan Gia Bảo – Nguyễn Văn Chương")
        _set_run_font(fr_left, size_pt=10.0, italic=True)

        fp1 = fc1.paragraphs[0]
        fp1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        fp1.paragraph_format.first_line_indent = Cm(0)
        fp1.paragraph_format.space_before = Pt(0)
        fp1.paragraph_format.space_after = Pt(0)
        add_complex_field(fp1, "PAGE", placeholder="1", size_pt=10.0, italic=True)

    # --- Phần đầu trang (MỤC LỤC, HÌNH ẢNH, BẢNG BIỂU, TỪ VIẾT TẮT) -
    def build_front_matter(self) -> None:
        # 1. MỤC LỤC (Trang 1 sau bìa)
        p_toc_title = self.doc.add_paragraph("MỤC LỤC", style="FrontTitle")
        p_toc_title.paragraph_format.page_break_before = False
        add_sdt_toc_block(
            self.doc,
            gallery_name="Table of Contents",
            style_id="TOC1",
            instr='TOC \\o "1-3" \\h \\z \\u',
            placeholder="Cập nhật trường (Update Field) trong Word để hiển thị Mục lục.",
        )

        # 2. DANH MỤC HÌNH ẢNH (Trang mới)
        p_lof_title = self.doc.add_paragraph("DANH MỤC HÌNH ẢNH", style="FrontTitle")
        p_lof_title.paragraph_format.page_break_before = True
        add_sdt_toc_block(
            self.doc,
            gallery_name="Table of Figures",
            style_id="TableofFigures",
            instr='TOC \\h \\z \\c "Hình"',
            placeholder="Cập nhật trường (Update Field) trong Word để hiển thị Danh mục hình ảnh.",
        )

        # 3. DANH MỤC BẢNG BIỂU (Trang mới)
        p_lot_title = self.doc.add_paragraph("DANH MỤC BẢNG BIỂU", style="FrontTitle")
        p_lot_title.paragraph_format.page_break_before = True
        add_sdt_toc_block(
            self.doc,
            gallery_name="Table of Figures",
            style_id="TableofFigures",
            instr='TOC \\h \\z \\c "Bảng"',
            placeholder="Cập nhật trường (Update Field) trong Word để hiển thị Danh mục bảng biểu.",
        )

        # 4. DANH MỤC TỪ VIẾT TẮT (Trang mới)
        p_abb_title = self.doc.add_paragraph("DANH MỤC TỪ VIẾT TẮT", style="FrontTitle")
        p_abb_title.paragraph_format.page_break_before = True
        abbr_rows = [
            ["BPR", "Bayesian Personalized Ranking", "Hàm mất mát xếp hạng cặp cho phản hồi ẩn [3]"],
            ["CI", "Confidence Interval", "Khoảng tin cậy Bootstrap 95% (1.000 lần lấy mẫu lại)"],
            ["DLG", "Deep Leakage from Gradients", "Tấn công tái tạo dữ liệu gốc từ vector gradient chia sẻ [13]"],
            ["DP-SGD", "Differentially Private SGD", "Cắt ngưỡng gradient + nhiễu Gaussian bảo vệ riêng tư [11]"],
            ["FedAvg", "Federated Averaging", "Thuật toán tổng hợp trung bình trọng số liên kết [6]"],
            ["FedProx", "Federated Proximal", "Biến thể FL thêm thành phần phạt kìm hãm Client Drift [7]"],
            ["FL", "Federated Learning", "Học liên kết phân tán không gom dữ liệu thô [6, 8]"],
            ["GAT", "Graph Attention Network", "Mạng nơ-ron đồ thị dùng cơ chế chú ý lân cận"],
            ["GNN", "Graph Neural Network", "Mạng nơ-ron trên cấu trúc đồ thị"],
            ["GraphSAGE", "Graph Sample and Aggregate", "Mạng đồ thị quy nạp lấy mẫu và tổng hợp lân cận [4]"],
            ["Item-KNN", "Item-based K-Nearest Neighbors", "Lọc cộng tác dựa trên độ tương đồng cosine giữa tin [5]"],
            ["LightGCN", "Light Graph Convolution Network", "Mạng tích chập đồ thị tinh gọn cho lọc cộng tác [1]"],
            ["MRR@K", "Mean Reciprocal Rank at K", "Trung bình nghịch đảo thứ hạng của mục đúng đầu tiên"],
            ["NDCG@K", "Normalized Discounted Cumulative Gain", "Chỉ số chất lượng xếp hạng có trọng số vị trí tại top-K"],
            ["Non-IID", "Non-Independent and Identically Distributed", "Dữ liệu phân phối không đồng nhất giữa các silo [8, 10]"],
            ["O*NET", "Occupational Information Network", "Hệ thống phân loại nghề nghiệp & kỹ năng chuẩn Hoa Kỳ [32]"],
            ["Recall@K", "Recall at K", "Tỷ lệ mục đúng xuất hiện trong danh sách top-K gợi ý"],
            ["SecAgg", "Secure Aggregation", "Giao thức mật mã che giấu cập nhật từng client [12]"],
            ["SOC", "Standard Occupational Classification", "Mã phân loại nghề nghiệp chuẩn 6 ký tự (soc[:7])"],
        ]
        self._simple_table(
            headers=["Từ viết tắt", "Thuật ngữ đầy đủ", "Ý nghĩa trong đề tài FedGraph"],
            rows=abbr_rows,
            widths=[2.5, 5.3, 7.7],
            font_size=10.5,
            col_alignments=[
                WD_ALIGN_PARAGRAPH.CENTER,
                WD_ALIGN_PARAGRAPH.LEFT,
                WD_ALIGN_PARAGRAPH.LEFT,
            ],
            pad_tb=34,
        )

    # --- Các hàm dựng thành phần nội dung ---------------------------
    def h1(self, text: str) -> None:
        p = self.doc.add_paragraph(style="Heading 1")
        r = p.add_run(text)
        _set_run_font(r, size_pt=16.0, bold=True)

    def h2(self, text: str) -> None:
        p = self.doc.add_paragraph(style="Heading 2")
        r = p.add_run(text)
        _set_run_font(r, size_pt=14.0, bold=True)

    def h3(self, text: str) -> None:
        p = self.doc.add_paragraph(style="Heading 3")
        r = p.add_run(text)
        _set_run_font(r, size_pt=13.0, bold=True)

    def _track_citations(self, text: str) -> None:
        for grp in re.findall(r"\[([0-9,\s\-–]+)\]", text):
            for part in grp.split(","):
                part = part.strip()
                if "-" in part or "–" in part:
                    sep = "–" if "–" in part else "-"
                    bounds = [x.strip() for x in part.split(sep)]
                    if len(bounds) == 2 and bounds[0].isdigit() and bounds[1].isdigit():
                        for k in range(int(bounds[0]), int(bounds[1]) + 1):
                            self.inline_citations.add(k)
                elif part.isdigit():
                    self.inline_citations.add(int(part))

    def p(self, text: str) -> None:
        self._track_citations(text)
        para = self.doc.add_paragraph(style="Normal")
        self._add_rich_runs(para, text, size_pt=13.0)

    def bullet(self, text: str) -> None:
        self._track_citations(text)
        para = self.doc.add_paragraph(style="Normal")
        pf = para.paragraph_format
        pf.left_indent = Cm(1.0)
        pf.first_line_indent = Cm(-0.4)
        pf.space_before = Pt(0)
        pf.space_after = Pt(4)
        self._add_rich_runs(para, "•  " + text, size_pt=13.0)

    @staticmethod
    def _add_rich_runs(para, text: str, size_pt: float = 13.0) -> None:
        sentinel = "\uFFF0ONET\uFFF0"
        safe = text.replace("O*NET", sentinel)
        tokens = re.split(
            r"(\*\*(?:(?!\*\*).)+?\*\*|\*(?:(?!\*).)+?\*|`[^`]+`)", safe
        )
        for tok in tokens:
            if not tok:
                continue
            if tok.startswith("**") and tok.endswith("**"):
                inner = tok[2:-2].replace("`", "").replace(sentinel, "O*NET")
                r = para.add_run(inner)
                _set_run_font(r, size_pt=size_pt, bold=True)
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                inner = tok[1:-1].replace("`", "").replace(sentinel, "O*NET")
                r = para.add_run(inner)
                _set_run_font(r, size_pt=size_pt, italic=True)
            elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
                inner = tok[1:-1].replace(sentinel, "O*NET")
                r = para.add_run(inner)
                _set_run_font(r, size_pt=size_pt - 0.5)
            else:
                r = para.add_run(tok.replace(sentinel, "O*NET"))
                _set_run_font(r, size_pt=size_pt)

    def equation(self, expr: str, chapter: int) -> str:
        self.eq_count += 1
        eq_label = f"({chapter}.{self.eq_count})"
        tbl = self.doc.add_table(rows=1, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(tbl, none=True)
        widths = [13.7, 1.8]
        _set_fixed_table_layout(tbl, widths)
        row = tbl.rows[0]
        _set_row_header_and_cant_split(row)

        c0, c1 = row.cells[0], row.cells[1]
        c0.width, c1.width = Cm(widths[0]), Cm(widths[1])
        c0.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        c1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _set_cell_margins(c0, 50, 50, 40, 40)
        _set_cell_margins(c1, 50, 50, 20, 20)

        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.first_line_indent = Cm(0)
        p0.paragraph_format.line_spacing = 1.25
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(expr)
        eq_sz = 10.5 if len(expr) > 85 else (11.5 if len(expr) > 65 else 12.5)
        _set_run_font(r0, size_pt=eq_sz, italic=True)

        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p1.paragraph_format.first_line_indent = Cm(0)
        p1.paragraph_format.line_spacing = 1.25
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(eq_label)
        _set_run_font(r1, size_pt=13.0)

        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.first_line_indent = Cm(0)
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(4)
        return eq_label

    def algorithm_box(self, title: str, lines: list[str]) -> None:
        self.alg_count += 1
        tbl = self.doc.add_table(rows=2, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(tbl, border_sz=4, none=False)
        _set_fixed_table_layout(tbl, [USABLE_WIDTH_CM])

        r0 = tbl.rows[0]
        _set_row_header_and_cant_split(r0, is_header=True)
        c0 = r0.cells[0]
        c0.width = Cm(USABLE_WIDTH_CM)
        _set_cell_margins(c0, 60, 60, 100, 100)
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p0.paragraph_format.first_line_indent = Cm(0)
        p0.paragraph_format.line_spacing = 1.2
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        p0.paragraph_format.keep_with_next = True
        run0 = p0.add_run(f"Thuật toán {self.alg_count}. {title}")
        _set_run_font(run0, size_pt=11.5, bold=True)

        r1 = tbl.rows[1]
        _set_row_header_and_cant_split(r1, is_header=False)
        c1 = r1.cells[0]
        c1.width = Cm(USABLE_WIDTH_CM)
        _set_cell_margins(c1, 70, 70, 110, 110)
        for idx, line in enumerate(lines):
            lp = c1.paragraphs[0] if idx == 0 else c1.add_paragraph()
            lp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            lp.paragraph_format.first_line_indent = Cm(0)
            lp.paragraph_format.line_spacing = 1.15
            lp.paragraph_format.space_before = Pt(0)
            lp.paragraph_format.space_after = Pt(1)
            lr = lp.add_run(line)
            _set_run_font(lr, name="Courier New", size_pt=9.5)

        sp = self.doc.add_paragraph()
        sp.paragraph_format.first_line_indent = Cm(0)
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(4)

    def code_block(self, lines: list[str]) -> None:
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(tbl, border_sz=4, none=False)
        _set_fixed_table_layout(tbl, [USABLE_WIDTH_CM])
        row = tbl.rows[0]
        _set_row_header_and_cant_split(row)
        cell = row.cells[0]
        cell.width = Cm(USABLE_WIDTH_CM)
        _set_cell_margins(cell, 70, 70, 110, 110)
        for idx, line in enumerate(lines):
            lp = cell.paragraphs[0] if idx == 0 else cell.add_paragraph()
            lp.alignment = WD_ALIGN_PARAGRAPH.LEFT
            lp.paragraph_format.first_line_indent = Cm(0)
            lp.paragraph_format.line_spacing = 1.15
            lp.paragraph_format.space_before = Pt(0)
            lp.paragraph_format.space_after = Pt(1)
            lr = lp.add_run(line)
            _set_run_font(lr, name="Courier New", size_pt=9.5)
        sp = self.doc.add_paragraph()
        sp.paragraph_format.first_line_indent = Cm(0)
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(4)

    def figure(
        self,
        filename: str,
        caption: str,
        width_cm: float = 15.2,
        base_dir: Path | None = None,
    ) -> None:
        root_dir = base_dir if base_dir is not None else FIG_DIR
        path = root_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Thiếu tệp hình ảnh bắt buộc: {path}")
        self.fig_count += 1
        p_img = self.doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.first_line_indent = Cm(0)
        p_img.paragraph_format.space_before = Pt(6)
        p_img.paragraph_format.space_after = Pt(4)
        p_img.paragraph_format.keep_with_next = True
        p_img.add_run().add_picture(str(path), width=Cm(width_cm))

        p_cap = self.doc.add_paragraph(style="Caption")
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.first_line_indent = Cm(0)
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(8)
        r1 = p_cap.add_run("Hình ")
        _set_run_font(r1, size_pt=13.0, bold=True, italic=True)
        add_complex_field(
            p_cap,
            "SEQ Hình \\* ARABIC",
            placeholder=str(self.fig_count),
            size_pt=13.0,
            bold=True,
            italic=True,
        )
        r2 = p_cap.add_run(f". {caption}")
        _set_run_font(r2, size_pt=13.0, bold=True, italic=True)

    def _simple_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        widths: list[float],
        font_size: float = 11.5,
        col_alignments: list[Any] | None = None,
        pad_tb: int = 55,
        pad_lr: int = 60,
    ) -> None:
        tbl = self.doc.add_table(rows=1 + len(rows), cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(tbl, border_sz=4, none=False)
        _set_fixed_table_layout(tbl, widths)

        hdr_row = tbl.rows[0]
        _set_row_header_and_cant_split(hdr_row, is_header=True)
        for j, htxt in enumerate(headers):
            cell = hdr_row.cells[j]
            cell.width = Cm(widths[j])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            _set_cell_margins(cell, pad_tb + 10, pad_tb + 10, pad_lr, pad_lr)
            cp = cell.paragraphs[0]
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cp.paragraph_format.first_line_indent = Cm(0)
            cp.paragraph_format.line_spacing = 1.15
            cp.paragraph_format.space_before = Pt(0)
            cp.paragraph_format.space_after = Pt(0)
            cp.paragraph_format.keep_with_next = True
            r = cp.add_run(htxt)
            _set_run_font(r, size_pt=font_size, bold=True)

        for i, rdata in enumerate(rows):
            row_obj = tbl.rows[i + 1]
            _set_row_header_and_cant_split(row_obj, is_header=False)
            for j, val in enumerate(rdata):
                cell = row_obj.cells[j]
                cell.width = Cm(widths[j])
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                _set_cell_margins(cell, pad_tb, pad_tb, pad_lr, pad_lr)
                cp = cell.paragraphs[0]
                if col_alignments is not None:
                    cp.alignment = col_alignments[j]
                else:
                    cp.alignment = (
                        WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
                    )
                cp.paragraph_format.first_line_indent = Cm(0)
                cp.paragraph_format.line_spacing = 1.15
                cp.paragraph_format.space_before = Pt(0)
                cp.paragraph_format.space_after = Pt(0)
                self._add_rich_runs(cp, str(val), size_pt=font_size)

        sp = self.doc.add_paragraph()
        sp.paragraph_format.first_line_indent = Cm(0)
        sp.paragraph_format.space_before = Pt(0)
        sp.paragraph_format.space_after = Pt(4)

    def table(
        self,
        caption: str,
        headers: list[str],
        rows: list[list[str]],
        widths: list[float],
        font_size: float = 11.5,
        col_alignments: list[Any] | None = None,
        pad_tb: int = 55,
        pad_lr: int = 60,
    ) -> None:
        self.tab_count += 1
        p_cap = self.doc.add_paragraph(style="Caption")
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.first_line_indent = Cm(0)
        p_cap.paragraph_format.space_before = Pt(6)
        p_cap.paragraph_format.space_after = Pt(4)
        p_cap.paragraph_format.keep_with_next = True

        r1 = p_cap.add_run("Bảng ")
        _set_run_font(r1, size_pt=13.0, bold=True, italic=True)
        add_complex_field(
            p_cap,
            "SEQ Bảng \\* ARABIC",
            placeholder=str(self.tab_count),
            size_pt=13.0,
            bold=True,
            italic=True,
        )
        r2 = p_cap.add_run(f". {caption}")
        _set_run_font(r2, size_pt=13.0, bold=True, italic=True)

        self._simple_table(
            headers=headers,
            rows=rows,
            widths=widths,
            font_size=font_size,
            col_alignments=col_alignments,
            pad_tb=pad_tb,
            pad_lr=pad_lr,
        )

    # =================================================================
    # 5. Nội dung học thuật 6 Chương + Tài liệu tham khảo
    # =================================================================
    def build_chapters(self) -> None:
        m = self.data["meta"]
        cuda = self.data["cuda"]
        cpu = self.data["cpu"]
        lo = self.data["local_only"]
        meda = self.data["medajob"]
        ablation = self.data["ablation"]
        sweep = self.data["sweep"]

        g = cuda["graph"]
        sp = cuda["split"]
        cs = cuda["cross_silo"]
        eda = cuda["eda"]
        models = cuda["models"]
        cpu_models = cpu["models"]
        per_c = cuda["per_client"]
        lat_cuda = cuda["latency"]
        lat_cpu = cpu["latency"]
        c_stats = m["clients"]["size_stats"]
        emp = m["employer_extraction"]
        src_counts = emp["source_counts"]

        # -------------------------------------------------------------
        # CHƯƠNG 1
        # -------------------------------------------------------------
        self.h1("CHƯƠNG 1. TỔNG QUAN BÀI TOÁN VÀ NGHIÊN CỨU LIÊN QUAN")

        self.h2("1.1. Đặt vấn đề và bối cảnh hệ gợi ý việc làm quy mô lớn")
        self.p(
            "Trong kỷ nguyên tuyển dụng trực tuyến, các nền tảng kết nối nhân lực đóng vai trò "
            "hạ tầng trung gian xử lý hàng triệu lượt ứng tuyển mỗi tháng [27, 31]. Khác biệt "
            "căn bản với hệ gợi ý thương mại điện tử hay giải trí (như phim ảnh, âm nhạc), bài "
            "toán gợi ý việc làm (Job Recommender Systems — JRS) chịu đồng thời bốn ràng buộc cấu "
            "trúc khắt khe [27, 28]: (i) tính chất ghép đôi hai phía (*reciprocal matching*), đòi "
            "hỏi tin tuyển dụng không chỉ phù hợp với sở thích ứng viên mà năng lực ứng viên cũng "
            "phải đáp ứng chuẩn kỹ năng nghề nghiệp của doanh nghiệp; (ii) vòng đời tin tuyển "
            "dụng ngắn hạn khiến tỷ lệ tin mới chưa có tương tác luôn ở mức cao; (iii) độ thưa "
            "dữ liệu cực đoan trên ma trận tương tác; và (iv) tính nhạy cảm pháp lý lẫn bí mật "
            "cạnh tranh nhân sự của hồ sơ tuyển dụng [28]."
        )
        self.p(
            "Trên bộ dữ liệu thực nghiệm quy mô lớn **CareerBuilder + O*NET 29.3 (V3)** của "
            f"đồ án, đồ thị tương tác sau làm sạch bao gồm {fi(g['n_users'])} ứng viên và "
            f"{fi(g['n_jobs'])} tin tuyển dụng thuộc {fi(cs['n_clients'])} nhà tuyển dụng độc "
            f"lập. Mật độ tương tác trên ma trận `user × job` đạt độ thưa lên tới "
            f"{eda['sparsity_pct']:.5f}% (chỉ {m['sparsity_pct']:.6f}% cặp khả dĩ có cạnh "
            f"ứng tuyển), trong đó {fi(sp['n_jobs_cold_start'])} tin tuyển dụng (chiếm "
            f"{sp['pct_jobs_cold_start']:.3f}%) là tin khởi đầu lạnh (*cold-start jobs*) hoàn "
            "toàn vắng mặt lượt ứng tuyển trong tập huấn luyện [27, 31]. Thêm vào đó, 55,56% số "
            "cạnh `user–job` (242.721 / 436.893 cạnh, tương ứng 88,32% tổng số ứng viên) thuộc về "
            "nhóm ứng viên có dưới 5 lượt nộp đơn, làm suy giảm nặng nề tín hiệu lọc cộng tác "
            "thuần túy nếu thiếu thông tin nghề nghiệp–kỹ năng bổ trợ [29]."
        )
        self.p(
            "Bên cạnh bài toán độ thưa, nghịch lý lớn nhất của các hệ gợi ý tuyển dụng hiện đại "
            "nằm ở **quyền riêng tư và chủ quyền dữ liệu (Data Privacy & Silo Isolation)**. Theo "
            "quy định bảo vệ dữ liệu như GDPR [28] và chính sách bảo mật nội bộ, các doanh "
            "nghiệp không thể tự do gom nhật ký ứng tuyển (`user–job` applications) hay hồ sơ "
            "lịch sử việc làm (`user_history`) về một kho lưu trữ tập trung để huấn luyện GNN "
            "toàn cục. Ngược lại, nếu mỗi doanh nghiệp tự huấn luyện mô hình riêng rẽ "
            "(*Local-only*), tầm nhìn bị cô lập trong phạm vi vài chục lượt nộp đơn cục bộ sẽ "
            "bỏ lỡ hoàn toàn hành vi chuyển dịch nghề nghiệp đa công ty của người tìm việc [8, 10]."
        )

        self.h2("1.2. Bản chất Cross-Silo Non-IID và mâu thuẫn cô lập dữ liệu")
        self.p(
            "Khảo sát định lượng trên tập dữ liệu V3 phơi bày bản chất **Cross-Silo Federated "
            "Learning** [8] đặc trưng của thị trường tuyển dụng: trong tổng số "
            f"{fi(cs['n_clients'])} nhà tuyển dụng (employer silos), có tới "
            f"{cs['pct_users_multi_client']:.2f}% ứng viên ({fi(m['clients']['n_users_multi_client'])} "
            f"người) nộp đơn vào từ hai doanh nghiệp trở lên (trung bình "
            f"{cs['mean_clients_per_user']:.2f} silo/ứng viên). Tuy nhiên, theo đúng ranh giới "
            "sở hữu thực tế, một cạnh ứng tuyển `(u, j)` chỉ tồn tại trong silo sở hữu tin "
            "tuyển dụng `client_of_job[j]`, chứ không thuộc về `client_of_user[u]`. Hệ quả "
            "là chỉ có 45,711% cạnh huấn luyện và vỏn vẹn "
            f"**{cs['pct_same_client_test']:.3f}%** cạnh kiểm thử rơi vào cùng nhà tuyển dụng "
            "với silo chính của ứng viên; thậm chí trên tập đánh giá của 20 silo lớn nhất, tới "
            f"**{lo['silo_cross_client_stats']['pct_eval_users_cross_silo_only']:.1f}%** (552/800) "
            "ứng viên chỉ có nhãn đúng nằm ở silo khác. Bất kỳ hệ gợi ý nào bỏ qua liên kết liên "
            "silo đều thất bại trên hơn hai phần ba người dùng đánh giá."
        )
        self.p(
            "Đồng thời, phân phối dữ liệu giữa 9.116 silos thể hiện tính chất **Non-IID lệch "
            "mạnh về quy mô lẫn miền nghề nghiệp (quantity skew & domain skew)** [8, 10]. "
            f"Doanh nghiệp lớn nhất (`randstad`, `client_id=0`) nắm giữ {fi(c_stats['max'])} "
            f"lượt ứng tuyển (1,09% toàn tập, 4.215 ứng viên và 603 tin), gấp **474,5 lần** "
            f"ngưỡng tối thiểu ({c_stats['min']} lượt); về số cạnh huấn luyện, tỷ lệ chênh lệch "
            f"đỉnh–đáy lên tới **864 lần** (4.320 so với 5 cạnh), với trung vị chỉ 23 lượt/silo "
            f"(Q1 = 15, Q3 = 47). Trong tập 9.116 silos có 418 doanh nghiệp chỉ sở hữu 1 tin "
            "tuyển dụng và 3.877 doanh nghiệp có từ 3 tin trở xuống. Khi huấn luyện liên kết trên "
            "dữ liệu phân mảnh mất cân đối như vậy, hai hệ quả nghiêm trọng phát sinh: (1) nếu "
            "tăng số bước tối ưu cục bộ tại mỗi silo, trọng số embedding cục bộ sẽ trượt về phân "
            "phối hẹp của riêng doanh nghiệp đó, gây ra **Client Drift** [7, 9]; và (2) nếu tổng "
            "hợp thiếu công bằng, nhóm doanh nghiệp nhỏ (long-tail) dễ chịu thiệt thòi rõ rệt "
            "về độ chính xác xếp hạng [10, 22]."
        )

        self.h2("1.3. Tổng quan các nghiên cứu liên quan")

        self.h3("1.3.1. Lọc cộng tác và Mạng nơ-ron đồ thị (Graph Collaborative Filtering)")
        self.p(
            "Các phương pháp lọc cộng tác nền tảng bắt đầu từ độ tương đồng lân cận **Item-KNN** "
            "[5] (tính độ tương đồng cosine trên ma trận tương tác nhị phân) và phân rã ma trận "
            "xếp hạng cặp **BPR-MF** [3] tối ưu hóa trực tiếp thứ tự tương đối cho phản hồi ẩn. "
            "Bước chuyển sang biểu diễn đồ thị hai phía `user–item` được khởi xướng bởi **NGCF** "
            "[2] nhằm truyền thông điệp bậc cao (*high-order connectivity*) qua nhiều tầng tích "
            "chập. Tuy nhiên, He et al. [1] thông qua thực nghiệm cắt giảm trên **LightGCN** đã "
            "chứng minh một phát hiện có giá trị lớn cho hệ thống phân tán: trong bài toán lọc "
            "cộng tác thuần ID (không có thuộc tính nút phong phú), hai thành phần kinh điển của "
            "GCN là ma trận biến đổi đặc trưng `W` và hàm kích hoạt phi tuyến `σ(·)` không những "
            "dư thừa mà còn gây quá khớp và suy giảm độ chính xác. Bằng cách giữ lại thuần túy "
            "bước lan truyền chuẩn hóa bậc đối xứng và tổ hợp tuyến tính giữa các tầng, LightGCN "
            "vừa đạt hiệu năng vượt trội NGCF (~16%) vừa giảm tối đa số lượng tham số cần đồng "
            "bộ qua mạng. Trong đồ án, nhóm cũng đối chứng với **GraphSAGE** [4] (tổng hợp trung "
            "bình lân cận) và **GAT** (mạng chú ý đồ thị có giới hạn bậc mẫu) để kiểm định giả "
            "thuyết này trên đồ thị tuyển dụng cực thưa."
        )

        self.h3("1.3.2. Học liên kết Cross-Silo, Client Drift và Bảo mật Gradient")
        self.p(
            "Thuật toán **FedAvg** [6] đặt nền móng cho Học liên kết bằng cơ chế huấn luyện "
            "SGD nhiều bước tại client và tổng hợp trung bình có trọng số theo kích thước dữ "
            "liệu trên server. Tài liệu tổng quan chuẩn mực của **Kairouz et al.** [8] phân biệt "
            "rành mạch hai mô hình triển khai: *Cross-Device FL* (hàng triệu thiết bị di động "
            "không ổn định) và *Cross-Silo FL* (các tổ chức/doanh nghiệp có hạ tầng ổn định, mỗi "
            "silo đại diện một kho dữ liệu độc lập như 9.116 nhà tuyển dụng trong FedGraph). Để "
            "khắc phục **Client Drift** trên phân phối Non-IID [10], **FedProx** [7] bổ sung "
            "thành phần chính quy hóa proximal `μ/2 ||w − w^t||²`, còn **SCAFFOLD** [9] dùng "
            "biến điều khiển (*control variates*) hiệu chỉnh phương sai gradient giữa các client."
        )
        self.p(
            "Ở khía cạnh an toàn dữ liệu, công trình đột phá **Deep Leakage from Gradients "
            "(DLG)** của Zhu et al. [13] chứng minh rằng một máy chủ trung thực-nhưng-tò-mò "
            "(*honest-but-curious*) vẫn có thể giải bài toán tối ưu ngược để tái tạo lại dữ liệu "
            "gốc từ vector gradient chia sẻ ở dạng rõ. Nhằm khóa chặt lỗ hổng này trong môi "
            "trường sản xuất, hai trụ cột phòng thủ chuẩn hóa gồm **DP-SGD** [11] (cắt ngưỡng "
            "chuẩn gradient kết hợp nhiễu Gaussian với *Moments Accountant* kiểm soát ngân sách "
            "(ε, δ)) và **Practical Secure Aggregation** [12] (giao thức mật mã bảo đảm server "
            "chỉ quan sát được tổng hợp cuối cùng và chịu được client dropout). Song song đó, "
            "**Deep Gradient Compression (DGC)** [14] cho thấy việc cắt tỉa chỉ giữ lại phần tử "
            "lớn nhất (**Top-K sparsification**) hoặc lượng tử hóa `FP16` giúp tiết kiệm hàng "
            "chục lần băng thông truyền thông mà vẫn bảo toàn khả năng hội tụ."
        )

        self.h3("1.3.3. Federated Recommendation và Subgraph Federated Learning")
        self.p(
            "Nhánh nghiên cứu **Federated Recommendation (FedRec)** [26] khởi đầu từ **FCF** "
            "[16] (giữ user embedding cục bộ và đồng bộ item factors), **MetaMF** [18] (dùng "
            "meta-network sinh trọng số cá nhân hóa), **FedRec** [19] (trung bình lai tránh lộ "
            "tập item đã tương tác) và **FedFast** [17] (cải tiến lấy mẫu đại diện *ActvSAMP* "
            "cùng tổng hợp thích ứng *ActvAGG* giúp đẩy nhanh tốc độ hội tụ trên tập item lớn). "
            "Khi kết hợp với mạng nơ-ron đồ thị [24, 25], các framework tiêu biểu gồm: "
            "**FedPerGNN** [15] (mỗi thiết bị người dùng giữ đồ thị cá nhân bậc 1, sử dụng "
            "LDP và *pseudo-items* để mở rộng lân cận ẩn danh), **FedSage+** [21] (huấn luyện "
            "mô hình sinh *Neighbor Generator* ước lượng các nút lân cận bị mất do chia cắt đồ "
            "thị con), **FED-PUB** [22] (cụm hóa cộng đồng ẩn dựa trên độ tương đồng chức năng "
            "để cá nhân hóa đồ thị con Non-IID), và **FedGraphNN** [23] (chuẩn benchmark đánh "
            "giá GNN phân tán). Đáng chú ý, công trình **FedGraph (Chen et al., IEEE TPDS 2022)** "
            "[20] dùng học tăng cường sâu (DRL) để lấy mẫu lân cận cho bài toán phân loại nút "
            "liên miền—tuy trùng tên gọi với đồ án nhưng khác biệt hoàn toàn về bài toán, kiến "
            "trúc và phân vùng dữ liệu (gợi ý việc làm Cross-Silo không chia sẻ cạnh người dùng "
            "qua cầu nối bản thể học công khai O*NET)."
        )

        self.h3("1.3.4. Hệ gợi ý việc làm dựa trên đồ thị kỹ năng và O*NET")
        self.p(
            "Trong lĩnh vực e-recruitment, **Skills2Job** [29] chứng minh ưu thế của việc mã hóa "
            "tin tuyển dụng và kỹ năng trên cơ sở dữ liệu đồ thị để vượt qua giới hạn khớp từ "
            "khóa cứng nhắc. Hệ thống phân loại nghề nghiệp quốc gia Hoa Kỳ **O*NET 29.3** [32] "
            "cung cấp mạng lưới chuẩn hóa giữa mã nghề SOC và danh mục kỹ năng công nghệ, tạo "
            "tiền đề cho **Alonso et al.** [30] kết hợp O*NET với mô hình **Transformer** nhằm "
            "nâng cao chất lượng đối khớp ngữ nghĩa ứng viên–công việc. Đồ án **FedGraph** kế "
            "thừa tư duy đồ thị kỹ năng này nhưng đặt vào ràng buộc **Cross-Silo FL**: chuyển "
            "toàn bộ cấu trúc `job–occupation–skill` thành **Public Graph Backbone** dùng chung, "
            "giữ kín tuyệt đối `user–job` và `user–occupation` tại từng silo doanh nghiệp."
        )

        self.table(
            caption="So sánh định vị hệ thống FedGraph với các nghiên cứu liên quan tiêu biểu",
            headers=[
                "Công trình / Hệ thống",
                "Phân vùng dữ liệu",
                "Kiến trúc & Học biểu diễn",
                "Cơ chế liên kết / Bảo mật",
                "Khác biệt & Vị trí của FedGraph",
            ],
            rows=[
                [
                    "LightGCN tập trung [1]",
                    "Tập trung 1 máy chủ",
                    "LightGCN L=2 + BPR",
                    "Đồ thị toàn cục (không riêng tư)",
                    "Đạt cận trên 0,7151 (FL Catalog), không đáp ứng ràng buộc tách silo.",
                ],
                [
                    "FedAvg / FedProx [6, 7]",
                    "FL tổng quát",
                    "Mạng nơ-ron / MF chuẩn",
                    "Trung bình trọng số / Proximal μ",
                    "Cần chỉnh sửa thành Sparse Touched-Node cho embedding đồ thị thưa.",
                ],
                [
                    "FedPerGNN [15]",
                    "Cross-Device (theo user)",
                    "GNN cá nhân hóa",
                    "Trao đổi embedding + LDP + pseudo-items",
                    "Phức tạp giao thức mở rộng lân cận; không thiết kế cho silo doanh nghiệp.",
                ],
                [
                    "FedSage+ [21]",
                    "Subgraph FL tổng quát",
                    "GraphSAGE + Generator",
                    "Sinh nút lân cận bị cắt đứt",
                    "Chi phí sinh nút giả cao; không tận dụng sẵn tri thức nghề công khai.",
                ],
                [
                    "FED-PUB [22]",
                    "Subgraph FL Non-IID",
                    "GNN + mặt nạ cụm ẩn",
                    "Tổng hợp theo tương đồng chức năng",
                    "Hướng mở rộng tiềm năng cho 5.262 client nhỏ (long-tail) của FedGraph.",
                ],
                [
                    "FedGraph (TPDS '22) [20]",
                    "Cross-client đồ thị con",
                    "GNN + DRL sampling",
                    "Cộng tác liên miền phân loại nút",
                    "Trùng tên gọi; giải node classification thay vì job recommendation.",
                ],
                [
                    "Skills2Job / O*NET+BERT [29, 30]",
                    "Tập trung trên GraphDB",
                    "Skill-Job Graph / Transformer",
                    "Bản thể học kỹ năng – O*NET",
                    "Chưa giải quyết bài toán học phân tán Cross-Silo giữa nhiều nhà tuyển dụng.",
                ],
                [
                    "**FedGraph V3 (Đồ án)**",
                    "**Cross-Silo (9.116 DN)**",
                    "**LightGCN L=2 + Sparse FedAvg**",
                    "**Public Backbone O*NET + GraphSafe**",
                    "**0 B raw user–job rời client; nối 9.116 silo qua 52.544 cạnh O*NET.**",
                ],
            ],
            widths=[3.1, 2.5, 2.9, 3.2, 3.8],
            font_size=10.0,
            pad_tb=45,
        )

        self.h2("1.4. Mục tiêu, phạm vi và đóng góp chính của đề tài")
        self.p(
            "Từ khoảng trống nghiên cứu đã định danh, đồ án **FedGraph** đề ra bốn mục tiêu và "
            "đóng góp trọng tâm: (1) Xây dựng quy trình tiền xử lý tiết kiệm bộ nhớ (`341,3 MB` "
            "RAM) hợp nhất dữ liệu CareerBuilder và O*NET 29.3 thành đồ thị không đồng nhất V3 "
            "với `264.995` nút, `764.364` cạnh, phân chia đúng `9.116` employer silos và loại bỏ "
            "rò rỉ đường vòng 2 bước nhảy; (2) Phát triển thuật toán **Cross-Silo LightGCN với "
            "Sparse Touched-Node FedAvg** và thực hiện hệ thống đối chứng toàn diện trên cả "
            "**Global Catalog** (`82.876` tin), **FL Catalog** (`9.058` / `4.511` / `956` tin) "
            "cùng thực nghiệm tái lập `Local-only Strict Silo` và `Stitched Upper Bound`; (3) Thực "
            "hiện 15 biến thể Ablation và 8 cấu hình Sweep để định lượng giá trị Public Graph "
            "Backbone (+9,00 điểm phần trăm), hiệu ứng mở rộng số silo và cơ chế Client Drift; và "
            "(4) Hoàn thiện hệ thống Full-Stack gồm PostgreSQL 16 (>21,3 triệu dòng), FastAPI + "
            "WebSocket (15 API) và React 19 + Three.js (5 trang tương tác) phục vụ trực quan hóa "
            "3D, giải thích lan truyền 2-hop và giám sát độ trễ thực tế."
        )

        # -------------------------------------------------------------
        # CHƯƠNG 2
        # -------------------------------------------------------------
        self.h1("CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ PHƯƠNG PHÁP ĐỀ XUẤT")

        self.h2("2.1. Định thức bài toán đồ thị Public Backbone – Private Silos")
        self.p(
            "Xét tập hợp gồm C = 9.116 nhà tuyển dụng độc lập (silos). Đồ thị tri thức tuyển dụng "
            "không đồng nhất toàn cục được ký hiệu là G = (V, E), trong đó tập đỉnh V phân hoạch "
            "thành bốn tập thực thể rời nhau: V = V_U ∪ V_J ∪ V_O ∪ V_S, với V_U là tập ứng viên "
            f"(|V_U| = {fi(g['n_users'])}), V_J là tập tin tuyển dụng (|V_J| = {fi(g['n_jobs'])}), "
            f"V_O là tập mã nghề nghiệp O*NET chuẩn `soc[:7]` (|V_O| = {fi(g['n_occ'])}) và V_S là "
            f"tập kỹ năng công nghệ (|V_S| = {fi(g['n_skill'])}). Tổng số thực thể là |V| = "
            f"{fi(g['n_nodes'])} nút."
        )
        self.p(
            "Nhằm bảo đảm tính hợp lệ của kịch bản **Cross-Silo Federated Learning** [8, 24], tập "
            "cạnh E (gồm 764.364 cạnh vô hướng trước khi đối xứng hóa) được phân định rành mạch "
            "thành hai phân vùng có ranh giới riêng tư bất khả xâm phạm:"
        )
        self.bullet(
            f"**Phân vùng Riêng tư (Private Edges — E_priv, {fi(g['edges_by_type']['0'] + g['edges_by_type']['3'])} "
            f"cạnh = 93,13%):** bao gồm tập cạnh ứng tuyển `user–job` (type 0: {fi(g['edges_by_type']['0'])} "
            f"cạnh) và tập cạnh nghề nghiệp lịch sử `user–occupation` (type 3: {fi(g['edges_by_type']['3'])} "
            "cạnh trích từ `user_history`). Quy tắc phân quyền bắt buộc là mỗi cạnh (u, j) ∈ E^{u-j} "
            "chỉ nằm tại đúng silo c = client_of_job[j] sở hữu tin j. Cạnh riêng tư tuyệt đối không "
            "được lưu tập trung hay truyền qua mạng dưới bất kỳ hình thức nào."
        )
        self.bullet(
            f"**Xương sống Công khai (Public Graph Backbone — E_pub, {fi(g['edges_by_type']['1'] + g['edges_by_type']['2'])} "
            f"cạnh = 6,87%):** bao gồm {fi(g['edges_by_type']['1'])} cạnh `job–occupation` (type 1) "
            f"và {fi(g['edges_by_type']['2'])} cạnh `occupation–skill` (type 2), nối kết "
            f"{fi(m['nodes']['n_public_nodes'])} nút công khai (583 nghề + 7.760 kỹ năng) [32]. "
            "Thay vì lưu trực tiếp hàng chục triệu cạnh `user–skill` và `job–skill` vào đồ thị "
            "huấn luyện GNN (gây bùng nổ bộ nhớ), tín hiệu kỹ năng được truyền tự nhiên thông qua "
            "lan truyền 2 bước nhảy `user ↔ occupation ↔ skill ↔ occupation ↔ job`."
        )

        self.h2("2.2. Dẫn xuất toán học kiến trúc LightGCN và hàm mục tiêu BPR")
        self.p(
            "Trong kiến trúc GCN tiêu chuẩn hoặc NGCF [2], biểu diễn tại tầng l+1 được tính qua "
            "biến đổi tuyến tính và phi tuyến `E^(l+1) = σ(Â · E^(l) · W^(l))`. Tuy nhiên, He et al. "
            "[1] chứng minh rằng đối với đồ thị tương tác nơi mỗi nút chỉ được đại diện bằng vector "
            "nhúng ID (không có vector đặc trưng văn bản đầu vào nhiều chiều), phép nhân ma trận "
            "W^(l) làm tăng nguy cơ quá khớp và phá vỡ tính tương thích nội tại giữa các tầng, còn "
            "hàm ReLU triệt tiêu các thành phần âm vốn mang thông tin phân biệt quan trọng (như nhóm "
            "tác giả đã ghi nhận trực tiếp ở `notebooks/_p2.py:203-206` đối với GraphSAGE). Vì vậy, "
            "**LightGCN** chỉ giữ lại phép tổng hợp lân cận chuẩn hóa bậc đối xứng. Ký hiệu Ã = A + A^T "
            "là ma trận kề đối xứng hóa của đồ thị và D̃ là ma trận bậc đường chéo của (Ã + I) với "
            "D̃_{ii} = ∑_j (Ã_{ij} + δ_{ij}), quá trình lan truyền tầng thứ l được viết dưới dạng "
            "ma trận và dạng từng nút như sau:"
        )
        self.equation("E^(l+1) = D̃^(-1/2) (Ã + I) D̃^(-1/2) E^(l),        l = 0, 1, ..., L − 1", chapter=2)
        self.equation(
            "e_i^(l+1) = ( 1 / (d_i + 1) ) e_i^(l) + ∑_{j ∈ N(i)} ( 1 / √((d_i + 1)(d_j + 1)) ) e_j^(l)",
            chapter=2,
        )
        self.p(
            "Trong đó E^(0) ∈ R^(|V| × d) là tham số khả huấn duy nhất của toàn mạng (với d = 32, "
            "tổng dung lượng cho 264.995 nút là 8.479.840 tham số float32 ≈ 33,92 MB), và d_i = |N(i)| "
            "là bậc của nút i trên đồ thị vô hướng. Việc chia cho √((d_i+1)(d_j+1)) có ý nghĩa chuẩn "
            "hóa kép: vừa kìm hãm hiện tượng bùng nổ chuẩn (*norm explosion*) tại các nút nghề nghiệp "
            "O*NET có bậc rất lớn (hub nodes), vừa giảm trọng số của những kỹ năng quá phổ biến xuất "
            "hiện ở hàng trăm nghề. Sau L = 2 bước truyền tin (tương ứng khoảng cách 2-hop nối ứng "
            "viên và việc làm qua nghề hoặc kỹ năng), biểu diễn cuối cùng là tổ hợp đều qua các tầng "
            "(α_l = 1/(L+1)) và điểm xếp hạng được tính bằng tích vô hướng [1]:"
        )
        self.equation("E = (1 / (L + 1)) ∑_{l=0}^{L} E^(l),        ŷ_{u,j} = (e_u)^T e_j", chapter=2)
        self.p(
            "Vì nhật ký ứng tuyển chỉ ghi nhận tương tác dương (ứng viên u nộp đơn vào tin j+), không "
            "có điểm đánh giá âm tường minh, mô hình sử dụng hàm mất mát xếp hạng cặp **Bayesian "
            "Personalized Ranking (BPR)** [3]. Xuất phát từ giả định ưu tiên cặp độc lập giữa các "
            "ứng viên, BPR cực đại hóa xác suất hậu nghiệm để điểm dự đoán của tin dương ŷ_{u,j+} "
            "vượt tin âm lấy mẫu ngẫu nhiên ŷ_{u,j−}, tương đương tối thiểu hóa hàm mất mát:"
        )
        self.equation(
            "L_BPR(E^(0)) = − (1/|B|) ∑_{(u, j+, j−) ∈ B} ln σ(ŷ_{u,j+} − ŷ_{u,j−}) + λ ||E^(0)_B||_2^2",
            chapter=2,
        )
        self.p(
            "Với σ(z) = 1 / (1 + e^(-z)) là hàm sigmoid và λ = 10^(-5). Đạo hàm của hạng tử đối âm "
            "−ln σ(ŷ_{u,j+} − ŷ_{u,j−}) theo chênh lệch Δŷ = ŷ_{u,j+} − ŷ_{u,j−} bằng "
            "−(1 − σ(Δŷ)) = −σ(−Δŷ). Điều này tạo nên cơ chế tự điều tiết rất đẹp về mặt tối ưu: khi "
            "mô hình đã xếp tin dương cao hơn hẳn tin âm (Δŷ ≫ 0), độ lớn gradient tiến về 0 để "
            "tránh quá khớp; ngược lại khi tin âm bị xếp cao hơn tin dương (Δŷ < 0), gradient mạnh "
            "hơn sẽ kéo embedding e_u lại gần e_{j+} và đẩy xa e_{j−} đồng thời lan truyền ngược "
            "về cả các nút nghề nghiệp O*NET và kỹ năng trên đường đi 2-hop."
        )

        self.h2("2.3. Giao thức Học liên kết đa silo: Sparse Touched-Node FedAvg và FedProx")
        self.p(
            "Tại vòng truyền thông thứ t ∈ {1, ..., T}, máy chủ điều phối chọn tập K doanh nghiệp "
            "tham gia C_t (K = 50 trong thí nghiệm chính hoặc K = 20 trong Ablation). Mỗi silo c ∈ C_t "
            "chỉ giữ phần đồ thị con cục bộ G_c = (V_c, E_c) gồm các tin tuyển dụng do doanh nghiệp "
            "c sở hữu (`client_of_job[j] == c`), các ứng viên từng tương tác với tập tin đó, và phần "
            "xương sống công khai O*NET liên đới (tùy bật/tắt `include_occ`, `include_skill` trong "
            "Ablation). Sau khi tải về lát cắt tham số E_global^(t)[V_c], client thực hiện tối ưu "
            "cục bộ bằng Adam (`lr = 0,05`) với ngân sách `n_steps = max(20, min(100, 20 × local_epochs))` "
            "trên toàn bộ cạnh `user–job` cục bộ (cắt ngưỡng tối đa 4.096 cạnh/batch)."
        )
        self.p(
            "Khác với mô hình CNN nơi mọi client đều cập nhật toàn bộ không gian tham số, trong đồ "
            "thị thưa 264.995 nút, mỗi silo c chỉ chạm tới một tập nút cục bộ rất nhỏ V_c ⊂ V. Nếu áp "
            "dụng công thức trung bình toàn cục E^(t+1) = ∑_c (w_c / ∑ w_k) E_c^(t) trực tiếp trên "
            "cả ma trận, những nút v ∉ V_c sẽ bị kéo về 0 (hoặc bị giữ pha loãng tỷ lệ với tổng trọng "
            "số của các silo khác). Để giải quyết triệt để hiện tượng pha loãng thưa (*sparse dilution*), "
            "FedGraph cài đặt cơ chế **Sparse Touched-Node FedAvg** [6]: tại server, tổng có trọng số "
            "`num[v]` và tổng trọng số `den[v]` chỉ tích lũy trên đúng những client có chạm tới nút v; "
            "chỉ các nút `touched = {v : den[v] > 0}` được cập nhật theo tỷ lệ chuẩn hóa cục bộ, còn "
            "tập nút không tham gia giữ nguyên giá trị từ vòng t:"
        )
        self.equation(
            "E_global^(t+1)[v] = ( ∑_{c ∈ C_t: v ∈ V_c} w_c · E_c^(t)[v] ) / ( ∑_{c ∈ C_t: v ∈ V_c} w_c ),    ∀ v ∈ ⋃_{c ∈ C_t} V_c",
            chapter=2,
        )
        self.p(
            "Mặc định, trọng số đóng góp được gán tỷ lệ thuận với kích thước dữ liệu tương tác của "
            "silo: w_c = |E_c^{u-j}| (*FedAvg weighted*), đối chứng với w_c = 1 (*FedAvg unweighted*). "
            "Đồng thời, để khảo sát cơ chế chống **Client Drift** trên dữ liệu Non-IID, đồ án triển "
            "khai biến thể **FedProx** [7] (μ = 0,01) bổ sung thành phần phạt khoảng cách Frobenius "
            "so với điểm neo toàn cục E_global^(t) vào hàm mất mát cục bộ:"
        )
        self.equation(
            "L_FedProx^(c)(E_c) = L_BPR^(c)(E_c) + (μ / 2) || E_c − E_global^(t)[V_c] ||_F^2",
            chapter=2,
        )
        self.p(
            "Về mặt lý thuyết [7, 9], khi tăng số epoch cục bộ (ví dụ `local_epochs = 5` tương ứng "
            "100 bước gradient), nghiệm cục bộ E_c^⋆ dần hội tụ về điểm tối ưu riêng của doanh nghiệp "
            "c thay vì cực tiểu toàn cục chung. Vì tập ứng viên và tập việc làm giữa các doanh nghiệp "
            "có độ lệch phân bố cao, tổng hợp tuyến tính các vector đã trôi xa nhau tạo ra sai số "
            "trung bình hóa (*aggregation bias*), giải thích lý do hiệu năng có thể suy giảm khi huấn "
            "luyện cục bộ quá sâu."
        )

        self.table(
            caption="Siêu tham số mặc định của mô hình LightGCN và giao thức Cross-Silo FL (V3)",
            headers=["Tham số / Thành phần", "Giá trị mặc định", "Phạm vi áp dụng / Ghi chú kỹ thuật"],
            rows=[
                ["Số chiều embedding (`dim`)", "32", "Áp dụng đồng nhất cho LightGCN, GraphSAGE, GAT, BPR-MF, FedAvg/FedProx"],
                ["Số tầng lan truyền (`layers`)", "2", "Lan truyền đối xứng `D^-1/2 (A + I) D^-1/2` [1]; khảo sát 1–3 trong Sweep"],
                ["Bộ tối ưu & Learning rate", "Adam (`0,05` FL / `0,02` cent.)", "Khác biệt nhằm hội tụ ổn định trong 6 vòng FL; GAT dùng `gnn_epochs // 2 = 3`"],
                ["Điều chuẩn L2 (`reg_w`) & Batch", "`1e-5` / `8.192`", "Cục bộ giới hạn tối đa 4.096 cạnh/batch; lấy mẫu âm đều trong catalog"],
                ["Số vòng & Số silo tham gia", "`fl_rounds=6`, `fl_clients=50`", "Top 50 silo lớn nhất theo số cạnh train; `local_epochs=1`"],
                ["Số bước cục bộ/vòng (`n_steps`)", "`20` (1 ep) / `100` (5 ep)", "Công thức `max(20, min(100, 20 × local_epochs))` trong `notebooks/_p2.py`"],
                ["Mẫu đánh giá & Bootstrap", "`800` users, `1.000` lần lặp", "Hạt giống `seed=42`, khoảng tin cậy 95% (CI95)"],
            ],
            widths=[4.8, 4.1, 6.6],
            font_size=10.5,
        )

        self.table(
            caption="Phân tích độ phức tạp tính toán và chi phí truyền thông mỗi vòng FL",
            headers=["Giai đoạn", "Độ phức tạp thời gian", "Dung lượng bộ nhớ / Truyền thông", "Ghi chú thực nghiệm V3"],
            rows=[
                ["Lan truyền đồ thị cục bộ", "O(L · |E_c| · d)", "O((|V_c| + |E_c|) · d)", "Thưa hóa CSR; L=2, d=32, mỗi bước nhân thưa-đặc"],
                ["Tối ưu BPR cục bộ", "O(n_steps · |B_c| · d)", "O(|B_c| · d)", "|B_c| ≤ 4.096 cạnh/bước; `n_steps = 20` khi ep=1"],
                ["Truyền tải lên Server", "O(|V_c| · d)", "4 · |V_c| · d bytes (FP32)", "0 B raw data; chỉ gửi lat cắt `E_local` (hoặc nén FP16/Top-20%)"],
                ["Tổng hợp Sparse FedAvg", "O(∑_{c ∈ C_t} |V_c| · d)", "O(|V| · d) ≈ 33,92 MB", "Không pha loãng nút v ∉ ⋃ V_c; chỉ chia cho `den[v] > 0`"],
            ],
            widths=[3.7, 3.6, 4.1, 4.1],
            font_size=10.5,
        )

        self.h2("2.4. Lý thuyết bảo mật Gradient, Nén truyền thông và Phương pháp đánh giá")
        self.p(
            "Dù giao thức **GraphSafe** bảo đảm 0 byte dữ liệu thô `(user, job)` hoặc `user_history` "
            "rời khỏi silo doanh nghiệp, về mặt lý thuyết an toàn thông tin, việc truyền ma trận "
            "cập nhật ΔW_c = E_c^(t) − E_global^(t)[V_c] ở dạng rõ vẫn để ngỏ bề mặt tấn công suy "
            "ngược gradient (*Gradient Inversion / DLG*) [13, 19]: kẻ tấn công quan sát tập chỉ số "
            "nút V_c và độ lớn thay đổi của từng hàng embedding có thể suy đoán ứng viên nào vừa "
            "tương tác với tin tuyển dụng nào trong silo c. Để hoàn thiện phòng thủ chiều sâu cho "
            "triển khai thương mại, lý thuyết chuẩn kết hợp **DP-SGD** [11], **Secure Aggregation** "
            "[12] và nén truyền thông **Top-K sparsification** [14] theo cơ chế cắt ngưỡng–nhiễu–lọc:"
        )
        self.equation(
            "ΔW̃_c = Top_K( clip(ΔW_c, C) + N(0, σ² C² I) ),    K ∈ {100% (FP32), 20% (Top-20%)}",
            chapter=2,
        )
        self.p(
            "Trong phạm vi đồ án V3 hiện tại, cần khẳng định trung thực ranh giới triển khai: "
            "**GraphSafe** đã được thực thi nghiêm ngặt trong huấn luyện V3, các cơ chế nén "
            "(`FP32`, `FP16`, `Top-20%`) được mô hình hóa tương tác trên **UI Fault-Injection "
            "Workbench** (`NodeMonitorPage.tsx`), còn việc tích hợp thuật toán **DP-SGD** và mật mã "
            "**Secure Aggregation** trực tiếp vào vòng huấn luyện PyTorch được xác định là hạn chế "
            "hiện tại và mục tiêu nâng cấp số 2 trong Chương 6."
        )
        self.p(
            "Về phương pháp đánh giá xếp hạng ngoại tuyến, để loại trừ sai lệch lạc quan do cấu trúc "
            "cạnh phụ, đồ án kiểm toán toàn bộ tập kiểm thử `37.957` cạnh `user–job` và phát hiện "
            f"**{fi(sp['n_test_leak'])} cạnh** ({sp['pct_test_leak']:.3f}%) tồn tại đường đi 2 bước "
            "nhảy `user → occupation → job` ngay trong tập huấn luyện. Loại bỏ các cạnh đường vòng "
            f"này tạo thành tập **Clean Test** ({fi(sp['n_test_clean'])} cạnh; {fi(sp['n_users_lost_after_clean'])} "
            "người dùng mất toàn bộ cạnh test). Đồng thời, do 50 silo tham gia trong `FedAvg (50N)` "
            "chỉ sở hữu `9.058` tin trên tổng `82.876` tin có cạnh train (10,93%), đồ án tách bạch "
            "hai thước đo: **Global Catalog** (`82.876` tin) và **FL Catalog** (`9.058` tin cho 50N; "
            "`4.511` tin cố định cho 20N; `956` tin có nghề O*NET cho 20N-O*NET). Ba chỉ số xếp hạng "
            "tại ngưỡng K ∈ {10, 20} và độ phủ danh mục được định nghĩa chuẩn hóa như sau [26]:"
        )
        self.equation(
            "Recall@K = |R_u(K) ∩ T_u| / |T_u|,    NDCG@K = DCG_u@K / IDCG_u@K,    MRR@K = (1/|U_eval|) ∑_u (1 / rank_u)",
            chapter=2,
        )
        self.p(
            "Mọi thí nghiệm chính đều đánh giá trên cùng mẫu `800` người dùng (`seed=42`) kèm khoảng "
            "tin cậy 95% (*Bootstrap 95% CI*) tính qua `1.000` lần lấy mẫu lại có hoàn lại nhằm bảo "
            "đảm kết luận so sánh giữa các mô hình có ý nghĩa thống kê vững chắc."
        )

        # -------------------------------------------------------------
        # CHƯƠNG 3
        # -------------------------------------------------------------
        self.h1("CHƯƠNG 3. XÂY DỰNG DỮ LIỆU V3 VÀ THUẬT TOÁN TRÊN ĐỒ THỊ")

        self.h2("3.1. Phân tích dữ liệu thô CareerBuilder + O*NET 29.3 và xử lý bộ nhớ")
        self.p(
            "Pipeline tiền xử lý `src/prepare_v3.py` (1.583 dòng mã Python) hợp nhất hai kho dữ liệu "
            "gốc: **CareerBuilder** [31] (`jobs.tsv` với {0} dòng tin tuyển dụng sạch cấu trúc, "
            "`apps.tsv` với {1} lượt ứng tuyển, `users.tsv` với {2} hồ sơ ứng viên, và "
            "`user_history.tsv` với {3} bản ghi kinh nghiệm nghề nghiệp) cùng bộ chuẩn nghề nghiệp "
            "và kỹ năng **O*NET phiên bản 29.3** [32] ({4} nghề nghiệp trong `Occupation Data.txt` "
            "và {5} kỹ năng công nghệ phân biệt trong `Technology Skills.txt`).".format(
                fi(m["raw"]["jobs_rows"]),
                fi(m["raw"]["apps_rows"]),
                fi(m["raw"]["users_rows"]),
                fi(m["raw"]["user_history_rows"]),
                fi(m["occupations"]["n_occupations_onet_total"]),
                fi(m["skills"]["n_skills_onet_total"]),
            )
        )
        self.p(
            "Quá trình kiểm toán kỹ thuật trước khi dựng đồ thị phát hiện năm vấn đề dữ liệu thực "
            "tế quan trọng (`notebooks/_p1.py:455-461`, `src/prepare_v3.py:494`): (1) **92%** mô tả "
            "công việc chứa thẻ HTML hoặc ký tự điều khiển `\\r\\n\\t` cần làm sạch bằng `detag()`; "
            "(2) **14,2%** cặp `(user_id, job_id)` xuất hiện trùng lặp trong log thô; (3) **1,9%** "
            "chuỗi chứa lỗi mã hóa *mojibake*; (4) **37%** trường mã bưu chính `Zip5` bị nhiễu hoặc "
            "sai định dạng nên bị loại bỏ, giữ lại hai trường sạch `city` và `state`; và (5) tệp "
            "`Skills.txt` (35 kỹ năng mềm/cơ bản tổng quát của O*NET) gán đầy đủ cả 35/35 phần tử "
            "cho 879/879 nghề khảo sát, dẫn đến **entropy thông tin bằng 0** và làm đồ thị bị bão "
            "hòa hoàn toàn nếu đưa vào. Vì vậy, V3 loại bỏ dứt khoát `Skills.txt` để chỉ giữ "
            "`Technology Skills.txt` giàu tính phân biệt. Để vận hành mượt mà trên máy trạm giới hạn "
            "3,9 GB RAM, toàn bộ các tệp TSV hàng triệu dòng được đọc tuần tự kiểu *streaming* qua "
            "`csv.reader` kết hợp mảng NumPy đóng gói, đạt đỉnh bộ nhớ chỉ **{0:.1f} MB** trong "
            "**{1:.1f} giây**.".format(m["memory_peak_mb"], m["runtime_seconds"])
        )

        self.h2("3.2. Bộ trích xuất 9 nguồn nhà tuyển dụng và phễu lọc 5 bước")
        self.p(
            "Thách thức kỹ thuật lớn nhất của CareerBuilder là không tồn tại cột định danh "
            "`EmployerID` hay `CompanyName` tường minh. Để phân tách đúng **Cross-Silo** theo từng "
            "doanh nghiệp, hàm `employer_from_text(desc, req)` (`src/prepare_v3.py:378-440`) thiết "
            "kế chuỗi 9 bộ trích xuất theo thứ tự ưu tiên độ tin cậy giảm dần trên 700 ký tự đầu "
            "và câu đầu tiên của mô tả công việc (`detag(desc)`), kết hợp đối chiếu danh sách đen "
            "nghiêm ngặt gồm `HEADHUNT_DOMAINS` (các hãng môi giới nhân sự lớn như `randstadusa.com`, "
            "`roberthalf.com`, `adecco.com`, `aerotek.com` hay cổng ATS như `taleo.net`, `workday.com`), "
            "`FREE_MAIL` (`gmail.com`, `yahoo.com`, ...), `HARD_NOISE` (`\"our client\"`, "
            "`\"confidential\"`, `\"equal opportunity\"`), `STOP_TOKENS` và `ROLE_WORDS` nhằm ngăn "
            "chức danh nghề nghiệp bị nhận nhầm thành tên công ty."
        )

        self.figure(
            "fig1_architecture.png",
            "Kiến trúc tổng thể hệ thống FedGraph Cross-Silo LightGCN và Full-Stack Serving",
            width_cm=15.3,
        )
        self.figure(
            "fig2_preprocessing_funnel.png",
            "Quy trình lọc 5 bước từ dữ liệu thô CareerBuilder đến 9.116 FL silos và phân bố 9 nguồn trích xuất nhà tuyển dụng",
            width_cm=15.3,
        )

        src_rows = [
            ["Ưu tiên 1a", "`S1_legal_dau_cau`", "Hậu tố pháp lý (Inc, LLC, Corp...) ngay đầu câu đầu tiên", fi(src_counts["S1_legal_dau_cau"])],
            ["Ưu tiên 1b", "`S1_legal_dau_mo_ta`", "Hậu tố pháp lý trong 700 ký tự đầu mô tả công việc", fi(src_counts["S1_legal_dau_mo_ta"])],
            ["Ưu tiên 2", "`S2_is_a`", "Mẫu ngữ pháp \"<Tên> is a/an/the/leading/growing...\"", fi(src_counts["S2_is_a"])],
            ["Ưu tiên 3", "`S3_seeks`", "Mẫu tuyển dụng \"<Tên> seeks / is seeking / is hiring...\"", fi(src_counts["S3_seeks"])],
            ["Ưu tiên 4", "`S6_viet_hoa`", "Cụm tên viết hoa toàn bộ đầu dòng (ALL CAPS)", fi(src_counts["S6_viet_hoa"])],
            ["Ưu tiên 5", "`S7_hau_to_cuoi`", "Hậu tố pháp lý neo cuối cụm trong câu mở đầu", fi(src_counts["S7_hau_to_cuoi"])],
            ["Ưu tiên 6", "`S4_about_us`", "Tiêu đề khối \"About us / Company overview: <Tên>\"", fi(src_counts["S4_about_us"])],
            ["Ưu tiên 7", "`S5_domain_email`", "Tên miền email doanh nghiệp (đã lọc FREE_MAIL & HEADHUNT)", fi(src_counts["S5_domain_email"])],
            ["Ưu tiên 8", "`S8_domain_website`", "Tên miền website công ty (`https://...` / `www...`)", fi(src_counts["S8_domain_website"])],
        ]
        self.table(
            caption="Thống kê 9 nguồn trích xuất nhà tuyển dụng trên CareerBuilder V3",
            headers=["Thứ tự", "Mã nguồn trích xuất", "Quy tắc ngữ pháp / Miền nhận diện", "Số tin trích xuất"],
            rows=src_rows,
            widths=[2.0, 3.6, 7.1, 2.8],
            font_size=10.5,
            pad_tb=42,
        )

        funnel_rows = []
        for st in emp["filter_steps"]:
            funnel_rows.append([
                st["step"],
                fi(st["n_employers"]) if st["n_employers"] is not None else "—",
                fi(st["n_jobs_with_employer"]) if st["n_jobs_with_employer"] is not None else "—",
                fi(st["n_apps"]) if st["n_apps"] is not None else "—",
                f"{st['pct_apps_remaining']:.2f}%" if st["pct_apps_remaining"] is not None else "—",
            ])
        self.table(
            caption="Thống kê phễu lọc 5 bước từ dữ liệu CareerBuilder gốc đến 9.116 FL silos (V3)",
            headers=[
                "Bước lọc dữ liệu",
                "Số nhà tuyển dụng",
                "Số tin có nhãn",
                "Số lượt ứng tuyển",
                "Tỷ lệ giữ lại",
            ],
            rows=funnel_rows,
            widths=[6.0, 2.5, 2.5, 2.5, 2.0],
            font_size=11.0,
        )

        self.h2("3.3. Ánh xạ O*NET soc[:7], bất đối xứng 5,1x và kiểm soát rò rỉ 2-hop")
        self.p(
            "Một phát hiện kỹ thuật quan trọng trong quá trình xây dựng V3 là việc chuẩn hóa mã "
            "O*NET-SOC về đúng **6 ký tự gốc (`soc[:7]` có dấu gạch ngang, ví dụ `11-1011`)** "
            "trên toàn bộ cả bốn loại thực thể. Ở phiên bản thử nghiệm trước đó, sự không nhất "
            "quán giữa mã 8 ký tự mở rộng (`11-1011.00`, `11-1011.03`) và mã 6 ký tự gây ra lỗi "
            "phồng cạnh lên tới 67,4%. Sau khi đồng nhất `soc[:7]` và khớp tiêu đề kép (`norm_title` "
            "chính xác kết hợp `loose_title` với `Occupation Data.txt` và `Alternate Titles.txt`), "
            f"đồ thị cuối cùng chứa **{fi(g['n_occ'])} nút nghề nghiệp** (`564` nghề có cạnh kỹ "
            f"năng công nghệ và `19` nghề chưa có kỹ năng trong `Technology Skills.txt`) nối tới "
            f"**{fi(g['n_skill'])} kỹ năng** qua **{fi(g['edges_by_type']['2'])} cạnh** (trung "
            f"bình {m['skills']['mean_skills_per_occupation']:.2f} kỹ năng/nghề)."
        )
        self.p(
            f"Trong tổng số {fi(g['n_jobs'])} tin tuyển dụng thuộc 9.116 silos, "
            f"**{fi(m['edges']['n_jobs_with_occupation_edge'])} tin ({eda['pct_jobs_with_occ']:.2f}%)** "
            f"ánh xạ được vào O*NET, còn {fi(m['edges']['n_jobs_without_occupation_edge'])} tin "
            "(68,56%) tuy thiếu cạnh `job–occupation` nhưng vẫn được giữ nguyên trong đồ thị nhằm "
            "phản ánh trung thực phân bố dữ liệu thô. Ở phía ứng viên, ánh xạ `user_history.tsv` "
            f"khớp được {m['skills']['pct_user_history_titles_mapped']:.2f}% tiêu đề (336.267 bản "
            f"ghi), hình thành {fi(g['edges_by_type']['3'])} cạnh duy nhất `user–occupation` phủ "
            "tới `136.264` ứng viên trong tập train. Như vậy xuất hiện **bất đối xứng 5,1 lần** giữa "
            "số ứng viên có cạnh nghề nghiệp (`136.264`) và số tin có cạnh nghề nghiệp (`26.678`), "
            "đây là nguyên nhân lý giải vì sao nâng độ phủ O*NET cho tin tuyển dụng mang lại bước "
            "nhảy hiệu năng lớn trong Chương 4."
        )
        self.p(
            "Về phân chia tập huấn luyện/kiểm thử, V3 giữ tỷ lệ 20% cạnh `user–job` làm tập test "
            "chỉ đối với các ứng viên có từ 5 lượt nộp đơn trở lên, tạo thành "
            f"**{fi(g['n_train_uj'])}** cạnh train và **{fi(g['n_test_uj'])}** cạnh test gốc "
            "(chiếm 8,688% tổng cạnh `user–job`, hoặc 19,095% trên nhóm đủ điều kiện). Để ngăn "
            "tình trạng mô hình \"nhìn trộm\" nhãn qua cầu nối công khai, tập test được rà soát "
            f"và loại bỏ **{fi(sp['n_test_leak'])} cạnh (2,318%)** có đường đi 2-hop `user → "
            f"occupation → job` đã tồn tại trong đồ thị train, cho ra tập **Clean Test gồm "
            f"{fi(sp['n_test_clean'])} cạnh**. Hình 1 minh họa ranh giới tách biệt giữa "
            "52.544 cạnh công khai và 711.820 cạnh riêng tư, còn Bảng 6 tổng hợp toàn bộ thống kê đồ thị."
        )

        graph_rows = [
            ["Đỉnh ứng viên (`user`)", fi(g["n_users"]), "Riêng tư theo tương tác cục bộ", "64,83% tổng số đỉnh; 44,58% ứng tuyển đa silo"],
            ["Đỉnh tin tuyển dụng (`job`)", fi(g["n_jobs"]), "Thuộc quyền sở hữu `client_of_job`", f"{fi(sp['n_jobs_cold_start'])} cold-start jobs (2,32%)"],
            ["Đỉnh nghề nghiệp (`occupation`)", fi(g["n_occ"]), "Công khai (Public Graph Backbone)", f"{m['occupations']['n_occupations_with_skill']} nghề có kỹ năng; chuẩn `soc[:7]`"],
            ["Đỉnh kỹ năng (`skill`)", fi(g["n_skill"]), "Công khai (Public Graph Backbone)", f"TB {m['skills']['mean_skills_per_occupation']:.2f} kỹ năng/nghề (loại `Skills.txt`)"],
            ["Cạnh `user–job` (type 0)", fi(g["edges_by_type"]["0"]), "Riêng tư (Private)", f"Train: {fi(g['n_train_uj'])} | Test: {fi(g['n_test_uj'])} (Clean: {fi(sp['n_test_clean'])})"],
            ["Cạnh `job–occupation` (type 1)", fi(g["edges_by_type"]["1"]), "Công khai (Public)", f"Độ phủ {eda['pct_jobs_with_occ']:.2f}% số tin tuyển dụng"],
            ["Cạnh `occupation–skill` (type 2)", fi(g["edges_by_type"]["2"]), "Công khai (Public)", "Nối gián tiếp 2-hop kỹ năng ứng viên & tin"],
            ["Cạnh `user–occupation` (type 3)", fi(g["edges_by_type"]["3"]), "Riêng tư (Private)", f"Trích `user_history` ({m['skills']['pct_user_history_titles_mapped']:.2f}% khớp, bất đối xứng 5,1x)"],
        ]
        self.table(
            caption="Thống kê chi tiết các loại đỉnh và cạnh của đồ thị không đồng nhất FedGraph V3",
            headers=["Thành phần đồ thị", "Số lượng", "Phân loại bảo mật", "Ghi chú phân bổ & độ phủ"],
            rows=graph_rows,
            widths=[4.4, 2.3, 3.8, 5.0],
            font_size=10.5,
        )

        self.h2("3.4. Đặc tả thuật toán FedGraph và đối chiếu tiền thân MEDAJob")
        self.p(
            "Thuật toán 1 và Thuật toán 2 dưới đây đặc tả chi tiết luồng xử lý đầu-cuối của "
            "FedGraph từ khâu chuẩn hóa dữ liệu thô, dựng đồ thị con tại từng silo đến bước tổng "
            "hợp thưa trên máy chủ điều phối."
        )

        self.algorithm_box(
            "Tiền xử lý Streaming & Phân chia Cross-Silo CareerBuilder + O*NET (V3)",
            [
                "Input : jobs.tsv, apps.tsv, users.tsv, user_history.tsv, O*NET 29.3 (db_29_3_text.zip)",
                "Output: graph.npz (264.995 nút, 764.364 cạnh), clients.json (9.116 silos), train/test masks",
                "1: Stream jobs.tsv qua csv.reader -> detag() -> trich employer_from_text() (9 nguồn + blacklists)",
                "2: Ánh xạ job_title -> mã O*NET soc[:7] qua Occupation Data + Alternate Titles (31,44% phủ)",
                "3: Đọc apps.tsv -> khử trùng lặp (14,2%) -> lọc employer >= 2 jobs và >= 10 apps -> 9.116 silos",
                "4: Gán client_of_job[j] = employer(j); tách cạnh user-job mỗi user (>=5 apps) theo tỷ lệ 80/20",
                "5: Đọc Technology Skills.txt (bỏ Skills.txt entropy=0) -> nối (job-occ) & (occ-skill) thành Public Backbone",
                "6: Kiểm tra rò rỉ đường vòng 2-hop (user -> occ -> job trong train) -> tách 880 cạnh -> Clean Test 37.077",
            ],
        )

        self.algorithm_box(
            "Huấn luyện Cross-Silo LightGCN với Sparse Touched-Node FedAvg / FedProx",
            [
                "Input : Đồ thị toàn cục G, ma trận khởi tạo E_global^(0) in R^(|V| x 32), T=6 vòng, K=50 silos",
                "Output: Ma trận embedding toàn cục E_global^(T) cho suy luận LightGCN",
                "1: for round t = 0, ..., T - 1 do",
                "2:   Chọn tập K silo tham gia C_t; khởi tạo bộ tích lũy num = 0, den = 0 kích thước (|V| x d)",
                "3:   for mỗi silo c in C_t (song song theo doanh nghiệp) do",
                "4:     Dựng đồ thị con G_c = (V_c, E_c) gồm job của c, user đã nộp đơn, và Public Backbone",
                "5:     Nhận E_c <- E_global^(t)[V_c]; chuẩn hóa kề đối xứng P_c = D_c^(-1/2)(A_c + I)D_c^(-1/2)",
                "6:     for step = 1, ..., n_steps = max(20, min(100, 20 * local_epochs)) do",
                "7:       Lan truyền L=2 tầng: E_bar = (1/3)(E_c + P_c*E_c + P_c^2*E_c)",
                "8:       Tính BPR loss trên batch cạnh user-job (+ mu/2 * ||E_c - E_global^(t)[V_c]||^2 nếu FedProx)",
                "9:       Cập nhật E_c bằng Adam(lr=0.05) trên toàn bộ tham số cục bộ",
                "10:    Gửi (V_c, E_c, w_c = |E_c^{u-j}|) về Server (0 B dữ liệu ứng tuyển thô rời silo)",
                "11:  Tích lũy thưa: num[V_c] += w_c * E_c; den[V_c] += w_c",
                "12:  Với mọi v có den[v] > 0: E_global^(t+1)[v] <- num[v] / den[v] (nút không chạm giữ nguyên)",
            ],
        )

        m_sys = meda["systems"]
        self.p(
            "Trước khi triển khai trên bộ CareerBuilder + O*NET V3, nhóm đã tiến hành kiểm chứng "
            "nguyên lý trên tập dữ liệu thí điểm quy mô nhỏ **MEDAJob** (`config.yaml`, "
            "`results/reco_main.json`) gồm 70 người dùng, 1.014 tin tuyển dụng và 307 tương tác "
            "(16 người dùng kiểm thử). Bảng 7 đối chiếu sự nhảy vọt về quy mô và hiệu quả băng "
            "thông khi chuyển từ thí điểm MEDAJob lên hệ thống chính V3: trên MEDAJob, dù `FedAvg` "
            f"đạt `Recall@20 = {m_sys['fedavg']['recall@20']:.4f}` (tiệm cận `Centralized LightGCN = "
            f"{m_sys['centralized']['recall@20']:.4f}` và vượt rõ `Local-only = {m_sys['local_only']['recall@20']:.4f}`), "
            "chi phí truyền 54.304 tham số (`217.216` bytes/lượt) qua 20 vòng dẫn tới tỷ lệ băng "
            "thông gấp **6.565 lần** dữ liệu tương tác thô (điểm hòa vốn lý thuyết 1.634.792 tương "
            "tác). Việc mở rộng lên quy mô CareerBuilder V3 cùng cơ chế cập nhật thưa chỉ các nút "
            "chạm tới (`Sparse Touched-Node`) mới khai thác trọn vẹn ưu thế của Học liên kết."
        )

        self.table(
            caption="Đối chiếu quy mô và kết quả giữa tập thí điểm MEDAJob và hệ thống chính V3",
            headers=["Tiêu chí so sánh", "Thí điểm MEDAJob (reco_main.json)", "Hệ thống chính V3 (CareerBuilder + O*NET)"],
            rows=[
                ["Số ứng viên / Số tin tuyển dụng", "70 users / 1.014 jobs", f"{fi(g['n_users'])} users / {fi(g['n_jobs'])} jobs"],
                ["Tổng số cạnh / Số silos FL", "307 tương tác / chia cụm nhỏ", f"{fi(g['n_edges'])} cạnh / {fi(cs['n_clients'])} employer silos"],
                ["Tri thức nghề nghiệp công khai", "Từ khóa kỹ năng cục bộ", f"{fi(g['n_occ'])} O*NET occupations + {fi(g['n_skill'])} tech skills"],
                ["Recall@20 (`Local-only` vs `FedAvg`)", f"{m_sys['local_only']['recall@20']:.4f} vs {m_sys['fedavg']['recall@20']:.4f}", f"{lo['results']['local_only_strict_silo']['recall@20']:.4f} vs {ablation[0]['R20']} (20N) / {ablation[12]['R20']} (O*NET)"],
                ["Cơ chế đồng bộ tham số", "Toàn bộ ma trận embedding (54.304 params)", "Sparse Touched-Node (chỉ đồng bộ tập nút V_c)"],
            ],
            widths=[4.3, 5.2, 6.0],
            font_size=10.5,
        )

        # -------------------------------------------------------------
        # CHƯƠNG 4
        # -------------------------------------------------------------
        self.h1("CHƯƠNG 4. THỰC NGHIỆM, KẾT QUẢ VÀ PHÂN TÍCH LỖI CHUYÊN SÂU")

        self.h2("4.1. Thiết lập thực nghiệm đa nền tảng (CUDA vs CPU) và đối chứng Local-only V3")
        self.p(
            "Toàn bộ thực nghiệm huấn luyện và đánh giá V3 được thực thi độc lập trên hai môi "
            "trường phần cứng khác nhau để kiểm chứng tính tái lập: (1) **Kaggle CUDA** "
            f"(`results_v3/notebook_metrics.json`, Python {cuda['environment']['python']}, PyTorch "
            f"{cuda['environment']['torch']}, tổng thời gian `943,1 giây`), và (2) **Local CPU** "
            f"(`results/v3/notebook_metrics.json`, Python {cpu['environment']['python']}, PyTorch "
            f"{cpu['environment']['torch']}, tổng thời gian `1.394,8 giây`). Kết quả chất lượng "
            "của mọi mô hình neural và Học liên kết, bảng Ablation 15 biến thể và Sweep 8 cấu hình "
            "trùng khớp tuyệt đối đến 4 chữ số thập phân giữa hai môi trường; chỉ hai thuật toán "
            "phi tham số là `Popularity` và `Item-KNN` sai khác vi mô ở thứ tự phá đồng hạng trên "
            "FL Catalog (`0,0529` so với `0,0542`; `0,4909` so với `0,4897`), bên cạnh tốc độ thực "
            "thi nhanh hơn đáng kể trên GPU."
        )
        self.p(
            "Đặc biệt, để lấp đầy khoảng trống đối chứng trên tập V3, nhóm xây dựng bổ sung tập "
            "lệnh tái lập `scripts/eval_local_only_v3.py` (`results_v3/local_only_v3.json`, chạy "
            "`124,47 giây` trên CPU, cùng `seed=42` và `800` người dùng đánh giá trên lát cắt cố "
            "định `20N` = `4.511` tin) nhằm đo lường hai cận đối chứng cực kỳ quan trọng: "
            "**`Local-only Strict Silo`** (mỗi doanh nghiệp tự huấn luyện LightGCN trên đồ thị riêng "
            "và chỉ suy luận cho người dùng từng nộp đơn ở silo đó—phản ánh đúng cô lập thực tế) "
            "và **`Local-only Stitched Upper Bound`** (giả lập trường hợp các ma trận cục bộ được "
            "ghép hậu kỳ và lan truyền trên toàn bộ đồ thị—một cận trên lý thuyết không thể đạt được "
            "nếu giữ nguyên nguyên tắc không tập trung dữ liệu)."
        )

        self.h2("4.2. So sánh hiệu năng 7 mô hình và giá trị của Học liên kết")
        lo_s = lo["results"]["local_only_strict_silo"]
        lo_u = lo["results"]["local_only_stitched_upper_bound"]
        ab_onet = ablation[12]
        ab_base = ablation[0]

        def _ci_str(ci: list[float]) -> str:
            return f"[{ci[0]:.4f}, {ci[1]:.4f}]"

        model_rows = [
            [
                "Item-KNN [5]", "Global (82.876)", f4(models["Item-KNN"]["recall@10"]),
                f4(models["Item-KNN"]["recall@20"]), _ci_str(models["Item-KNN"]["recall@20_ci95"]),
                f4(models["Item-KNN"]["ndcg@20"]), f4(models["Item-KNN"]["mrr@20"]),
                f"{models['Item-KNN']['seconds']:.2f} / {cpu_models['Item-KNN']['seconds']:.2f}",
            ],
            [
                "LightGCN Cent. [1]", "Global (82.876)", f4(models["LightGCN"]["recall@10"]),
                f4(models["LightGCN"]["recall@20"]), _ci_str(models["LightGCN"]["recall@20_ci95"]),
                f4(models["LightGCN"]["ndcg@20"]), f4(models["LightGCN"]["mrr@20"]),
                f"{models['LightGCN']['seconds']:.2f} / {cpu_models['LightGCN']['seconds']:.2f}",
            ],
            [
                "GAT Cent.", "Global (82.876)", f4(models["GAT"]["recall@10"]),
                f4(models["GAT"]["recall@20"]), _ci_str(models["GAT"]["recall@20_ci95"]),
                f4(models["GAT"]["ndcg@20"]), f4(models["GAT"]["mrr@20"]),
                f"{models['GAT']['seconds']:.2f} / {cpu_models['GAT']['seconds']:.2f}",
            ],
            [
                "GraphSAGE Cent. [4]", "Global (82.876)", f4(models["GraphSAGE"]["recall@10"]),
                f4(models["GraphSAGE"]["recall@20"]), _ci_str(models["GraphSAGE"]["recall@20_ci95"]),
                f4(models["GraphSAGE"]["ndcg@20"]), f4(models["GraphSAGE"]["mrr@20"]),
                f"{models['GraphSAGE']['seconds']:.2f} / {cpu_models['GraphSAGE']['seconds']:.2f}",
            ],
            [
                "FedAvg (50N) [6]", "Global (82.876)", f4(models["FedAvg"]["recall@10"]),
                f4(models["FedAvg"]["recall@20"]), _ci_str(models["FedAvg"]["recall@20_ci95"]),
                f4(models["FedAvg"]["ndcg@20"]), f4(models["FedAvg"]["mrr@20"]),
                f"{models['FedAvg']['seconds']:.2f} / {cpu_models['FedAvg']['seconds']:.2f}",
            ],
            [
                "BPR-MF [3]", "Global (82.876)", f4(models["BPR-MF"]["recall@10"]),
                f4(models["BPR-MF"]["recall@20"]), _ci_str(models["BPR-MF"]["recall@20_ci95"]),
                f4(models["BPR-MF"]["ndcg@20"]), f4(models["BPR-MF"]["mrr@20"]),
                f"{models['BPR-MF']['seconds']:.2f} / {cpu_models['BPR-MF']['seconds']:.2f}",
            ],
            [
                "Popularity", "Global (82.876)", f4(models["Popularity"]["recall@10"]),
                f4(models["Popularity"]["recall@20"]), _ci_str(models["Popularity"]["recall@20_ci95"]),
                f4(models["Popularity"]["ndcg@20"]), f4(models["Popularity"]["mrr@20"]),
                f"{models['Popularity']['seconds']:.2f} / {cpu_models['Popularity']['seconds']:.2f}",
            ],
            [
                "LightGCN Cent. [1]", "FL (50N: 9.058)", "—",
                f4(models["LightGCN"]["R20_FlUniverse"]), "—", "—", "—",
                f"{models['LightGCN']['seconds']:.2f} / {cpu_models['LightGCN']['seconds']:.2f}",
            ],
            [
                "GraphSAGE Cent. [4]", "FL (50N: 9.058)", "—",
                f4(models["GraphSAGE"]["R20_FlUniverse"]), "—", "—", "—",
                f"{models['GraphSAGE']['seconds']:.2f} / {cpu_models['GraphSAGE']['seconds']:.2f}",
            ],
            [
                "Item-KNN [5]", "FL (50N: 9.058)", "—",
                f"{models['Item-KNN']['R20_FlUniverse']:.4f} (CPU: {cpu_models['Item-KNN']['R20_FlUniverse']:.4f})",
                "—", "—", "—",
                f"{models['Item-KNN']['seconds']:.2f} / {cpu_models['Item-KNN']['seconds']:.2f}",
            ],
            [
                "FedAvg (50N)", "FL (50N: 9.058)", "—",
                f4(models["FedAvg"]["R20_FlUniverse"]), _ci_str(models["FedAvg"]["R20_FlUniverse_ci95"]),
                f4(models["FedAvg"]["NDCG20_FlUniverse"]), f4(models["FedAvg"]["MRR20_FlUniverse"]),
                f"{models['FedAvg']['seconds']:.2f} / {cpu_models['FedAvg']['seconds']:.2f}",
            ],
            [
                "GAT Cent.", "FL (50N: 9.058)", "—",
                f4(models["GAT"]["R20_FlUniverse"]), "—", "—", "—",
                f"{models['GAT']['seconds']:.2f} / {cpu_models['GAT']['seconds']:.2f}",
            ],
            [
                "BPR-MF [3]", "FL (50N: 9.058)", "—",
                f4(models["BPR-MF"]["R20_FlUniverse"]),
                "—", "—", "—",
                f"{models['BPR-MF']['seconds']:.2f} / {cpu_models['BPR-MF']['seconds']:.2f}",
            ],
            [
                "Popularity", "FL (50N: 9.058)", "—",
                f"{models['Popularity']['R20_FlUniverse']:.4f} (CPU: {cpu_models['Popularity']['R20_FlUniverse']:.4f})",
                "—", "—", "—",
                f"{models['Popularity']['seconds']:.2f} / {cpu_models['Popularity']['seconds']:.2f}",
            ],
            [
                "**FedAvg (20N O*NET)**", "FL (956 jobs)", f4(ab_onet["R10"]),
                f4(ab_onet["R20"]), "—", f4(ab_onet["NDCG20"]), f4(ab_onet["MRR20"]),
                f"{float(ab_onet['giây']):.1f} / {cpu['ablation'][12]['giây']:.1f}",
            ],
            [
                "**FedAvg (20N Fixed)**", "FL (4.511 jobs)", f4(ab_base["R10"]),
                f4(ab_base["R20"]), _ci_str(lo["results"]["fedavg_20n_repro"]["recall@20_ci95"]),
                f4(ab_base["NDCG20"]), f4(ab_base["MRR20"]),
                f"{float(ab_base['giây']):.1f} / {cpu['ablation'][0]['giây']:.1f}",
            ],
            [
                "Local-only (Stitched UB)", "FL (4.511 jobs)", f4(lo_u["recall@10"]),
                f4(lo_u["recall@20"]), _ci_str(lo_u["recall@20_ci95"]),
                f4(lo_u["ndcg@20"]), f4(lo_u["mrr@20"]),
                f"— / {lo_u['train_seconds']:.2f}",
            ],
            [
                "**Local-only (Strict Silo)**", "FL (4.511 jobs)", f4(lo_s["recall@10"]),
                f4(lo_s["recall@20"]), _ci_str(lo_s["recall@20_ci95"]),
                f4(lo_s["ndcg@20"]), f4(lo_s["mrr@20"]),
                f"— / {lo_s['train_seconds']:.2f}",
            ],
        ]

        self.table(
            caption="Tổng hợp hiệu năng các mô hình trên Global Catalog và FL Catalog (800 eval users, seed=42)",
            headers=[
                "Mô hình",
                "Phạm vi",
                "R@10",
                "R@20",
                "95% CI (R@20)",
                "NDCG@20",
                "MRR@20",
                "Thời gian (CUDA/CPU, s)",
            ],
            rows=model_rows,
            widths=[2.7, 2.0, 1.25, 1.55, 2.5, 1.45, 1.45, 2.6],
            font_size=9.5,
        )

        self.figure(
            "fig3_model_comparison.png",
            "So sánh hiệu năng xếp hạng giữa các mô hình trên FL Catalog và Global Catalog (kèm 95% CI)",
            width_cm=15.3,
        )

        self.p("Từ Bảng 8 và Hình 3, bốn kết luận thực nghiệm cốt lõi được xác lập:")
        self.bullet(
            "**1. Học liên kết vượt trội tuyệt đối so với mô hình cô lập Local-only:** Trên cùng "
            f"tập đánh giá cố định 20N (`4.511` tin tuyển dụng), **FedAvg (20N)** đạt "
            f"`Recall@20 = {f4(ab_base['R20'])}` (CI95 {_ci_str(lo['results']['fedavg_20n_repro']['recall@20_ci95'])}, "
            f"`NDCG@20 = {f4(ab_base['NDCG20'])}`, `MRR@20 = {f4(ab_base['MRR20'])}`), bỏ xa "
            f"**Local-only Strict Silo** (`Recall@20 = {f4(lo_s['recall@20'])}`, CI95 "
            f"{_ci_str(lo_s['recall@20_ci95'])}) tới **+23,73 điểm phần trăm** (tăng **+96,5%** "
            "tương đối; hai khoảng tin cậy 95% hoàn toàn rời nhau). Đáng chú ý, ngay cả khi so với "
            "cận trên phi thực tế `Local-only Stitched Upper Bound` (`0,3939`), `FedAvg` vẫn cao hơn "
            "**+8,94 điểm phần trăm** vì quá trình đồng bộ lặp nhiều vòng tạo ra không gian nhúng "
            "liên thông giữa các doanh nghiệp."
        )
        self.bullet(
            "**2. Ưu thế của LightGCN so với GraphSAGE/GAT và vai trò chất xúc tác O*NET:** "
            "Trong nhóm tập trung trên `FL Catalog (50N)`, **Centralized LightGCN** đạt cận trên "
            f"`{f4(models['LightGCN']['R20_FlUniverse'])}`, vượt xa `GraphSAGE` "
            f"({f4(models['GraphSAGE']['R20_FlUniverse'])}) và `GAT` ({f4(models['GAT']['R20_FlUniverse'])}). "
            "Nguyên nhân là các lớp biến đổi trọng số W và cơ chế chú ý trong GraphSAGE/GAT dễ "
            "quá khớp trên đồ thị thưa, còn việc giữ nguyên lan truyền tuyến tính LightGCN bảo "
            "toàn chính xác cấu trúc bậc cao [1]. Khi giới hạn trên phân khúc tin có ánh xạ nghề "
            f"O*NET (`956` tin), **FedAvg (20N O*NET)** vươn tới `Recall@20 = {f4(ab_onet['R20'])}`, "
            f"gấp **10,6–10,9 lần** baseline `Popularity` (`0,0529` CUDA / `0,0542` CPU)."
        )
        self.bullet(
            "**3. Độ vững trước Clean Test (loại 880 cạnh đường vòng):** Khi kiểm thử lại sau khi "
            "gỡ bỏ 880 cạnh có đường đi 2-hop `user → occ → job` trong tập train, cả `Item-KNN` "
            "(`0,5408 → 0,5449`) lẫn `LightGCN` (`0,4002 → 0,4017`) đều duy trì hoặc tăng nhẹ hiệu "
            "năng, trong khi `Popularity` sụt giảm 67% (`0,0154 → 0,0051`). Kết quả chứng minh "
            "LightGCN không gian lận bằng đường tắt nghề nghiệp mà học được tín hiệu lọc cộng tác thực thụ."
        )
        self.bullet(
            "**4. Global Catalog Gap:** Trên toàn thị trường `82.876` tin, `Item-KNN` dẫn đầu ở "
            "`0,5408`, theo sau bởi `LightGCN` (`0,4002`), còn `FedAvg (50N)` mới đạt `0,0475`—hiện "
            "tượng này được phân tích cơ chế chi tiết tại Mục 4.6."
        )

        self.h2("4.3. Nghiên cứu cắt giảm (Ablation Study 15 biến thể)")
        ab_rows = []
        for idx, row in enumerate(ablation):
            cpu_sec = cpu["ablation"][idx]["giây"]
            ab_rows.append([
                row["biến_thể"],
                row["ghi_chú"],
                f4(row["R10"]),
                f4(row["R20"]),
                f4(row["NDCG20"]),
                f4(row["MRR20"]),
                row["n_shard"],
                fi(int(row["n_catalog"])),
                f"{float(row['giây']):.1f} / {cpu_sec:.1f}",
            ])
        self.table(
            caption="Kết quả Ablation Study 15 biến thể trên tập FL Catalog cố định (4 vòng liên kết)",
            headers=[
                "Biến thể",
                "Mô tả thiết lập",
                "R@10",
                "R@20",
                "NDCG\n@20",
                "MRR\n@20",
                "Silos",
                "Catalog",
                "Giây (CUDA/CPU)",
            ],
            rows=ab_rows,
            widths=[2.55, 2.65, 1.35, 1.35, 1.45, 1.45, 1.05, 1.35, 2.30],
            font_size=9.5,
            pad_tb=40,
            pad_lr=35,
        )

        self.figure(
            "fig4_ablation_and_drift.png",
            "Phân tích Ablation: đóng góp của Public Graph Backbone, mở rộng số client và hiệu ứng Client Drift",
            width_cm=15.3,
        )

        self.p("Bảng 9 và Hình 4 khẳng định bốn quy luật thiết kế mang tính quyết định:")
        self.bullet(
            "**Đóng góp +9,00 điểm phần trăm của Public Graph Backbone (`Occ + Skill`):** Trên lát "
            "cắt cố định `4.511` tin, bỏ lớp kỹ năng `(a)` làm `Recall@20` giảm `0,4833 → 0,4589` "
            "(-2,44 điểm) và bỏ cả lớp nghề nghiệp `(b)` làm `Recall@20` rơi xuống `0,3933` "
            "(**-9,00 điểm**, NDCG@20 từ `0,3469 → 0,2657`). Khi đánh giá thuần trên `956` tin có "
            "mã O*NET `(f1 → f2 → f3)`, xu hướng lặp lại y hệt (`0,5756 → 0,5270 → 0,5066`, -6,90 điểm). "
            "Điều này chứng tỏ xương sống O*NET thực sự thay thế được một phần các cạnh liên silo bị "
            "cô lập mà không cần mô hình sinh lân cận đắt đỏ như FedSage+ [21, 29, 32]."
        )
        self.bullet(
            "**Co giãn quy mô tham gia (`Client Scaling 5 → 10 → 20`):** Tăng số nhà tuyển dụng "
            "hợp tác từ 5 lên 10 rồi 20 trên cùng danh mục `4.511` tin đẩy `Recall@20` tăng hơn "
            "**gấp đôi** (`0,2398 → 0,3512 → 0,4833`, tức +24,35 điểm). Lưu ý rằng thời gian chạy "
            "tăng gần tuyến tính với số silo (`6,9s → 12,4s → 23,5s` CUDA), phản ánh chi phí truyền "
            "thông và xử lý đồ thị con tỷ lệ thuận với độ phủ cộng tác."
        )
        self.bullet(
            "**Bằng chứng thực nghiệm về Client Drift (`local_epochs 1 → 5`):** Khi tăng số epoch "
            "cục bộ từ 1 lên 5 (`20 → 100` bước Adam/vòng), thời gian huấn luyện tăng gấp **4,84 lần** "
            "(`23,2s → 112,4s` CUDA; `39,7s → 195,5s` CPU), nhưng **`Recall@20` lại sụt giảm từ "
            "`0,4833` xuống `0,4565`** (-2,68 điểm) và `NDCG@20` giảm mạnh `-4,14` điểm (`0,3469 → "
            "0,3055`). Kết quả này cung cấp minh chứng định lượng sắc nét cho lý thuyết Client Drift "
            "của Karimireddy et al. [9] và Li et al. [10] trên các data silos Non-IID."
        )
        self.bullet(
            "**Trọng số tổng hợp và `FedProx (μ=0,01)`:** `FedAvg weighted` theo số cạnh `user–job` "
            "(`0,4833`) vượt `FedAvg unweighted` (`0,4716`, +1,17 điểm) vì bảo toàn đúng đóng góp "
            "thống kê của các doanh nghiệp nhiều dữ liệu [6]. Trong khi đó, `FedProx (μ=0,01)` đạt "
            "`0,4627` (thấp hơn `FedAvg` 2,06 điểm và chậm hơn ~5%): ở chế độ `local_epochs = 1` đã "
            "ít trôi, thành phần phạt proximal kèm cấu trúc Public Backbone chung vô tình kìm hãm "
            "tốc độ thích nghi của embedding cục bộ trong ngắn hạn 4 vòng [7]."
        )

        self.h2("4.4. Hội tụ 6 vòng liên kết và khảo sát siêu tham số (Sweep 8 cấu hình)")
        hist_rows = []
        for idx, h in enumerate(cuda["fedavg_main"]["history"]):
            cpu_h = cpu["fedavg_main"]["history"][idx]
            hist_rows.append([
                str(h["round"]),
                f"{h['loss']:.6f}",
                f"{h['recall20']:.6f}",
                f"{h['ndcg20']:.6f}",
                f"{h['round_seconds']:.2f}",
                f"{cpu_h['round_seconds']:.2f}",
            ])
        self.table(
            caption="Quá trình hội tụ qua 6 vòng của FedAvg (50N) trên Global Catalog",
            headers=["Vòng (Round)", "Loss trung bình", "Recall@20 (Global)", "NDCG@20 (Global)", "Thời gian CUDA (s)", "Thời gian CPU (s)"],
            rows=hist_rows,
            widths=[2.1, 2.7, 3.0, 2.9, 2.4, 2.4],
            font_size=10.5,
        )

        sweep_rows = []
        for idx, s in enumerate(sweep):
            cpu_s = cpu["sweep"][idx]
            sweep_rows.append([
                s["dim"],
                s["layers"],
                s["n_clients"],
                s["local_epochs"],
                f4(s["recall10"]),
                f4(s["recall20"]),
                f4(s["ndcg20"]),
                f4(s["mrr20"]),
                f4(s["coverage"]),
                f"{float(s['seconds']):.1f} / {cpu_s['seconds']:.1f}",
            ])
        self.table(
            caption="Kết quả khảo sát 8 cấu hình siêu tham số (Global Catalog, 6 vòng)",
            headers=["dim", "layers", "clients", "local_ep", "R@10", "R@20", "NDCG\n@20", "MRR\n@20", "Cov@10", "Giây (CUDA/CPU)"],
            rows=sweep_rows,
            widths=[0.95, 1.25, 1.30, 1.50, 1.40, 1.40, 1.65, 1.55, 1.50, 3.00],
            font_size=9.5,
            pad_tb=40,
            pad_lr=35,
        )

        self.figure(
            "fig5_convergence_and_sweep.png",
            "Đường cong hội tụ 6 vòng của FedAvg (50N) và khảo sát đánh đổi hiệu năng – thời gian của 8 cấu hình Sweep",
            width_cm=15.3,
        )

        self.p(
            "Từ Bảng 10, Bảng 11 và Hình 5: `FedAvg (50N)` tăng tốc nhanh nhất trong 3 vòng đầu "
            "(`Recall@20` Global tăng từ `0,034122` lên `0,045432`) và tiếp tục tiến ổn định lên "
            "`0,047515` ở vòng 6 với thời gian mỗi vòng rất đều đặn (`12,08–12,59s` CUDA; "
            "`20,99–23,29s` CPU). Trong Sweep 8 cấu hình: (i) tăng `dim` từ `16 → 32 → 64` nâng "
            "`Recall@20` (`0,0198 → 0,0221 → 0,0265`) nhưng tăng gấp đôi dung lượng truyền thông và "
            "thời gian CPU (`27,2s → 48,9s`); (ii) tăng số tầng `layers` từ `1 → 2` cải thiện "
            "`NDCG@20` (`0,0162 → 0,0178`), song lên `3` tầng lại chững hoàn toàn (`0,0176`) và "
            "chậm thêm 31% CUDA (`19,5s → 25,6s`) do hiện tượng làm mịn quá mức (*over-smoothing*) [1]; "
            "và (iii) tăng `local_epochs` lên `5` tái xác nhận sụt giảm hiệu năng (`0,0221 → 0,0187`) "
            "do Client Drift. Do đó, cấu hình `dim=32, layers=2, local_epochs=1` là điểm tối ưu Pareto."
        )

        self.h2("4.5. Phân tích độ trễ tính toán (CUDA vs CPU) và công bằng giữa các Silo")
        self.figure(
            "fig6_latency_and_fairness.png",
            "Phân bố độ trễ vòng huấn luyện qua 300 mẫu đo (CUDA vs CPU) và công bằng hiệu năng theo quy mô client",
            width_cm=15.3,
        )
        self.p(
            f"Thống kê trên {lat_cuda['n_samples']} mẫu đo độ trễ thực (`50 clients × 6 vòng` bằng "
            "`time.perf_counter()`, Hình 6a): **Kaggle CUDA** đạt trung vị `p50 = "
            f"{lat_cuda['p50_ms']:.2f} ms`, phân vị 95 `p95 = {lat_cuda['p95_ms']:.2f} ms` "
            f"(trung bình `{lat_cuda['mean_ms']:.2f} ms`, miền giá trị `{lat_cuda['min_ms']:.2f}–"
            f"{lat_cuda['max_ms']:.2f} ms`, tỷ số đuôi `p95/p50 = {lat_cuda['p95_over_p50']:.2f}`). "
            f"Trên **Local CPU**, độ trễ tăng `1,77x` với `p50 = {lat_cpu['p50_ms']:.2f} ms` và "
            f"`p95 = {lat_cpu['p95_ms']:.2f} ms` (`p95/p50 = {lat_cpu['p95_over_p50']:.2f}`). Tỷ số "
            "đuôi ổn định dưới 1,4 ở cả hai nền tảng xác nhận quy trình tính toán cục bộ không gặp "
            "hiện tượng nghẽn bất thường ở cấp đơn nút."
        )
        self.p(
            "Tuy nhiên, đánh giá công bằng theo quy mô doanh nghiệp (Hình 6b) phơi bày sự chênh lệch "
            f"rõ rệt: trong tổng số 9.116 silos có {fi(per_c['n_clients_without_test'])} silo "
            f"({per_c['pct_clients_without_test']:.2f}%) không có cạnh kiểm thử (vì ứng viên nộp "
            f"dưới 5 đơn). Trên {fi(per_c['n_clients_with_test'])} silo có tập test, nhóm `1.716` "
            f"doanh nghiệp quy mô lớn (`≥ 10` tin tuyển dụng) đạt trung bình `Recall@20 = "
            f"{per_c['recall20_ge10_jobs']:.4f}` trên Global Catalog, cao hơn **+40,5%** so với "
            f"nhóm `5.262` doanh nghiệp vừa và nhỏ (`< 10` tin, `Recall@20 = {per_c['recall20_lt10_jobs']:.4f}`). "
            "Đây là hệ quả trực tiếp của *quantity skew* khi các silo lớn xuất hiện dày đặc hơn trong "
            "tập tham gia top-K và chiếm tỷ trọng cao trong tổng hợp `FedAvg weighted`."
        )

        self.h2("4.6. Phân tích lỗi và các nút thắt cổ chai hệ thống (Error & Bottleneck Analysis)")
        self.p(
            "Để lý giải sâu sắc nguyên nhân gốc rễ đằng sau các khoảng cách hiệu năng ở Chương 4, "
            "nhóm thực hiện phân tích lỗi theo bốn nút thắt cổ chai định lượng của kiến trúc V3:"
        )
        self.bullet(
            "**1. Khoảng cách Global Catalog Gap (`0,0475` vs `0,3905` / `0,5408`):** Khi chấm điểm "
            "trên toàn bộ `82.876` tin tuyển dụng của thị trường, 50 nhà tuyển dụng tham gia trong "
            "`FedAvg (50N)` chỉ sở hữu `9.058` tin trong danh mục (**10,93%**). Theo cơ chế *Sparse "
            "Touched-Node*, khoảng **89,07%** (`73.818` tin) thuộc về 9.066 doanh nghiệp chưa từng "
            "được chọn vào vòng huấn luyện nên vector embedding của chúng vẫn giữ nguyên trạng thái "
            "khởi tạo ngẫu nhiên `N(0, 0.1²)`. Khi tính tích vô hướng `e_u^T e_j` trên toàn thị "
            "trường, các vector ngẫu nhiên chưa được chuẩn hóa tạo ra điểm số nhiễu chen ngang vào "
            "top-20, làm `Recall@20` giảm 8,2 lần so với khi xếp hạng trong `FL Catalog`. Điều này "
            "giải thích vì sao **Stratified Client Sampling** qua nhiều vòng hơn [17] là chìa khóa "
            "để thu hẹp Global Catalog Gap."
        )
        self.bullet(
            "**2. Nút thắt độ phủ O*NET (`31,44%`) và bất đối xứng `5,1x`:** Dù ánh xạ được "
            "136.264 ứng viên vào O*NET, phía tin tuyển dụng chỉ đạt độ phủ `31,44%` (`26.678 / "
            "84.845` tin) do giới hạn so khớp chuỗi tiêu đề (`norm_title`/`loose_title`). Kết quả "
            "là **68,56% tin tuyển dụng (58.167 tin)** bị đứt gãy cầu nối `job–occupation–skill`, "
            "không nhận được thông điệp kỹ năng từ ứng viên ở tầng 2. Khoảng cách giữa `FedAvg 20N` "
            "trên toàn bộ tập cố định (`0,4833`) và trên phân khúc tin có mã O*NET (`0,5756`, cao hơn "
            "+9,23 điểm) đo lường chính xác phần hiệu năng đang bị bỏ lỡ bởi nút thắt này."
        )
        self.bullet(
            "**3. Sai số tin khởi đầu lạnh (`1.969` cold-start jobs):** Trong Global Catalog có "
            "2,321% tin tuyển dụng hoàn toàn không có cạnh `user–job` trong tập train. Với chế độ "
            "chấm nghiêm ngặt `Cold=Miss`, `Recall@20` của Centralized LightGCN giảm nhẹ từ `0,4002` "
            "xuống `0,3963` (-0,39 điểm), còn `GraphSAGE` giảm `0,1376 → 0,1373`. Nếu tin cold-start "
            "đồng thời thiếu cả cạnh `job–occupation` (nằm trong nhóm 68,56% chưa map O*NET), không "
            "một đường lan truyền GNN nào có thể cập nhật biểu diễn cho tin đó."
        )
        self.bullet(
            "**4. Thiên lệch đuôi dài (Long-Tail Skew) giữa 9.116 Silos:** Với 3.877 silos có từ "
            "3 tin trở xuống và 22,38% silos không đủ cạnh test, các thuật toán lấy mẫu ưu tiên "
            "top-50 silo lớn nhất sẽ tự nhiên thiên vị nhóm doanh nghiệp tuyển dụng lớn, dẫn tới "
            "chênh lệch `+40,5%` Recall@20 đã quan sát ở Hình 6b và đòi hỏi cơ chế cá nhân hóa "
            "hoặc cụm hóa chức năng kiểu FED-PUB [22]."
        )

        # -------------------------------------------------------------
        # CHƯƠNG 5 (MỚI — DEMO & HỆ THỐNG FULL-STACK)
        # -------------------------------------------------------------
        self.h1("CHƯƠNG 5. TRIỂN KHAI DEMO VÀ KIỂM CHỨNG HỆ THỐNG FULL-STACK")

        self.h2("5.1. Kiến trúc triển khai 3 tầng và lược đồ PostgreSQL 16 (21,3+ triệu dòng)")
        self.p(
            "Để chuyển hóa mô hình nghiên cứu **FedGraph** thành một Hệ thống Hỗ trợ Ra quyết định "
            "(DSS) có khả năng trình diễn, kiểm toán dữ liệu và quan sát hành vi Federated Learning "
            "theo thời gian thực, nhóm thiết kế kiến trúc **Full-Stack 3 tầng** tách biệt hoàn toàn: "
            "(1) tầng lưu trữ **PostgreSQL 16 Alpine** (`docker-compose.yml`, container `dss-postgres`, "
            "cổng `5433`, cơ sở dữ liệu `dss_jobs`), (2) tầng dịch vụ **FastAPI + WebSocket** "
            "(`api/main.py`, `api/dashboard.py`, `api/db.py`, `api/fl_sim.py`), và (3) tầng giao "
            "diện trực quan **React 19 + TypeScript 5.7 + Vite 6.2 + Three.js 0.173 + Recharts 2.15**."
        )
        self.p(
            "Ở tầng dữ liệu (`api/schema.sql`, `api/load_to_pg.py`), hệ thống quản lý **9 bảng quan "
            "hệ với hơn 21,3 triệu bản ghi** được nạp hàng loạt tốc độ cao qua giao thức `COPY ... "
            "FROM STDIN`: bốn bảng thực thể gốc gồm `users` (171.807 dòng), `jobs` (84.845 dòng), "
            "`apps` (436.893 dòng), `employers` (9.116 dòng); hai bảng mở rộng kỹ năng 2 bước nhảy "
            "được vật chất hóa từ `artifacts/v3/graph.npz` nhằm phục vụ truy vấn gợi ý tức thời "
            "gồm `job_skills` (**2.593.468 dòng**) và `user_skills` (**18.017.133 dòng**); cùng ba "
            "bảng nhật ký theo dõi huấn luyện là `train_runs`, `round_metrics` và `node_latency`. "
            "Hệ thống đánh chỉ mục bắt buộc `idx_job_skills_job` và `idx_user_skills_user` để tránh "
            "quét tuần tự 18 triệu dòng khi gọi `POST /api/recommend`. Khi vận hành ở môi trường không "
            "bật Docker PostgreSQL (`DSS_DRY_RUN=1`), `make_store()` trong `api/db.py` tự động kích "
            "hoạt lớp `InMemoryStore` sử dụng ma trận thưa nén hàng `_CSR` giữ nguyên toàn bộ đồ thị "
            "thật V3 trong RAM với chi phí bộ nhớ tối thiểu."
        )

        self.table(
            caption="Đặc tả 15 điểm cuối REST/WebSocket và 9 bảng cơ sở dữ liệu trong hệ thống Full-Stack",
            headers=["Phân hệ / Tệp nguồn", "Thành phần / Endpoint / Bảng", "Chức năng & Dữ liệu phục vụ"],
            rows=[
                ["`api/schema.sql` (9 bảng)", "`users`, `jobs`, `apps`, `employers`", "Lưu 171.807 ứng viên, 84.845 tin, 436.893 lượt nộp, 9.116 silos"],
                ["`api/schema.sql` (2-hop)", "`job_skills` (2,59M), `user_skills` (18,02M)", "Vật chất hóa quan hệ kỹ năng 2-hop; đánh index phục vụ `/api/recommend`"],
                ["`api/schema.sql` (Telemetry)", "`train_runs`, `round_metrics`, `node_latency`", "Lưu lịch sử chạy FL, chỉ số từng vòng, độ trễ & bytes từng client"],
                ["`api/main.py` (Core REST)", "`GET /health`, `/api/clients`, `/api/clients/{id}`, `/api/graph/summary`", "Kiểm tra kết nối DB/artifacts, phân trang 9.116 silos & top kỹ năng"],
                ["`api/main.py` (Inference)", "`POST /api/recommend`", "Gợi ý top-K việc làm theo giao thoa kỹ năng 2-hop + popularity + nghề"],
                ["`api/main.py` (FL Control)", "`POST /api/train/start`, `/stop/{id}`, `GET /status/{id}`, `/runs`", "Khởi tạo, dừng an toàn đầu vòng kế và truy vấn phiên chạy FL"],
                ["`api/main.py` (WebSocket)", "`WS /ws/latency`, `WS /ws/train/{run_id}`", "Đẩy từng sự kiện độ trễ `perf_counter()` và chỉ số vòng theo thời gian thực"],
                ["`api/dashboard.py` (V3)", "`GET /api/dashboard/overview`, `/graph`, `/fl-sim`, `/conclusions`", "Cung cấp số liệu V3, mẫu 430 nút 3D, 5 kịch bản FL, ma trận 6 tiêu chí"],
            ],
            widths=[3.8, 5.2, 6.5],
            font_size=10.0,
            pad_tb=42,
        )

        self.h2("5.2. Trực quan hóa Tổng quan và Khám phá Đồ thị 2-Hop LightGCN (/, /do-thi)")
        self.p(
            "Toàn bộ 5 trang giao diện thực tế đã được khởi chạy trực tiếp trên nền FastAPI "
            "(`uvicorn api.main:app --port 8000`) kết nối dữ liệu thực V3 và Vite React (`:5173`), "
            "kiểm chứng hiển thị WebGL/Recharts đầy đủ ở độ phân giải cao. **Lưu ý nguồn số liệu "
            "hiển thị**: tệp `api/dashboard.py` đọc `results/v3/notebook_metrics.json` (bản chạy "
            "Local CPU), do đó các màn hình web hiển thị độ trễ CPU (`p50 = 418,0 ms`, `p95 = 566,6 ms`) "
            "và tie-break CPU của `Popularity` (`0,0542`) / `Item-KNN` (`0,4897`)—hoàn toàn nhất quán "
            "với dữ liệu đối chứng Local CPU đã trình bày ở Chương 4."
        )
        self.p(
            "Hình 7 trình bày trang **Tổng quan** (`OverviewPage.tsx`, route `/`). Khối bên trái "
            "tích hợp thành phần 3D `FederatedGlassConstellation` (Three.js) mô phỏng trực quan chu "
            "trình 4 bước giữa Máy chủ điều phối (`52.544` cạnh công khai) và `9.116` client doanh "
            "nghiệp (`711.820` cạnh riêng tư khóa kín, `0 B` dữ liệu thô rời máy). Khối bên phải nổi "
            "bật KPI `0.5756 FedAvg · O*NET` cùng thanh so sánh tỷ lệ từ `Popularity (0.0542)` đến "
            "`LightGCN (0.7151)`. Bên dưới là ba thẻ tóm tắt quy mô (`264.995 nút`, `9.116 Node FL`, "
            "`37.957 cạnh test`), thanh phân tách tỷ lệ cạnh Công khai/Riêng tư (6,9% vs 93,1%) gắn "
            "thông số PostgreSQL `2.59M job_skills · 18.02M user_skills`, và bảng đối chiếu 7 mô hình "
            "giữa `Global Catalog (82.876 tin)` và `FL Catalog (9.058 tin)`."
        )

        self.figure(
            "demo_01_overview.png",
            "Giao diện trang Tổng quan (/) với Three.js FederatedGlassConstellation và bảng đối chiếu 7 mô hình V3",
            width_cm=15.0,
            base_dir=DEMO_DIR,
        )

        self.p(
            "Hình 8 ghi nhận màn hình **Đồ thị việc làm** (`JobGraphPage.tsx`, route `/do-thi`). "
            "Backend `/api/dashboard/graph` trích xuất tất định một đồ thị con 430 nút đại diện "
            "(`30` nghề O*NET lõi ở bán cầu trong `r≈3,4`, `120` kỹ năng phổ biến `r≈5,6`, `200` "
            "tin tuyển dụng `r≈7,8` và `80` ứng viên vỏ ngoài `r≈10,4`) bố cục bằng thuật toán "
            "Fibonacci-sphere kết hợp tinh chỉnh lực lò xo 3D (`2.994` cạnh). Người dùng có thể chuyển "
            "đổi giữa chế độ **2D Phẳng** và **3D WebGL**, bật/tắt ranh giới cạnh **Công khai** / "
            "**Riêng tư**, lọc loại nút hoặc tìm kiếm tiếng Việt không dấu (`_fold()`). Điểm nhấn "
            "nghiên cứu của trang là hộp công cụ **LightGCN 2-Hop Explainer** trong `Node Inspector`: "
            "khi chọn `Ứng viên #76044` (bậc `3`, phạm vi `Riêng tư (Client)`) và kích hoạt nút "
            "`Đang phát 2-Hop`, giao diện tô sáng đường truyền tin từ 3 nút lân cận tầng 1 sang "
            "**10 nút tiếp cận được ở tầng 2** (như `Nghề O*NET 13-1199`, `Nghề O*NET 11-3071`, và các "
            "ứng viên đồng hành), hiển thị trực tiếp công thức chuẩn hóa đối xứng LightGCN."
        )

        self.figure(
            "demo_02_graph_2hop.png",
            "Trang Đồ thị việc làm (/do-thi) minh họa LightGCN 2-Hop Explainer trên Ứng viên #76044 (Layer 1 -> Layer 2)",
            width_cm=15.2,
            base_dir=DEMO_DIR,
        )

        self.h2("5.3. Mô phỏng kịch bản FL và Giám sát Node thời gian thực (/lien-bang, /giam-sat-node)")
        self.p(
            "Hình 9 minh họa trang **Mô phỏng Federated Learning** (`FlSimPage.tsx`, route `/lien-bang`). "
            "Màn hình cung cấp bộ chọn 5 kịch bản thực nghiệm (`20 Node Fixed 4.511 tin`, `20 Node "
            "O*NET 956 tin`, `50 Node Main 9.058 tin`, `10 Node`, `5 Node`), công tắc chuyển đổi nhanh "
            "giữa `FL Catalog` và `Global (82.876)` cùng thanh trượt vòng `1..6`. Trên kịch bản "
            "`20 Node Fixed`, biểu đồ Recharts vẽ đường hội tụ `FedAvg Recall@20 = 0.4833` và "
            "`NDCG@20 = 0.3469` kèm các đường tham chiếu `LightGCN (0.7151)`, `GraphSAGE (0.5113)` "
            "và `Popularity (0.0542)`. Ở nửa dưới là hai biểu đồ song song **Ablation Study (+9,0% R@20)** "
            "và **Client Scaling (5 → 10 → 20 Node, ×2,02 Recall@20)** cùng ba bảng mở rộng cho 15 "
            "biến thể Ablation, 8 cấu hình Sweep và Top 20 nhà tuyển dụng. *(Ghi chú kiểm toán mã "
            "nguồn: dòng 114 của `FlSimPage.tsx` lọc chuỗi `'(d) FedAvg unweighted'` thay vì `'(g) FedAvg "
            "unweighted'` trong CSV nên thanh tóm tắt rút gọn hiển thị 5/6 biến thể chính, trong khi "
            "bảng mở rộng 15 dòng bên dưới vẫn hiển thị đầy đủ 100% số liệu gốc.)*"
        )

        self.figure(
            "demo_03_fl_sim.png",
            "Trang Mô phỏng FL (/lien-bang) với đường cong hội tụ 6 vòng, Ablation Study và Client Scaling",
            width_cm=15.0,
            base_dir=DEMO_DIR,
        )

        self.p(
            "Hình 10 ghi nhận trạng thái vận hành thực tế của trang **Giám sát & Thực nghiệm Node FL** "
            "(`NodeMonitorPage.tsx`, route `/giam-sat-node`) sau khi kích hoạt **`Preset 2 · Stress 30% "
            "Drop + Deadline`** (`100 clients · 8 vòng · FedProx · 30% dropout · cắt ngưỡng 65ms · FP32`). "
            "Backend `api/fl_sim.py` đẩy từng sự kiện tick qua WebSocket `/ws/latency` và cập nhật "
            "vòng qua `/ws/train/{run_id}` bằng thời gian thực đo CPU `time.perf_counter()`, đạt trạng thái "
            "hoàn tất `Vòng 8/8`: `Recall@20 = 0.575`, `NDCG@20 = 0.449`, `Drift TB = 0.31`, độ trễ "
            "`p50 / p95 = 22.91 / 65 ms` (bị cắt trần bởi chính sách Deadline 65ms), `70/70` client "
            "hoạt động (30 node mất kết nối) và tổng tải `57.50 MB (0 B dữ liệu ứng viên rời máy)`. "
            "Khối trung tâm trình diễn **3D Topology** (`LiveFlTopology3D`) với chiều cao cột tỷ lệ "
            "logarit theo trọng số `p_k` và mã màu theo mức Client Drift, đi kèm **Node Inspector** "
            "đang soi hồ sơ nhà tuyển dụng lớn nhất `randstad` (`client_id=0`, `4.215` users, `603` "
            "jobs, trọng số `p_k = 8,05%`, `Client Drift = 0,45`, trạng thái `Offline`). Đặc biệt, "
            "biểu đồ **Non-IID Fairness & Coordinated Brushing** ở đáy trang định lượng sự chênh lệch "
            "giữa nhóm `Top 10% Large Drift = 0.251` và nhóm `Long-Tail Small Drift = 0.436` (chênh lệch "
            "công bằng `Fairness Gap Δ = 0.185`), cho phép nhấp chọn từng điểm phân tán để đồng bộ hóa "
            "lựa chọn trên cảnh 3D và Node Inspector."
        )

        self.figure(
            "demo_04_node_monitor.png",
            "Trang Giám sát Node FL (/giam-sat-node) chạy Preset 2 Stress 30% Drop + Deadline 65ms hoàn tất 8/8 vòng",
            width_cm=14.2,
            base_dir=DEMO_DIR,
        )

        self.h2("5.4. Trang Kết luận & Ma trận kiểm chứng và Ranh giới Mô phỏng (/ket-luan)")
        self.p(
            "Hình 11 trình bày trang **Kết luận và hạn chế** (`ConclusionsPage.tsx`, route `/ket-luan`) "
            "với ma trận đối chiếu 6 tiêu chí đề bài (`5/6 yêu cầu đạt · 1 chưa đạt` do chưa triển khai "
            "**Online A/B Test** trên người dùng thật), tóm tắt 3 thành tựu, 5 hạn chế thực tế trung thực, "
            "4 bài học phương pháp và lộ trình phát triển kèm lệnh tái lập CLI."
        )

        self.figure(
            "demo_05_conclusions.png",
            "Trang Kết luận và hạn chế (/ket-luan) hiển thị Ma trận kiểm chứng 6 tiêu chí (5/6 Đạt) và Roadmap V3",
            width_cm=13.4,
            base_dir=DEMO_DIR,
        )

        self.p(
            "Nhằm bảo đảm chuẩn mực trung thực khoa học tuyệt đối, Bảng 13 phân định rành mạch giữa "
            "những thành phần sử dụng **dữ liệu thật và phép đo thực tế** với những thành phần mang "
            "tính **mô phỏng tương tác phục vụ nghiên cứu giao diện** trong ứng dụng Web Full-Stack."
        )

        self.table(
            caption="Phân định ranh giới giữa Thành phần thực đo V3 và Mô phỏng tương tác trên Web Demo",
            headers=["Thành phần / Chức năng hệ thống", "Bản chất triển khai", "Nguồn dữ liệu / Cơ chế xác thực"],
            rows=[
                ["Đồ thị V3 & Phân vùng 9.116 Silos", "**Dữ liệu thật V3**", "`artifacts/v3/graph.npz`, `clients.json`, `meta.json` (264.995 nút, 764.364 cạnh)"],
                ["Cơ sở dữ liệu & 18/18 Smoke Checks", "**Hệ thống thật**", "PostgreSQL 16 `dss_jobs` (9 bảng, >21,3M dòng) + fallback `InMemoryStore` `_CSR`"],
                ["Gợi ý `/api/recommend` & Đồ thị `/graph`", "**Thuật toán thật**", "Giao thoa kỹ năng 2-hop + popularity + nghề; lấy mẫu 430 nút Fibonacci-shell"],
                ["Bảng Benchmark, Ablation & Sweep", "**Kết quả thực nghiệm V3**", "`results/v3/notebook_metrics.json` & `results_v3/` (800 eval users, 1.000 bootstrap)"],
                ["Độ trễ từng client khi chạy `/ws/latency`", "**Đo thật bằng `perf_counter()`**", "`api/fl_sim.py` tính ma trận NumPy (dim ≤ 256) và tuần tự hóa byte thật trên CPU"],
                ["Đường cong Recall/Loss trong `/ws/train`", "**Mô phỏng hàm mũ**", "`api/fl_sim.py:_metric_for()` gắn cờ `simulated_metrics: True` (không train GNN live)"],
                ["Dropout, Deadline 65ms, Nén Top-20% & Drift", "**UI Fault-Injection Simulator**", "`NodeMonitorPage.tsx` (`applyResearchEffects()`, `computeClientDrift()`) mô phỏng công thức"],
            ],
            widths=[4.8, 3.6, 7.1],
            font_size=10.5,
            pad_tb=42,
        )

        # -------------------------------------------------------------
        # CHƯƠNG 6
        # -------------------------------------------------------------
        self.h1("CHƯƠNG 6. KẾT LUẬN, HẠN CHẾ VÀ HƯỚNG PHÁT TRIỂN")

        self.h2("6.1. Tổng kết kết quả đạt được")
        self.p(
            "Đồ án **FedGraph** đã giải quyết trọn vẹn bài toán xây dựng hệ thống gợi ý việc làm bảo "
            "vệ quyền riêng tư theo mô hình **Cross-Silo Federated Learning** kết hợp **LightGCN** "
            "trên bộ dữ liệu quy mô công nghiệp **CareerBuilder + O*NET 29.3 V3**. Hệ thống đáp ứng "
            "hoàn chỉnh **5/6 tiêu chí kiểm chứng kỹ thuật cốt lõi**: (1) Bảo toàn 0 byte dữ liệu "
            "`user–job` và `user_history` rời khỏi `9.116` employer silos (`GraphSafe`) trên đồ thị "
            "264.995 nút, 764.364 cạnh; (2) Chứng minh hiệu quả vượt trội của Học liên kết so với cô "
            "lập cục bộ (`FedAvg 20N = 0,4833` so với `Local-only Strict Silo = 0,2460`, tăng +96,5% "
            "tương đối, và đạt `0,5756` trên nhóm tin có O*NET); (3) Định lượng giá trị cầu nối tri "
            "thức công khai O*NET (`+9,00` điểm phần trăm Recall@20) và xác nhận thực nghiệm hiện "
            "tượng Client Drift (`local_epochs 1 → 5` giảm `0,4833 → 0,4565`); (4) Vận hành cơ sở "
            "dữ liệu PostgreSQL 16 với hơn 21,3 triệu dòng cùng 15 điểm cuối FastAPI/WebSocket đạt "
            "18/18 kiểm thử khói; và (5) Triển khai ứng dụng React 19 + Three.js 5 trang tích hợp "
            "LightGCN 2-Hop Explainer và FL Research Workbench."
        )

        self.h2("6.2. Năm hạn chế trung thực của hệ thống V3")
        self.p(
            "Báo cáo tổng hợp minh bạch năm hạn chế kỹ thuật của phiên bản hiện tại làm cơ sở cho "
            "các bước cải tiến kế tiếp:"
        )
        self.bullet(
            "**1. Chưa tích hợp DP-SGD và Secure Aggregation trong huấn luyện PyTorch:** Dù GraphSafe "
            "không chia sẻ dữ liệu thô, các ma trận `E_local` / ΔW vẫn được tổng hợp dạng rõ tại "
            "server, chưa miễn nhiễm trước tấn công suy ngược gradient [11, 12, 13]."
        )
        self.bullet(
            "**2. Chịu lỗi Straggler/Dropout và nén ΔW mới ở mức mô phỏng giao diện:** Vòng lặp V3 "
            "chạy đồng bộ trên một máy đơn; các kịch bản Dropout (15–30%), cắt Deadline 65ms và nén "
            "`FP16`/`Top-20%` hiện phục vụ phân tích tương tác trên `NodeMonitorPage.tsx` dựa trên "
            "độ trễ CPU của `api/fl_sim.py`."
        )
        self.bullet(
            "**3. Độ phủ ánh xạ O*NET mới đạt 31,44%:** Khớp chuỗi tiêu đề chỉ liên kết được "
            "`26.678 / 84.845` tin tuyển dụng vào mã `soc[:7]`, để lại 68,56% tin thiếu cầu nối "
            "kỹ năng công khai trên tầng Public Backbone [30, 32]."
        )
        self.bullet(
            "**4. Khoảng cách Global Catalog Gap (`0,0475` vs `0,3905`):** Do mỗi vòng chỉ chọn 50 "
            "trên 9.116 silos (10,93% danh mục), ~89% số tin còn lại giữ nguyên embedding ngẫu nhiên "
            "khi đánh giá trên toàn thị trường 82.876 tin [17, 26]."
        )
        self.bullet(
            "**5. Chưa thực hiện Online A/B Testing:** Toàn bộ đánh giá hiện nay dựa trên dữ liệu lịch "
            "sử ngoại tuyến (`37.077` clean test edges); chưa đo trực tiếp CTR hay tỷ lệ chuyển đổi "
            "ứng tuyển thực tế [28]."
        )

        self.h2("6.3. Lộ trình phát triển tiếp theo")
        self.p(
            "Dựa trên kết quả phân tích lỗi ở Chương 4 và kiểm chứng hệ thống ở Chương 5, nhóm đề "
            "xuất bốn hướng nâng cấp ưu tiên:"
        )
        self.bullet(
            "**Mở rộng độ phủ O*NET từ 31,44% lên >85% bằng Sentence-BERT / Transformer [30]:** Thay "
            "thế so khớp chuỗi cứng bằng đối khớp vector ngữ nghĩa từ tiêu đề và mô tả công việc để "
            "kết nối nốt `58.167` tin còn lại vào mạng kỹ năng O*NET."
        )
        self.bullet(
            "**Tích hợp DP-SGD [11], Secure Aggregation [12] và Top-K Compression [14] vào vòng "
            "huấn luyện PyTorch:** Đo đạc trực tiếp đường cong đánh đổi *Privacy (ε, δ) – Utility "
            "(Recall@20) – Bandwidth (MB)* khi cắt ngưỡng, thêm nhiễu Gaussian và nén thưa ΔW thật."
        )
        self.bullet(
            "**Stratified Client Sampling [17] và cá nhân hóa FED-PUB [22]:** Lấy mẫu phân tầng "
            "qua nhiều vòng hơn trên toàn bộ 9.116 silos để thu hẹp Global Catalog Gap, kết hợp "
            "tổng hợp theo cụm tương đồng chức năng nhằm giảm chênh lệch +40,5% cho 5.262 doanh "
            "nghiệp nhỏ."
        )
        self.bullet(
            "**Thử nghiệm chịu lỗi phân tán đa tiến trình [8] và Online A/B Testing [28]:** Bổ sung "
            "giả lập độ trễ mạng thực thụ khi huấn luyện LightGCN và triển khai kiểm thử A/B trực "
            "tuyến có kiểm soát."
        )

        self.table(
            caption="Ma trận tổng hợp mức độ hoàn thành mục tiêu và lộ trình phát triển FedGraph",
            headers=["Tiêu chí / Hạng mục", "Trạng thái", "Bằng chứng kiểm chứng V3", "Định hướng nâng cấp"],
            rows=[
                ["Bảo vệ riêng tư dữ liệu thô (`GraphSafe`)", "**Đạt**", "0 B `user–job`/`user_history` rời silo; 9.116 silos", "Bổ sung `DP-SGD` [11] & `SecAgg` [12] trong PyTorch"],
                ["Hiệu quả FL vượt cô lập cục bộ", "**Đạt**", "`FedAvg 20N = 0,4833` vs `Local-only = 0,2460` (+96,5%)", "Stratified Sampling [17] thu hẹp Global Gap"],
                ["Đóng góp tri thức công khai O*NET", "**Đạt**", "`+9,00 pts` (`0,3933 → 0,4833`); `0,5756` trên tin O*NET", "Dùng Transformer/SBERT [30] nâng phủ `31,44% → >85%`"],
                ["Cơ sở dữ liệu & API Full-Stack", "**Đạt**", "PostgreSQL >21,3M dòng; `18/18` smoke checks; 15 API/WS", "Phân vùng chỉ mục & tải trực tiếp không `DRY_RUN`"],
                ["Độ trễ & Giám sát trực quan 3D", "**Đạt**", "`p50=236,49 ms` CUDA / `418,03 ms` CPU; UI 5 trang 3D", "Đưa Straggler/Dropout/Top-K vào ML training thực"],
                ["Kiểm thử người dùng trực tuyến", "**Chưa**", "Mới đánh giá offline (800 users, 1.000 bootstrap)", "Triển khai **Online A/B Test** đo CTR & hài lòng [28]"],
            ],
            widths=[3.7, 1.9, 5.1, 4.8],
            font_size=10.5,
        )

        # -------------------------------------------------------------
        # TÀI LIỆU THAM KHẢO (32 nguồn IEEE kiểm chứng từ citations.md)
        # -------------------------------------------------------------
        self.h1("TÀI LIỆU THAM KHẢO")
        refs = [
            '[1] X. He, K. Deng, X. Wang, Y. Li, Y. Zhang, and M. Wang, "LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation," in Proc. 43rd Int. ACM SIGIR Conf. Res. Develop. Inf. Retr. (SIGIR \'20), 2020, pp. 639–648, doi: 10.1145/3397271.3401063.',
            '[2] X. Wang, X. He, M. Wang, F. Feng, and T.-S. Chua, "Neural Graph Collaborative Filtering," in Proc. 42nd Int. ACM SIGIR Conf. Res. Develop. Inf. Retr. (SIGIR \'19), 2019, doi: 10.1145/3331184.3331267.',
            '[3] S. Rendle, C. Freudenthaler, Z. Gantner, and L. Schmidt-Thieme, "BPR: Bayesian Personalized Ranking from Implicit Feedback," in Proc. 25th Conf. Uncertainty Artif. Intell. (UAI \'09), 2009, doi: 10.48550/arXiv.1205.2618.',
            '[4] W. L. Hamilton, Z. Ying, and J. Leskovec, "Inductive Representation Learning on Large Graphs," in Adv. Neural Inf. Process. Syst. (NeurIPS \'17), vol. 30, 2017.',
            '[5] B. Sarwar, G. Karypis, J. Konstan, and J. Riedl, "Item-based collaborative filtering recommendation algorithms," in Proc. 10th Int. Conf. World Wide Web (WWW \'01), 2001, doi: 10.1145/371920.372071.',
            '[6] H. B. McMahan, E. Moore, D. Ramage, S. Hampson, and B. Agüera y Arcas, "Communication-Efficient Learning of Deep Networks from Decentralized Data," in Proc. 20th Int. Conf. Artif. Intell. Statist. (AISTATS \'17), PMLR vol. 54, 2017.',
            '[7] T. Li, A. K. Sahu, M. Zaheer, M. Sanjabi, A. Talwalkar, and V. Smith, "Federated Optimization in Heterogeneous Networks," in Proc. Mach. Learn. Syst. (MLSys \'20), 2020.',
            '[8] P. Kairouz et al., "Advances and Open Problems in Federated Learning," Found. Trends Mach. Learn., vol. 14, no. 1–2, pp. 1–210, 2021, doi: 10.1561/2200000083.',
            '[9] S. P. Karimireddy, S. Kale, M. Mohri, S. J. Reddi, S. U. Stich, and A. T. Suresh, "SCAFFOLD: Stochastic Controlled Averaging for Federated Learning," in Proc. 37th Int. Conf. Mach. Learn. (ICML \'20), PMLR vol. 119, 2020.',
            '[10] Q. Li, Y. Diao, Q. Chen, and B. He, "Federated Learning on Non-IID Data Silos: An Experimental Study," in Proc. IEEE 38th Int. Conf. Data Eng. (ICDE \'22), 2022, doi: 10.1109/ICDE53745.2022.00077.',
            '[11] M. Abadi et al., "Deep Learning with Differential Privacy," in Proc. 2016 ACM SIGSAC Conf. Comput. Commun. Secur. (CCS \'16), 2016, doi: 10.1145/2976749.2978318.',
            '[12] K. Bonawitz et al., "Practical Secure Aggregation for Privacy-Preserving Machine Learning," in Proc. 2017 ACM SIGSAC Conf. Comput. Commun. Secur. (CCS \'17), 2017, doi: 10.1145/3133956.3133982.',
            '[13] L. Zhu, Z. Liu, and S. Han, "Deep Leakage from Gradients," in Adv. Neural Inf. Process. Syst. (NeurIPS \'19), vol. 32, 2019, doi: 10.48550/arXiv.1906.08935.',
            '[14] Y. Lin, S. Han, H. Mao, Y. Wang, and W. J. Dally, "Deep Gradient Compression: Reducing the Communication Bandwidth for Distributed Training," in Int. Conf. Learn. Represent. (ICLR \'18), 2018, doi: 10.48550/arXiv.1712.01887.',
            '[15] C. Wu, F. Wu, L. Lyu, T. Qi, Y. Huang, and X. Xie, "A Federated Graph Neural Network Framework for Privacy-Preserving Personalization," Nature Communications, vol. 13, art. 3091, 2022, doi: 10.1038/s41467-022-30714-9.',
            '[16] M. Ammad-ud-din et al., "Federated Collaborative Filtering for Privacy-Preserving Personalized Recommendation System," arXiv:1901.09888, 2019, doi: 10.48550/arXiv.1901.09888.',
            '[17] K. Muhammad et al., "FedFast: Going Beyond Average for Faster Training of Federated Recommender Systems," in Proc. 26th ACM SIGKDD Int. Conf. Knowl. Discov. Data Min. (KDD \'20), 2020, doi: 10.1145/3394486.3403176.',
            '[18] Y. Lin et al., "Meta Matrix Factorization for Federated Rating Predictions," in Proc. 43rd Int. ACM SIGIR Conf. Res. Develop. Inf. Retr. (SIGIR \'20), 2020, doi: 10.1145/3397271.3401081.',
            '[19] G. Lin, F. Liang, W. Pan, and Z. Ming, "FedRec: Federated Recommendation With Explicit Feedback," IEEE Intell. Syst., vol. 36, no. 5, pp. 21–30, 2021, doi: 10.1109/MIS.2020.3017205.',
            '[20] F. Chen, P. Li, T. Miyazaki, and C. Wu, "FedGraph: Federated Graph Learning With Intelligent Sampling," IEEE Trans. Parallel Distrib. Syst., vol. 33, no. 8, 2022, doi: 10.1109/TPDS.2021.3125565.',
            '[21] K. Zhang, C. Yang, X. Li, L. Sun, and S. M. Yiu, "Subgraph Federated Learning with Missing Neighbor Generation," in Adv. Neural Inf. Process. Syst. (NeurIPS \'21), vol. 34, 2021, doi: 10.48550/arXiv.2106.13430.',
            '[22] J. Baek, W. Jeong, J. Jin, J. Yoon, and S. J. Hwang, "Personalized Subgraph Federated Learning," in Proc. 40th Int. Conf. Mach. Learn. (ICML \'23), PMLR vol. 202, 2023, doi: 10.48550/arXiv.2206.10206.',
            '[23] C. He et al., "FedGraphNN: A Federated Learning System and Benchmark for Graph Neural Networks," ICLR 2021 Workshop on DPML / arXiv:2104.07145, 2021, doi: 10.48550/arXiv.2104.07145.',
            '[24] X. Fu, B. Zhang, Y. Dong, C. Chen, and J. Li, "Federated Graph Machine Learning: A Survey of Concepts, Techniques, and Applications," ACM SIGKDD Explor. Newsl., 2022, doi: 10.1145/3575637.3575644.',
            '[25] R. Liu, P. Xing, Z. Deng, A. Li, C. Guan, and H. Yu, "Federated Graph Neural Networks: Overview, Techniques, and Challenges," IEEE Trans. Neural Netw. Learn. Syst., 2025, doi: 10.1109/TNNLS.2024.3360429.',
            '[26] Z. Sun, Y. Xu, Y. Liu, W. He, Y. L. Jiang, F. Wu, and L.-z. Cui, "A Survey on Federated Recommendation Systems," IEEE Trans. Neural Netw. Learn. Syst., 2024, doi: 10.1109/TNNLS.2024.3354924.',
            '[27] C. de Ruijt and S. Bhulai, "Job Recommender Systems: A Review," arXiv:2111.13576, 2021, doi: 10.48550/arXiv.2111.13576.',
            '[28] Y. Mashayekhi, N. Li, B. Kang, J. Lijffijt, and T. De Bie, "A Challenge-Based Survey of E-Recruitment Recommendation Systems," ACM Comput. Surv., vol. 56, no. 10, 2024, doi: 10.1145/3659942.',
            '[29] A. Giabelli, L. Malandri, F. Mercorio, M. Mezzanzanica, and A. Seveso, "Skills2Job: A recommender system that encodes job offer embeddings on graph databases," Appl. Soft Comput., vol. 101, art. 107049, 2021, doi: 10.1016/j.asoc.2020.107049.',
            '[30] R. Alonso, D. Dessí, A. Meloni, and D. Reforgiato Recupero, "A novel approach for job matching and skill recommendation using transformers and the O*NET database," Big Data Res., art. 100509, 2025, doi: 10.1016/j.bdr.2025.100509.',
            '[31] J. Zhao, J. Wang, M. Sigdel, B. Zhang, P. Hoang, M. Liu, and M. Korayem, "Embedding-based Recommender System for Job to Candidate Matching on Scale," arXiv:2107.00221, 2021, doi: 10.48550/arXiv.2107.00221.',
            '[32] National Center for O*NET Development, "O*NET 29.3 Database," U.S. Department of Labor, Employment and Training Administration, 2025. [Online]. Available: https://www.onetcenter.org/database.html',
        ]
        for ref in refs:
            p = self.doc.add_paragraph(style="Normal")
            pf = p.paragraph_format
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.left_indent = Cm(0.9)
            pf.first_line_indent = Cm(-0.9)
            pf.line_spacing = 1.4
            pf.space_before = Pt(0)
            pf.space_after = Pt(4)
            r = p.add_run(ref)
            _set_run_font(r, size_pt=12.5)

    def save(self, out_path: Path) -> Path:
        _enable_update_fields(self.doc)
        buf = io.BytesIO()
        self.doc.save(buf)
        buf.seek(0)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(buf, "r") as zin, zipfile.ZipFile(
            out_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/theme/theme1.xml":
                    txt = data.decode("utf-8")
                    txt = re.sub(
                        r'typeface="(Calibri Light|Calibri|Cambria)"',
                        'typeface="Times New Roman"',
                        txt,
                    )
                    data = txt.encode("utf-8")
                zout.writestr(item, data)
        return out_path

    def verify_grounding(self) -> None:
        missing_cites = [i for i in range(1, 33) if i not in self.inline_citations]
        if missing_cites:
            raise AssertionError(
                f"Các tài liệu tham khảo chưa được trích dẫn inline trong văn bản: {missing_cites}"
            )
        if self.fig_count != 11:
            raise AssertionError(f"Kỳ vọng 11 hình, thực tế chèn {self.fig_count}")
        if self.tab_count != 14:
            raise AssertionError(f"Kỳ vọng 14 bảng đánh số, thực tế chèn {self.tab_count}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build FedGraph formal DOCX report")
    ap.add_argument(
        "--word-update",
        action="store_true",
        help="Chạy WINWORD.EXE COM cập nhật TOC/LOF/LOT và hậu xử lý XML",
    )
    ap.add_argument(
        "--qa-pdf-dir",
        type=Path,
        default=None,
        help="Thư mục xuất PDF kiểm tra chất lượng (chỉ khi bật --word-update)",
    )
    args = ap.parse_args()

    data = load_ground_truth()
    builder = FedGraphReportBuilder(data)
    builder.build_cover_page()
    builder.start_main_section()
    builder.build_front_matter()
    builder.build_chapters()
    builder.verify_grounding()
    out = builder.save(OUT_DOCX)
    print(
        f"Generated {out} | Figures={builder.fig_count} | Tables={builder.tab_count} "
        f"| Equations={builder.eq_count} | Algorithms={builder.alg_count} "
        f"| Inline citations={len(builder.inline_citations)}/32"
    )

    if args.word_update:
        qa_dir = args.qa_pdf_dir
        if qa_dir is None:
            qa_dir = Path(os.environ.get("TEMP", str(ROOT))) / "fedgraph_docx_qa_v2"
        stats = update_fields_via_word_com(out, qa_pdf_dir=qa_dir)
        print(f"Word COM + Post-save XML stats: {stats}")


if __name__ == "__main__":
    main()
