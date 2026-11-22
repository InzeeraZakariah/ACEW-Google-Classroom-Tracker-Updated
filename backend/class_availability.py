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


def build_missing_pdf(result: dict, scope_label: str = "") -> io.BytesIO:
    """
    A PDF listing ONLY the classes that are not in Google Classroom,
    grouped by department. `scope_label` describes what was checked,
    e.g. "Year: III | Department: All | Section: A".
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

    summary = result["summary"]
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
            f"<font color='#1a8c40'><b>All {summary['expected']} class(es) in this selection "
            f"are available in Google Classroom.</b></font>", styles["Normal"]))
        doc.build(story)
        buffer.seek(0)
        return buffer

    story.append(Paragraph(
        f"<b>{summary['missing']}</b> of <b>{summary['expected']}</b> class(es) "
        f"<font color='#cc2626'><b>not found</b></font>.", styles["Normal"]))
    story.append(Spacer(1, 10))

    by_department = {}
    for item in missing:
        by_department.setdefault(item["department"], []).append(item)

    for department, items in by_department.items():
        story.append(Paragraph(
            f"{escape(department)} &nbsp; <font size=9 color='#666666'>{len(items)} missing</font>",
            styles["Heading3"],
        ))

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

    doc.build(story)
    buffer.seek(0)
    return buffer