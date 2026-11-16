import io
import math
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from due_date_report import DueDateReportBuilder

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


HEADERS = ["Subject Name", "Staff Name", "Type", "Uploaded Title", "Problem", "Expected Format"]
_FIELDS = ["subject", "staff_name", "kind", "title", "problem", "expected"]
_XLSX_WIDTHS = [30, 22, 12, 36, 34, 34]
_PDF_WEIGHTS = [1.5, 1.2, 0.8, 2.0, 1.8, 1.7]


class NamingReportBuilder:
    """
    Naming-mismatch report from naming_checker.find_mismatches() rows.
    Grouped by DEPARTMENT (one Excel sheet / PDF section each), and
    inside it one table per course (year + class name).
    Excel via build_xlsx, portrait A4 PDF via build_pdf.
    """

    @staticmethod
    def _blocks(rows):
        """{department: [ {title, rows:[[cells...]]} per course ]}"""
        grouped = {}
        for r in rows:
            key = (r["department"], r["year"], r["class_name"])
            grouped.setdefault(key, []).append([r[f] for f in _FIELDS])

        departments = {}
        for (department, year, class_name) in sorted(grouped):
            departments.setdefault(department, []).append({
                "title": f"{department}  |  Year {year}  |  {class_name}",
                "rows": grouped[(department, year, class_name)],
            })
        return departments

    @staticmethod
    def build_xlsx(rows):
        departments = NamingReportBuilder._blocks(rows)

        workbook = Workbook()
        workbook.remove(workbook.active)

        side = Side(style="thin", color="999999")
        border = Border(left=side, right=side, top=side, bottom=side)
        fill = PatternFill("solid", fgColor="F8CBAD")
        wrap_top = Alignment(wrap_text=True, vertical="top")

        used = set()
        for department, blocks in departments.items():
            sheet = workbook.create_sheet(
                title=DueDateReportBuilder._sheet_name(department, used)
            )
            for col, width in enumerate(_XLSX_WIDTHS, start=1):
                sheet.column_dimensions[sheet.cell(row=1, column=col).column_letter].width = width

            row_idx = 1
            for block in blocks:
                title = sheet.cell(row=row_idx, column=1, value=block["title"])
                title.font = Font(bold=True, size=12)
                sheet.merge_cells(start_row=row_idx, start_column=1,
                                  end_row=row_idx, end_column=len(HEADERS))
                row_idx += 1

                for col, text in enumerate(HEADERS, start=1):
                    cell = sheet.cell(row=row_idx, column=col, value=text)
                    cell.font = Font(bold=True)
                    cell.fill = fill
                    cell.border = border
                row_idx += 1

                for data in block["rows"]:
                    max_lines = 1
                    for col, text in enumerate(data, start=1):
                        cell = sheet.cell(row=row_idx, column=col, value=text)
                        cell.alignment = wrap_top
                        cell.border = border
                        per_line = _XLSX_WIDTHS[col - 1]
                        max_lines = max(max_lines, math.ceil(max(len(str(text)), 1) / per_line))
                    sheet.row_dimensions[row_idx].height = max(15, 13.5 * max_lines)
                    row_idx += 1
                row_idx += 1  # blank row between courses

        if not workbook.sheetnames:
            sheet = workbook.create_sheet(title="No Data")
            sheet.append(["No naming mismatches found."])

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def build_pdf(rows):
        

        departments = NamingReportBuilder._blocks(rows)

        heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12, leading=15)
        dept_style = ParagraphStyle("dept", fontName="Helvetica-Bold", fontSize=10, leading=13)
        title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=9, leading=11)
        head_cell = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=6.5, leading=8)
        body_cell = ParagraphStyle("body", fontName="Helvetica", fontSize=6.5, leading=8)
        plain = ParagraphStyle("plain", fontName="Helvetica", fontSize=9, leading=12)

        margin = 10 * mm
        usable = A4[0] - 2 * margin
        total = sum(_PDF_WEIGHTS)
        col_widths = [usable * w / total for w in _PDF_WEIGHTS]

        def para(text, style):
            return Paragraph("<br/>".join(escape(line) for line in str(text).split("\n")), style)

        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.drawRightString(A4[0] - margin, 6 * mm, f"Page {doc.page}")
            canvas.restoreState()

        story = [Paragraph("Naming Mismatch Report", heading), Spacer(1, 4 * mm)]
        if not departments:
            story.append(Paragraph("No naming mismatches found.", plain))

        first = True
        for department, blocks in departments.items():
            if not first:
                story.append(PageBreak())
            first = False
            story.append(Paragraph(f"Department: {escape(department)}", dept_style))
            story.append(Spacer(1, 3 * mm))

            for block in blocks:
                data = [[para(h, head_cell) for h in HEADERS]]
                data += [[para(cell, body_cell) for cell in row] for row in block["rows"]]

                table = Table(data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8CBAD")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(Paragraph(escape(block["title"]), title_style))
                story.append(Spacer(1, 2 * mm))
                story.append(table)
                story.append(Spacer(1, 6 * mm))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=12 * mm,
            title="Naming Mismatch Report",
        )
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        buffer.seek(0)
        return buffer