import io
import math
import re
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from material_classifier import QA_MARKER_PATTERN, QUESTIONS_WORD_PATTERN, detect_notes, detect_qa
from requirement_engine import RequirementEngine
from academic_schedule_manager import AcademicScheduleManager

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# Class names carry a trailing batch-year range, e.g.
# "IV-Yr VII-Sem AI&DS A (2023-2027)". Excel sheet names max out at
# 31 characters, so the range is dropped from the SHEET NAME only.
_BATCH_SUFFIX = re.compile(r"\s*\(\s*\d{4}\s*-\s*\d{4}\s*\)\s*$")

VALID_STATUSES = ("Pending", "Completed")

MAIN_HEADERS = {
    "Completed": [
        "Subject Name", "Staff Name", "Unit to Upload", "Unit Found",
        "Assignment to Upload", "Assignment Found",
    ],
    "Pending": [
        "Subject Name", "Staff Name", "Unit Uploaded", "Unit Pending",
        "Assignment Uploaded", "Assignment Pending",
    ],
}

# Excel column widths (first 6 columns; any further QA part columns get 24).
_XLSX_WIDTHS = [30, 24, 24, 24, 22, 22]
# PDF column weights for the 6 main columns.
_PDF_WEIGHTS = [1.6, 1.2, 1.1, 1.1, 1.1, 1.1]

_HEAD_BLUE = "D9E1F2"
_HEAD_GREEN = "E2EFDA"


# ---- reading units / QA out of a Classroom item ---------------------
# All of this goes through material_classifier.py, so the report reads
# a title exactly the way the classifier did when it filed the upload.
def _notes_unit(item):
    title = str(item.get("title") or item.get("unit") or "")
    found, label = detect_notes(title)
    match = re.match(r"Unit (\d+)$", label) if found else None
    return int(match.group(1)) if match else None


def _qa_info(item):
    """
    (unit number or None, part letter or "", type, display word) for a
    QA item, or None if it isn't QA. Works whether the item is stored
    already classified (unit / part / type) or only as a title.
    """
    if item.get("type") or item.get("unit"):
        info = {
            "unit": str(item.get("unit") or ""),
            "part": str(item.get("part") or ""),
            "type": str(item.get("type") or "Q&A"),
        }
    else:
        found, info = detect_qa(str(item.get("title") or ""))
        if not found:
            return None

    digits = re.search(r"(\d+)", info.get("unit", ""))
    unit = int(digits.group(1)) if digits else None
    part = re.sub(r"(?i)^part[\s\-]*", "", info.get("part", "")).strip().upper()
    qtype = info.get("type") or "Q&A"

    # "Questions" is the same slot as "Q&A" for the classifier, but show
    # the word the teacher actually used when the title is available.
    word = qtype
    lower = str(item.get("title") or "").lower()
    if lower and QUESTIONS_WORD_PATTERN.search(lower) and not QA_MARKER_PATTERN.search(lower):
        word = "MCQ Questions" if qtype.startswith("MCQ") else "Questions"

    return unit, part, qtype, word


def _numbered(materials, prefix):
    """["Unit 2", "Unit 1"] -> ["unit-1", "unit-2"] (assignment-N likewise)."""
    numbers = set()
    other = []
    for material in materials or []:
        match = re.search(r"(\d+)", str(material))
        if match:
            numbers.add(int(match.group(1)))
        else:
            other.append(str(material))
    return [f"{prefix}-{n}" for n in sorted(numbers)] + other


def _lines(values):
    values = list(values)
    return "\n".join(values) if values else "-"


class DueDateReportBuilder:
    """
    Builds the dean-facing upload report, one document per status
    (Pending / Completed), as Excel (build) or portrait PDF
    (build_pdf), both from the same data.

    One Excel sheet / PDF section per course; inside it one group per
    due date; inside that, one small two-part card per subject:

      Completed
        Subject Name | Staff Name | Unit to Upload | Unit Found |
          Assignment to Upload | Assignment Found
        <values; units one per line>
        QA to Upload | Part-A Found | Part-B Found | Part-C Found
        <values; one item per line>

      Pending
        Subject Name | Staff Name | Unit Uploaded | Unit Pending |
          Assignment Uploaded | Assignment Pending
        <values>
        QA to Upload | Part-A Pending | Part-B Pending | Part-C Pending
        <values>

    Parts come from the regulation. Whether a subject is Pending or
    Completed — and its uploaded / pending lists — come from
    RequirementEngine, so a row can't disagree with that decision.
    """

    # ------------------------------------------------------------
    # Data
    # ------------------------------------------------------------
    @staticmethod
    def _qa_headers(status, part_names):
        if status == "Completed":
            return ["QA to Upload"] + [f"Part-{p} Found" for p in part_names] + ["QA Found (No Part)"]
        return ["QA to Upload"] + [f"Part-{p} Pending" for p in part_names]

    @staticmethod
    def _row(status, record, entry, part_types, result):
        """
        Returns (main_row, qa_row) for one subject.
        part_types: {"A": "Q&A", "C": "MCQ Q&A", ...} from the regulation.
        """
        notes = record.get("notes", [])
        assignments = record.get("assignments", [])
        qa = record.get("qa", [])

        req_notes = sorted({int(n) for n in entry.get("notes_required_units") or []})
        req_qa = sorted({int(n) for n in entry.get("qa_required_units") or []})

        subject = record.get("subject", "")
        staff = record.get("staff_name", "")
        qa_to_upload = _lines(f"unit-{n}" for n in req_qa)

        if status == "Completed":
            a = result["assignments"]
            total = a["uploaded_count"] + a["pending_count"]
            assignment_to_upload = f"{a['uploaded_count']}/{total}" if total else "-"

            notes_found = {n for n in (_notes_unit(i) for i in notes) if n is not None}

            # Every QA upload, listed under its part.
            labels = {part: set() for part in part_types}
            no_part_labels = set()
            for item in qa:
                info = _qa_info(item)
                if info is None:
                    continue
                unit, part, _qtype, word = info
                if unit is not None:
                    label = f"unit-{unit} {word}"
                else:
                    label = str(item.get("title") or item.get("unit") or word)
                sort_key = unit if unit is not None else 10 ** 6
                if part in labels:
                    labels[part].add((sort_key, label))
                elif not part:
                    no_part_labels.add((sort_key, label))

            main = [
                subject,
                staff,
                _lines(f"unit-{n}" for n in req_notes),
                _lines(f"unit-{n}" for n in sorted(notes_found)),
                assignment_to_upload,
                str(len(assignments)) if assignments else "-",
            ]
            qa_row = [qa_to_upload]
            for part in part_types:
                qa_row.append(_lines(label for _, label in sorted(labels[part])))
            qa_row.append(_lines(label for _, label in sorted(no_part_labels)))
            return main, qa_row

        # Pending: required items only, as the engine counted them.
        pending_by_part = {part: set() for part in part_types}
        for key in result["qa"].get("pending_materials", []):
            match = re.match(r"Unit-(\d+) Part-([A-Za-z0-9]+)", str(key))
            if match and match.group(2).upper() in pending_by_part:
                pending_by_part[match.group(2).upper()].add(int(match.group(1)))

        main = [
            subject,
            staff,
            _lines(_numbered(result["notes"].get("uploaded_materials"), "unit")),
            _lines(_numbered(result["notes"].get("pending_materials"), "unit")),
            _lines(_numbered(result["assignments"].get("uploaded_materials"), "assignment")),
            _lines(_numbered(result["assignments"].get("pending_materials"), "assignment")),
        ]
        qa_row = [qa_to_upload]
        for part in part_types:
            qa_row.append(_lines(f"unit-{n}" for n in sorted(pending_by_part[part])))
        return main, qa_row

    @staticmethod
    def _blocks(records_by_pair, regulation, entries, status):
        """
        Returns table blocks ordered by course then due date:
        {"class_name", "due_date", "regulation", "main_headers",
         "qa_headers", "subjects": [{"main": [...], "qa": [...]}]}
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}, got {status!r}")

        qa_parts = regulation.get("qa_parts", [])
        part_types = {}
        for p in qa_parts:
            name = str(p.get("part", "")).strip().upper()
            if name and name not in part_types:
                part_types[name] = str(p.get("type") or "Q&A")

        grouped = {}

        for entry in entries:
            due_date = entry.get("date")

            for pair in AcademicScheduleManager.pairs_of(entry):
                for record in records_by_pair.get(pair, []):
                    req = {
                        "year": record.get("year"),
                        "department": record.get("department"),
                        "semester": record.get("semester"),
                        "section": record.get("section"),
                        "subject": record.get("subject"),
                        "regulation": entry.get("regulation"),
                        "notes_required_units": entry.get("notes_required_units", []),
                        "assignment_required_units": entry.get("assignment_required_units", []),
                        "qa_required_units": entry.get("qa_required_units", []),
                        "due_date": due_date,
                    }

                    result = RequirementEngine.evaluate(
                        req, qa_parts, due_date,
                        record.get("notes", []),
                        record.get("assignments", []),
                        record.get("qa", []),
                    )
                    if result["status"] != status:
                        continue

                    key = (record.get("class_name") or "Unknown", due_date or "-")
                    grouped.setdefault(key, []).append(
                        DueDateReportBuilder._row(status, record, entry, part_types, result)
                    )

        blocks = []
        for (class_name, due_date) in sorted(grouped):
            pairs = sorted(grouped[(class_name, due_date)], key=lambda r: r[0][0].lower())
            qa_headers = DueDateReportBuilder._qa_headers(status, list(part_types))

            # Completed only: drop the "QA Found (No Part)" column when
            # none of this group's subjects has such an upload.
            if status == "Completed" and all(qa[-1] == "-" for _, qa in pairs):
                qa_headers = qa_headers[:-1]
                pairs = [(main, qa[:-1]) for main, qa in pairs]

            blocks.append({
                "class_name": class_name,
                "due_date": due_date,
                "regulation": regulation.get("name") or "",
                "main_headers": MAIN_HEADERS[status],
                "qa_headers": qa_headers,
                "subjects": [{"main": main, "qa": qa} for main, qa in pairs],
            })
        return blocks

    @staticmethod
    def _title(block):
        return (
            f"{block['class_name']}  |  Regulation {block['regulation']}  |  "
            f"Due date: {block['due_date']}"
        )

    # ------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------
    @staticmethod
    def _sheet_name(class_name: str, used: set) -> str:
        """
        A valid, unique Excel sheet name for a course: batch-year
        suffix dropped, forbidden characters ([]:*?/\\) replaced,
        capped at 31 characters, and de-duplicated case-insensitively.
        """
        name = _BATCH_SUFFIX.sub("", class_name or "").strip()
        for ch in "[]:*?/\\":
            name = name.replace(ch, "-")
        name = name.strip("'") or "Course"

        base = name[:31]
        candidate = base
        counter = 2
        while candidate.lower() in used:
            suffix = f" ({counter})"
            candidate = base[: 31 - len(suffix)] + suffix
            counter += 1

        used.add(candidate.lower())
        return candidate

    @staticmethod
    def build(records_by_pair, regulation, entries, status):
        """Returns a BytesIO of ONE .xlsx workbook for `status`."""
        blocks = DueDateReportBuilder._blocks(records_by_pair, regulation, entries, status)

        workbook = Workbook()
        workbook.remove(workbook.active)  # drop the default blank sheet

        side = Side(style="thin", color="999999")
        border = Border(left=side, right=side, top=side, bottom=side)
        blue = PatternFill("solid", fgColor=_HEAD_BLUE)
        green = PatternFill("solid", fgColor=_HEAD_GREEN)
        wrap_top = Alignment(wrap_text=True, vertical="top")
        wrap_mid = Alignment(wrap_text=True, vertical="center")

        used_names: set = set()
        sheets = {}
        next_row = {}

        def write_row(sheet, row_idx, cells, widths, fills=None):
            """fills: None for a body row, or a list with one PatternFill per column."""
            max_lines = 1
            for col, text in enumerate(cells, start=1):
                cell = sheet.cell(row=row_idx, column=col, value=text)
                cell.border = border
                if fills is not None:
                    cell.fill = fills[col - 1]
                    cell.font = Font(bold=True)
                    cell.alignment = wrap_mid
                else:
                    cell.alignment = wrap_top
                per_line = max(int(widths[col - 1]), 1)
                lines = sum(
                    max(1, math.ceil(len(line) / per_line))
                    for line in str(text).split("\n")
                )
                max_lines = max(max_lines, lines)
            sheet.row_dimensions[row_idx].height = max(15, 13.5 * max_lines)
            return row_idx + 1

        for block in blocks:
            class_name = block["class_name"]
            if class_name not in sheets:
                sheets[class_name] = workbook.create_sheet(
                    title=DueDateReportBuilder._sheet_name(class_name, used_names)
                )
                next_row[class_name] = 1
            sheet = sheets[class_name]
            row_idx = next_row[class_name]

            # ONE header row = main headers + QA headers
            headers = list(block["main_headers"]) + list(block["qa_headers"])
            header_fills = (
                [blue] * len(block["main_headers"]) + [green] * len(block["qa_headers"])
            )
            max_cols = len(headers)

            widths = [
                _XLSX_WIDTHS[i] if i < len(_XLSX_WIDTHS) else 16
                for i in range(max_cols)
            ]
            for col, width in enumerate(widths, start=1):
                sheet.column_dimensions[get_column_letter(col)].width = width

            # Title row
            title = sheet.cell(row=row_idx, column=1, value=DueDateReportBuilder._title(block))
            title.font = Font(bold=True, size=12)
            sheet.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=max_cols)
            row_idx += 2  # blank row under the title

            row_idx = write_row(sheet, row_idx, headers, widths, header_fills)

            # One row per subject: main columns followed by QA columns.
            for subject in block["subjects"]:
                row_idx = write_row(sheet, row_idx, list(subject["main"]) + list(subject["qa"]), widths)

            next_row[class_name] = row_idx + 1  # blank row before the next block on this sheet

        if not workbook.sheetnames:
            sheet = workbook.create_sheet(title="No Data")
            sheet.append([f"No subjects are currently {status.lower()}."])

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer

    # ------------------------------------------------------------
    # PDF (A4 portrait)
    # ------------------------------------------------------------
    @staticmethod
    def build_pdf(records_by_pair, regulation, entries, status):
        blocks = DueDateReportBuilder._blocks(records_by_pair, regulation, entries, status)

        heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12, leading=15)
        title_style = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=9, leading=11)
        head_cell = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=7, leading=8.5)
        body_cell = ParagraphStyle("body", fontName="Helvetica", fontSize=7, leading=8.5)
        plain = ParagraphStyle("plain", fontName="Helvetica", fontSize=9, leading=12)

        margin = 10 * mm
        usable = A4[0] - 2 * margin

        def para(text, style):
            return Paragraph("<br/>".join(escape(line) for line in str(text).split("\n")), style)

        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.drawRightString(A4[0] - margin, 6 * mm, f"Page {doc.page}")
            canvas.restoreState()

        story = [Paragraph(f"Due Date Report - {status}", heading), Spacer(1, 4 * mm)]

        if not blocks:
            story.append(Paragraph(f"No subjects are currently {status.lower()}.", plain))

        previous_class = None
        for block in blocks:
            if previous_class is not None and block["class_name"] != previous_class:
                story.append(PageBreak())
            previous_class = block["class_name"]

            story.append(Paragraph(escape(DueDateReportBuilder._title(block)), title_style))
            story.append(Spacer(1, 2 * mm))

            if not block["subjects"]:
                continue

            # ONE header row = main headers + QA headers
            headers = list(block["main_headers"]) + list(block["qa_headers"])
            n_main = len(block["main_headers"])
            n_cols = len(headers)

            weights = [
                _PDF_WEIGHTS[i] if i < len(_PDF_WEIGHTS) else 1.4
                for i in range(n_cols)
            ]
            col_widths = [usable * w / sum(weights) for w in weights]

            data = [[para(h, head_cell) for h in headers]]
            for subject in block["subjects"]:
                row = list(subject["main"]) + list(subject["qa"])
                data.append([para(v, body_cell) for v in row])

            t = Table(data, colWidths=col_widths, repeatRows=1)  # header repeats on page breaks
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 0), (n_main - 1, 0), colors.HexColor("#" + _HEAD_BLUE)),
                ("BACKGROUND", (n_main, 0), (-1, 0), colors.HexColor("#" + _HEAD_GREEN)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=12 * mm,
            title=f"Due Date Report - {status}",
        )
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        buffer.seek(0)
        return buffer