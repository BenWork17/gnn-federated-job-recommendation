"""
Dựng báo cáo .docx từ template PBL6 của khoa + số liệu trong results/*.json.

NGUYÊN TẮC: không có con số nào được gõ tay trong file này.
Mọi giá trị đều đọc từ results/reco_main.json và artifacts/medajob/meta.json.
Cuối mỗi lần dựng, hàm verify_numbers() kiểm tra các số quan trọng
xuất hiện đúng trong tài liệu; lệch là báo lỗi ngay.

Cấu trúc giữ nguyên bìa và style của template; phần thân được viết lại cho
đề tài này. Mục lục là field thật + bật updateFields để Word tự cập nhật.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common import ROOT, banner, load_config, load_json, setup_console, step

FIG_DIR = None
CFG = None


# =====================================================================
# Tiện ích XML
# =====================================================================
def _add_field(paragraph, instr: str, placeholder: str = "") -> None:
    """Chèn field Word (PAGE, TOC, ...) vào một paragraph."""
    run = paragraph.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instr)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = placeholder
    r.append(t)
    fld.append(r)
    run._r.addnext(fld)


def _enable_update_fields(doc: Document) -> None:
    """Bật để Word cập nhật mọi field (mục lục, số trang) khi mở file."""
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        el = OxmlElement("w:updateFields")
        el.set(qn("w:val"), "true")
        settings.append(el)


def _set_cell_shading(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _repeat_header(row) -> None:
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


# =====================================================================
# Lớp dựng tài liệu
# =====================================================================
class Report:
    def __init__(self, template: Path, fig_dir: Path, fig_width_cm: float = 16.4):
        self.doc = Document(str(template))
        self.fig_dir = Path(fig_dir)
        self.fig_width_cm = float(fig_width_cm)
        self.fig_no = 0
        self.tab_no = 0
        self.figures: list[str] = []
        self.tables: list[str] = []

    # --- dọn thân, giữ bìa -------------------------------------------
    def reset_body(self) -> None:
        """Giữ bìa (tới section break đầu tiên), xoá phần thân cũ."""
        body = self.doc.element.body
        children = list(body.iterchildren())

        # tìm đoạn kết thúc bìa: paragraph có pPr/sectPr
        cover_end = None
        for i, ch in enumerate(children):
            pPr = ch.find(qn("w:pPr"))
            if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
                cover_end = i
                break
        if cover_end is None:
            raise RuntimeError("Không tìm thấy section break của trang bìa")

        # giữ 0..cover_end và sectPr cuối body
        keep_head = children[: cover_end + 1]
        final_sect = children[-1] if children[-1].tag == qn("w:sectPr") else None
        for ch in children[cover_end + 1:]:
            if ch is final_sect:
                continue
            body.remove(ch)

        # sao lưu danh sách để dùng lại nếu cần
        self._cover = keep_head
        self._final_sect = final_sect

        # xoá header/footer của các section phía sau (đang gắn «i», «3»…)
        for sect in self.doc.sections[1:]:
            for part in (sect.header, sect.footer):
                for p in part.paragraphs:
                    for r in list(p.runs):
                        r._r.getparent().remove(r._r)

    # --- sửa bìa ------------------------------------------------------
    def fill_cover(self, title: str, subtitle: str, students: list[str],
                   course: str, year: str = "2026") -> None:
        paras = self.doc.paragraphs
        for p in paras:
            t = p.text.strip()
            if t == "PBL6: DỰ ÁN CHUYÊN NGÀNH":
                p.text = course
            elif t.startswith("BÁO CÁO PHÂN TÍCH MÔ HÌNH"):
                self._replace_keep_format(p, title)
            elif "Convolutional Matrix Factorization" in t:
                self._replace_keep_format(p, subtitle)
            elif t.startswith("Đà Nẵng,"):
                self._replace_keep_format(p, f"Đà Nẵng, {year}")

        # điền tên sinh viên vào dòng "Sinh viên: ......"
        for p in paras:
            if p.text.strip().startswith("Sinh viên:"):
                self._replace_keep_format(
                    p,
                    f"Sinh viên: {students[0]}          LỚP: 22NH15")
                if len(students) > 1:
                    new_p = copy.deepcopy(p._p)
                    p._p.addnext(new_p)
                    from docx.text.paragraph import Paragraph
                    np = Paragraph(new_p, p._parent)
                    self._replace_keep_format(np, f"Sinh viên: {students[1]}")
                break

    @staticmethod
    def _replace_keep_format(paragraph, text: str) -> None:
        """Thay chữ nhưng giữ định dạng của run đầu tiên."""
        if paragraph.runs:
            paragraph.runs[0].text = text
            for r in paragraph.runs[1:]:
                r.text = ""
        else:
            paragraph.add_run(text)

    # --- khối văn bản -------------------------------------------------
    def h1(self, text: str) -> None:
        self.doc.add_heading(text, level=1)

    def h2(self, text: str) -> None:
        self.doc.add_heading(text, level=2)

    def p(self, text: str, style: str = "0-NDUNG") -> None:
        para = self.doc.add_paragraph(style=style)
        self._rich(para, text)

    @staticmethod
    def _rich(para, text: str) -> None:
        """Hỗ trợ **đậm** và *nghiêng* đơn giản trong chuỗi."""
        import re

        tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text)
        for tok in tokens:
            if not tok:
                continue
            if tok.startswith("**") and tok.endswith("**"):
                para.add_run(tok[2:-2]).bold = True
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                para.add_run(tok[1:-1]).italic = True
            else:
                para.add_run(tok)

    def bullets(self, items: list[str]) -> None:
        for it in items:
            self.p("• " + it, style="0-NDUNG")

    def formula(self, text: str) -> None:
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(text)
        run.font.name = "Consolas"
        run.font.size = Pt(11)

    def code(self, text: str) -> None:
        for line in text.strip("\n").split("\n"):
            para = self.doc.add_paragraph()
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.space_before = Pt(0)
            run = para.add_run(line if line else " ")
            run.font.name = "Consolas"
            run.font.size = Pt(9)

    def figure(self, filename: str, caption: str, width_cm: float | None = None):
        path = self.fig_dir / filename
        if not path.exists():
            self.p(f"[Thiếu hình: {filename}]")
            return
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(6)
        para.add_run().add_picture(
            str(path), width=Cm(width_cm or self.fig_width_cm))
        self.fig_no += 1
        cap = self.doc.add_paragraph(
            f"Hình {self.fig_no}. {caption}", style="4-HINH")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.figures.append(f"Hình {self.fig_no}. {caption}")

    def table(self, df: pd.DataFrame, caption: str, widths: list[float] | None = None,
              font_size: float = 10.0) -> None:
        self.tab_no += 1
        cap = self.doc.add_paragraph(
            f"Bảng {self.tab_no}. {caption}", style="6-BANG")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

        table = self.doc.add_table(rows=1, cols=len(df.columns))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        header = table.rows[0]
        _repeat_header(header)
        for j, col in enumerate(df.columns):
            cell = header.cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(col))
            run.bold = True
            run.font.size = Pt(font_size)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_cell_shading(cell, "DCE6F1")

        for i, row in df.iterrows():
            cells = table.add_row().cells
            for j, val in enumerate(row):
                cells[j].text = ""
                run = cells[j].paragraphs[0].add_run(str(val))
                run.font.size = Pt(font_size)
                cells[j].paragraphs[0].alignment = (
                    WD_ALIGN_PARAGRAPH.LEFT if j == 0
                    else WD_ALIGN_PARAGRAPH.CENTER)

        if widths:
            for j, w in enumerate(widths):
                for row in table.rows:
                    row.cells[j].width = Cm(w)
        self.tables.append(f"Bảng {self.tab_no}. {caption}")
        self.doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # --- mục lục -------------------------------------------------------
    def toc(self) -> None:
        heading = self.doc.add_paragraph("MỤC LỤC", style="Title")
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para = self.doc.add_paragraph()
        run = para.add_run()
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), 'TOC \\o "1-2" \\h \\z \\u')
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = "Nhấn chuột phải → Update Field để hiện mục lục."
        r.append(t)
        fld.append(r)
        run._r.addnext(fld)
        self.doc.add_page_break()

    def page_number_footer(self) -> None:
        """Đánh số trang ở giữa chân trang cho section hiện tại."""
        section = self.doc.sections[-1]
        footer = section.footer
        para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in list(para.runs):
            r._r.getparent().remove(r._r)
        self._page_field(para)

    @staticmethod
    def _page_field(paragraph) -> None:
        run = paragraph.add_run()
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = " PAGE "
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        txt = OxmlElement("w:t")
        txt.text = "1"
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        for el in (fld_begin, instr, fld_sep, txt, fld_end):
            run._r.append(el)

    def save(self, path: Path) -> Path:
        _enable_update_fields(self.doc)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(path))
        return path
