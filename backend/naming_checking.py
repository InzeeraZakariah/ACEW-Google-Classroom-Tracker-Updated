import re
from typing import Any, Dict, List, Tuple

from material_classifier import ASSIGNMENT_NUMBER_PATTERN, NOTE_PATTERNS, PART_PATTERN, UNIT_PATTERN, qa_composite_key



EXAMPLES = {
    "Notes": "Unit 1  /  Unit-1",
    "Assignment": "Assignment-1  /  Assignment 1  /  Unit-1 Assignment",
    "QA": "Unit-1 Part-A Q&A  (Part A also accepted)",
    "Not recognised": "Unit-1  /  Assignment-1  /  Unit-1 Part-A Q&A",
}


def _notes_problem(title: str):
    lower = title.lower()
    if UNIT_PATTERN.search(lower):
        return None

    patterns = [NOTE_PATTERNS] if isinstance(NOTE_PATTERNS, str) else NOTE_PATTERNS
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            word = re.match(r"[a-z]+", pattern).group(0).capitalize()
            return f"Named '{word} {match.group(1)}' - use 'Unit-{match.group(1)}'"

    return "No unit number"


def _assignment_problem(title: str):
    lower = title.lower()

    # "Assignment-1", "Assignment 1" and "Unit-1 Assignment" are all fine.
    if ASSIGNMENT_NUMBER_PATTERN.search(lower) or UNIT_PATTERN.search(lower):
        return None

    return "Assignment number missing"


def _qa_problem(item: Dict[str, Any], title: str):
    # Items may be stored already classified (unit / part / type) or
    # as plain titles; check whichever is there.
    if item.get("unit") is not None or item.get("type"):
        unit = str(item.get("unit") or "")
        part = str(item.get("part") or "")
        if unit.lower().startswith("qa"):
            return "Old-style QA title (no Unit / Part)"
        unit_ok = bool(re.search(r"\d", unit))
        part_ok = bool(part.strip())
    else:
        lower = title.lower()
        unit_ok = bool(UNIT_PATTERN.search(lower))
        part_ok = bool(PART_PATTERN.search(lower))

    problems = []
    if not unit_ok:
        problems.append("Unit number missing")
    if not part_ok:
        problems.append("Part (A/B/C) missing")
    return "; ".join(problems) or None


def find_mismatches(records_by_pair: Dict[Tuple[str, str], List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """
    records_by_pair: {(year, department): [Classroom records]}.

    Returns one row per upload that isn't in the standard naming
    format, sorted by department, year, course, subject. Row keys:
    year, department, class_name, subject, staff_name, kind, title,
    problem, expected.
    """
    rows = []
    seen = set()

    def add(year, department, record, kind, title, problem):
        row = {
            "year": year,
            "department": department,
            "class_name": record.get("class_name") or "Unknown",
            "subject": record.get("subject", ""),
            "staff_name": record.get("staff_name", ""),
            "kind": kind,
            "title": title or "(no title)",
            "problem": problem,
            "expected": EXAMPLES[kind],
        }
        key = (department, year, row["class_name"], row["subject"], kind, row["title"])
        if key not in seen:
            seen.add(key)
            rows.append(row)

    for (year, department), records in records_by_pair.items():
        for record in records:
            for item in record.get("notes", []) or []:
                title = str(item.get("original_title") or item.get("title") or item.get("unit") or "").strip()
                problem = _notes_problem(title)
                if problem:
                    add(year, department, record, "Notes", title, problem)

            for item in record.get("assignments", []) or []:
                title = str(item.get("original_title") or item.get("title") or "").strip()
                problem = _assignment_problem(title)
                if problem:
                    add(year, department, record, "Assignment", title, problem)

            for item in record.get("qa", []) or []:
                title = str(item.get("original_title") or item.get("title") or qa_composite_key(item) or "").strip()
                problem = _qa_problem(item, title)
                if problem:
                    add(year, department, record, "QA", title, problem)

            # Uploads the classifier couldn't place at all (only present
            # if the Classroom fetch keeps them in record["other"]).
            for item in record.get("other", []) or []:
                title = str(item.get("original_title") or item.get("title") or "").strip()
                add(year, department, record, "Not recognised", title,
                    "Not recognised as Notes, Assignment or Q&A")

    rows.sort(key=lambda r: (r["department"], r["year"], r["class_name"],
                             r["subject"].lower(), r["kind"], r["title"].lower()))
    return rows