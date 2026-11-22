import io
import re
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_BATCH_SUFFIX = re.compile(r"\s*\(.*\)\s*$")


def _clean(value) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def parse_course_name(name: str):
    """
    "IV-Yr VII-Sem AI&DS A (2023-2027)" -> ("IV", "AI&DS", "A")
    "I-Year I-SEM MBA C"                -> ("I", "MBA", "C")

    Returns None when the name doesn't follow the
    "<year> <semester> <department> <section>" pattern.
    """
    text = _BATCH_SUFFIX.sub("", str(name or "")).upper().strip()
    tokens = text.split()
    if len(tokens) < 4:
        return None

    year = re.sub(r"-?(YEAR|YR)$", "", tokens[0])

    sem_index = next((i for i, t in enumerate(tokens) if "SEM" in t), None)
    if sem_index is None or sem_index + 1 >= len(tokens) - 1:
        return None

    department = _clean("".join(tokens[sem_index + 1:-1]))
    section = tokens[-1]

    if not year or not department or not section:
        return None
    return year, department, section


def check(course_names, departments) -> dict:
    """
    course_names: every course name currently in Google Classroom.
    departments:  registry entries - [{"name", "years", "sections"}].

    Expected classes are every Year x Section of every registered
    department. Each is marked Available (with the matching Classroom
    course name(s)) or Missing. Courses that match no expected class
    - unregistered department, unknown section, unparsable name - are
    returned separately so nothing in Classroom is silently ignored.
    """
    found = {}
    for course_name in course_names:
        parsed = parse_course_name(course_name)
        if parsed:
            found.setdefault(parsed, []).append(course_name)

    expected_keys = set()
    department_rows = []
    total_available = 0
    total_missing = 0

    for dept in departments:
        key_name = _clean(dept["name"])
        classes = []

        for year in dept["years"]:
            for section in dept["sections"]:
                key = (str(year).upper(), key_name, str(section).upper())
                expected_keys.add(key)
                names = found.get(key, [])
                classes.append({
                    "year": key[0],
                    "section": key[2],
                    "status": "Available" if names else "Missing",
                    "course_names": names,
                })

        available = sum(1 for c in classes if c["status"] == "Available")
        total_available += available
        total_missing += len(classes) - available

        department_rows.append({
            "name": dept["name"],
            "expected": len(classes),
            "available": available,
            "missing": len(classes) - available,
            "classes": classes,
        })

    unrecognised = []
    for course_name in course_names:
        parsed = parse_course_name(course_name)
        if parsed is None or parsed not in expected_keys:
            unrecognised.append(course_name)

    return {
        "generated_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "summary": {
            "expected": total_available + total_missing,
            "available": total_available,
            "missing": total_missing,
        },
        "departments": department_rows,
        "unrecognised": sorted(unrecognised),
    }


def build_pdf(result: dict) -> io.BytesIO:
    """Renders check()'s result as an A4 PDF; returns a BytesIO."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Google Classroom - Class Availability",
    )

    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5, leading=11)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    green = colors.Color(0.10, 0.55, 0.25)
    red = colors.Color(0.80, 0.15, 0.15)

    summary = result["summary"]
    story = [
        Paragraph("Google Classroom - Class Availability", styles["Title"]),
        Paragraph(f"Generated {escape(result['generated_at'])}", small),
        Spacer(1, 6),
        Paragraph(
            f"<b>{summary['expected']}</b> expected classes: "
            f"<font color='#1a8c40'><b>{summary['available']}</b> available</font>, "
            f"<font color='#cc2626'><b>{summary['missing']}</b> missing</font>.",
            styles["Normal"],
        ),
        Spacer(1, 10),
    ]

    for dept in result["departments"]:
        story.append(Paragraph(
            f"{escape(dept['name'])} &nbsp; "
            f"<font size=9 color='#666666'>{dept['available']} of {dept['expected']} available</font>",
            styles["Heading3"],
        ))

        rows = [["Year", "Section", "Status", "Classroom course"]]
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.25, 0.28, 0.55)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        for i, c in enumerate(dept["classes"], start=1):
            is_available = c["status"] == "Available"
            rows.append([
                c["year"],
                c["section"],
                c["status"],
                Paragraph(escape("; ".join(c["course_names"])) or "-", cell),
            ])
            style_cmds.append(("TEXTCOLOR", (2, i), (2, i), green if is_available else red))
            style_cmds.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
            if not is_available:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.Color(1, 0.93, 0.93)))

        table = Table(rows, colWidths=[18 * mm, 22 * mm, 26 * mm, 108 * mm], repeatRows=1)
        table.setStyle(TableStyle(style_cmds))
        story.extend([table, Spacer(1, 10)])

    if result["unrecognised"]:
        story.append(Paragraph("In Classroom but not matched to a registered class", styles["Heading3"]))
        story.append(Paragraph(
            "Unregistered department, a section/year not set up for the department, "
            "or a name that doesn't follow the usual pattern.", small))
        story.append(Spacer(1, 4))
        for name in result["unrecognised"]:
            story.append(Paragraph(f"&bull; {escape(name)}", cell))

    doc.build(story)
    buffer.seek(0)
    return buffer


def missing_list(result: dict) -> list:
    """Flat list of the classes that are not in Google Classroom:
    [{"department", "year", "section"}, ...]"""
    return [
        {"department": dept["name"], "year": c["year"], "section": c["section"]}
        for dept in result["departments"]
        for c in dept["classes"]
        if c["status"] == "Missing"
    ]


def build_missing_pdf(result: dict, scope_label: str = "", problems=None) -> io.BytesIO:
    """
    A PDF listing ONLY the classes that are not in Google Classroom,
    grouped by department. `scope_label` describes what was checked.
    `problems` (optional) lists rows of an uploaded file that couldn't
    be read, so nothing is skipped silently.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Classes Not Found in Google Classroom",
    )

    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    red = colors.Color(0.80, 0.15, 0.15)

    missing = missing_list(result)

    story = [
        Paragraph("Classes Not Found in Google Classroom", styles["Title"]),
        Paragraph(f"Generated {escape(result['generated_at'])}", small),
    ]
    if scope_label:
        story.append(Paragraph(f"Checked: {escape(scope_label)}", small))
    story.append(Spacer(1, 8))

    if not missing:
        story.append(Paragraph(
            "<font color='#1a8c40'><b>All classes in this selection are available "
            "in Google Classroom.</b></font>", styles["Normal"]))
    else:
        by_department = {}
        for item in missing:
            by_department.setdefault(item["department"], []).append(item)

        for department, items in by_department.items():
            story.append(Paragraph(escape(department), styles["Heading3"]))

            rows = [["Year", "Section", "Class"]]
            for item in items:
                rows.append([item["year"], item["section"],
                             f"{item['year']} year - {department} - Section {item['section']}"])

            table = Table(rows, colWidths=[24 * mm, 28 * mm, 122 * mm], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.25, 0.28, 0.55)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 1), (-1, -1), red),
                ("BACKGROUND", (0, 1), (-1, -1), colors.Color(1, 0.95, 0.95)),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ]))
            story.extend([table, Spacer(1, 10)])

    if problems:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Rows in the list that could not be read", styles["Heading3"]))
        for line in problems:
            story.append(Paragraph(f"&bull; {escape(line)}", small))

    doc.build(story)
    buffer.seek(0)
    return buffer


def available_list(result: dict) -> list:
    """Flat list of the classes that ARE in Google Classroom:
    [{"department", "year", "section", "course_names": [...]}, ...]"""
    return [
        {
            "department": dept["name"],
            "year": c["year"],
            "section": c["section"],
            "course_names": c["course_names"],
        }
        for dept in result["departments"]
        for c in dept["classes"]
        if c["status"] == "Available"
    ]


def build_available_pdf(result: dict, scope_label: str = "") -> io.BytesIO:
    """
    A PDF listing ONLY the classes that exist in Google Classroom,
    grouped by department, with the matching Classroom course name.
    `scope_label` describes what was checked, e.g.
    "Year: III | Department: All | Section: A".
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Classes Available in Google Classroom",
    )

    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5, leading=11)
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    green = colors.Color(0.10, 0.55, 0.25)

    available = available_list(result)

    story = [
        Paragraph("Classes Available in Google Classroom", styles["Title"]),
        Paragraph(f"Generated {escape(result['generated_at'])}", small),
    ]
    if scope_label:
        story.append(Paragraph(f"Checked: {escape(scope_label)}", small))
    story.append(Spacer(1, 8))

    if not available:
        story.append(Paragraph(
            "<font color='#cc2626'><b>No classes in this selection were found "
            "in Google Classroom.</b></font>", styles["Normal"]))
        doc.build(story)
        buffer.seek(0)
        return buffer

    by_department = {}
    for item in available:
        by_department.setdefault(item["department"], []).append(item)

    for department, items in by_department.items():
        story.append(Paragraph(escape(department), styles["Heading3"]))

        rows = [["Year", "Section", "Classroom course"]]
        for item in items:
            rows.append([
                item["year"],
                item["section"],
                Paragraph(escape("; ".join(item["course_names"])) or "-", cell),
            ])

        table = Table(rows, colWidths=[24 * mm, 28 * mm, 122 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.25, 0.28, 0.55)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 1), (1, -1), green),
            ("BACKGROUND", (0, 1), (-1, -1), colors.Color(0.94, 0.99, 0.95)),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.extend([table, Spacer(1, 10)])

    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------
# Uploaded class list: match an exact list of classes against Classroom
# ---------------------------------------------------------------------
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_YEAR_WORD = re.compile(r"^(X|IX|VIII|VII|VI|V|IV|III|II|I)\b")
_COLUMN_NAMES = {
    "year": {"year", "years", "yr"},
    "department": {"department", "departments", "dept", "branch"},
    "section": {"section", "sections", "sec"},
}


def normalize_year(value) -> str:
    """'III', 'iii', 'III-Yr', 'III Year', 3, 3.0 and '3rd' all become 'III'."""
    text = str(value or "").strip().upper()
    digits = re.match(r"^(\d+)", text)
    if digits:
        n = int(digits.group(1))
        return _ROMAN[n - 1] if 1 <= n <= len(_ROMAN) else ""
    word = _YEAR_WORD.match(text)
    return word.group(1) if word else ""


def _read_table(filename: str, data: bytes) -> list:
    name = (filename or "").lower()

    if name.endswith(".csv"):
        import csv
        text = data.decode("utf-8-sig", errors="replace")
        return [row for row in csv.reader(io.StringIO(text))]

    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        try:
            workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            return [list(row) for row in workbook.active.iter_rows(values_only=True)]
        except Exception:
            raise ValueError("Couldn't read this Excel file. Save it as .xlsx and try again.")

    raise ValueError("Upload an .xlsx or .csv file.")


def _parse_rows(rows: list, allow_no_header: bool = False):
    """
    Shared by file and pasted-text parsing. Finds the Year / Department /
    Section columns by header name (matched loosely); with
    allow_no_header, a list without a header row is read as
    Year, Department, Section in that order.
    Returns (wanted, problems); raises ValueError with a message the
    app can show.
    """
    header_index, columns = None, {}
    for i, row in enumerate(rows[:10]):
        labels = [re.sub(r"\s+", "", str(c or "")).lower() for c in row]
        found = {key: labels.index(label)
                 for key, names in _COLUMN_NAMES.items()
                 for label in labels if label in names}
        if len(found) == 3:
            header_index, columns = i, found
            break

    if header_index is None:
        if not allow_no_header:
            raise ValueError(
                "Couldn't find the columns Year, Department and Section in the first rows of the file.")
        header_index, columns = -1, {"year": 0, "department": 1, "section": 2}

    wanted, seen, problems = [], set(), []
    for offset, row in enumerate(rows[header_index + 1:], start=header_index + 2):
        cells = [row[columns[k]] if columns[k] < len(row) else None
                 for k in ("year", "department", "section")]
        if all(c in (None, "") for c in cells):
            continue  # blank line

        year = normalize_year(cells[0])
        department = _clean(cells[1])
        section = str(cells[2] or "").strip().upper()

        if not (year and department and section):
            problems.append(f"Row {offset}: needs a valid Year, Department and Section")
            continue

        key = (year, department, section)
        if key not in seen:
            seen.add(key)
            wanted.append(key)

    if not wanted:
        raise ValueError("No usable rows found - each row needs a Year, Department and Section.")

    return wanted, problems


def parse_class_list_text(text: str):
    """
    Reads a class list pasted into the app — typically columns copied
    straight from Excel (tab-separated), but comma-, semicolon- or
    space-separated lines work too ("III CSE A"). A header row
    (Year, Department, Section) is optional.
    Returns (wanted, problems).
    """
    text = (text or "").strip("\ufeff\r\n ")
    if not text:
        raise ValueError("Paste the class list first.")
    if len(text) > 200_000:
        raise ValueError("The pasted list is too large.")

    import csv
    if "\t" in text:
        rows = list(csv.reader(io.StringIO(text), delimiter="\t"))
    elif "," in text:
        rows = list(csv.reader(io.StringIO(text), delimiter=","))
    elif ";" in text:
        rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    else:
        rows = [line.split() for line in text.splitlines()]

    return _parse_rows(rows, allow_no_header=True)


def parse_class_list(filename: str, data: bytes):
    """Reads an uploaded .xlsx / .csv class list (header row required)."""
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > 2_000_000:
        raise ValueError("The uploaded file is too large (limit 2 MB).")

    return _parse_rows(_read_table(filename, data))


def check_classes(course_names, wanted) -> dict:
    """Same result shape as check(), but for an exact list of
    (year, department, section) classes instead of a cross product."""
    found = {}
    for course_name in course_names:
        parsed = parse_course_name(course_name)
        if parsed:
            found.setdefault(parsed, []).append(course_name)

    order = {}
    for year, department, section in wanted:
        order.setdefault(department, []).append((year, section))

    departments, available, missing = [], 0, 0
    for department, classes in order.items():
        classes.sort(key=lambda c: (_ROMAN.index(c[0]) if c[0] in _ROMAN else 99, c[1]))
        rows = []
        for year, section in classes:
            names = found.get((year, department, section), [])
            rows.append({
                "year": year,
                "section": section,
                "status": "Available" if names else "Missing",
                "course_names": names,
            })
        a = sum(1 for r in rows if r["status"] == "Available")
        available += a
        missing += len(rows) - a
        departments.append({"name": department, "expected": len(rows),
                            "available": a, "missing": len(rows) - a, "classes": rows})

    return {
        "generated_at": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "summary": {"expected": available + missing, "available": available, "missing": missing},
        "departments": departments,
        "unrecognised": [],
    }
