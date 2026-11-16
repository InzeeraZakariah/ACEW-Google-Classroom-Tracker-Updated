import re


# Regular Expression Patterns
# Notes are recognised by "Unit N" only. This must stay a LIST (even
# with one pattern): detect_notes loops over it, and looping over a
# plain string would try each single character as a pattern.
NOTE_PATTERNS = [
    r"unit[\s\-]*(\d+)",
]

ASSIGNMENT_WORD_PATTERN = re.compile(r"\bassignment\b")
ASSIGNMENT_NUMBER_PATTERN = re.compile(r"assignment[\s\-]*(\d+)")

# QA structural patterns — deliberately regex-based (not literal strings)
# so that future regulations (new Parts, new Units) classify correctly
# without needing a code change. Only config.py's EXPECTED_QA list needs
# to be updated by the dean when the regulation changes.
UNIT_PATTERN = re.compile(r"unit[\s\-]*(\d+)")
PART_PATTERN = re.compile(r"part[\s\-]*([a-z])\b")
MCQ_PATTERN = re.compile(r"\bmcq\b")

# Matches every spelling variant of "Q&A": Q&A, Q & A, Q-A, Q &A, Q& A
QA_MARKER_PATTERN = re.compile(r"q\s*[&\-]?\s*a\b")

# "Questions" is treated as naming the same material as "Q&A" for a
# given Unit + Part slot (per spec: they're alternate names a teacher
# might use for the identical upload).
QUESTIONS_WORD_PATTERN = re.compile(r"\bquestions\b")

# Legacy fallback: old-style titles like "QA University Question Paper"
# that don't follow the Unit/Part structure at all.
LEGACY_QA_PREFIX = "qa"


# Notes Detection
def detect_notes(title: str):

    text = title.lower()
    for pattern in NOTE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return True, f"Unit {match.group(1)}"

    if "note" in text:
        return True, title.strip()

    return False, ""


# Assignment Detection
def detect_assignment(title: str):
    text = title.lower()

    # Must contain the word "assignment" somewhere at all.
    if not ASSIGNMENT_WORD_PATTERN.search(text):
        return False, ""

    # Prefer an explicit number directly attached to "assignment"
    # (e.g. "Assignment-1", "Assignment 1").
    number_match = ASSIGNMENT_NUMBER_PATTERN.search(text)
    if number_match:
        return True, f"Assignment {number_match.group(1)}"

    # Fall back to a Unit number elsewhere in the title
    # (e.g. "Unit-1 Assignment" — no number directly after the word).
    # The assignment for Unit N is Assignment N, so it is filed under
    # the same "Assignment N" label that RequirementEngine looks for —
    # otherwise it would never count towards a required assignment.
    unit_match = UNIT_PATTERN.search(text)
    if unit_match:
        return True, f"Assignment {unit_match.group(1)}"

    return True, title.strip()


def normalize_qa_type(text: str):
    """
    Given a raw fragment of text, determine whether it names a QA-type
    marker ("Q&A" / "Questions", optionally prefixed "MCQ"), and return
    its normalized form.

    Returns "MCQ Q&A", "Q&A", or None if no QA marker is present.
    Useful for normalizing config.py / dean-entered EXPECTED_QA strings
    consistently with how uploaded material titles are classified.
    """
    lower = text.lower()

    has_marker = bool(QA_MARKER_PATTERN.search(lower)) or bool(QUESTIONS_WORD_PATTERN.search(lower))
    if not has_marker:
        return None

    if MCQ_PATTERN.search(lower):
        return "MCQ Q&A"

    return "Q&A"


def qa_composite_key(item: dict) -> str:
    """
    The single canonical "Unit-3 Part-B Q&A" style identity string for a
    classified QA item (unit/part/type dict, e.g. as produced by
    detect_qa or stored in a record's "qa" list). Both pending.py and
    the due-date report must build this the same way, or a spelling
    variant that classify_material correctly normalizes will still
    show up as a mismatch downstream.
    """
    return " ".join(
        piece for piece in [
            item.get("unit", ""),
            item.get("part", ""),
            item.get("type", "")
        ] if piece
    ).strip()


# Question & Answer Detection
def detect_qa(title: str):
    text = title.strip()
    lower = text.lower()

    unit_match = UNIT_PATTERN.search(lower)
    # Part is optional — some QA uploads are per-unit only, with no
    # Part-A/B/C split (e.g. "Unit-1 Questions").
    part_match = PART_PATTERN.search(lower)

    if unit_match:
        qtype = normalize_qa_type(lower)

        if qtype is not None:
            unit_num = unit_match.group(1)

            return True, {
                "unit": f"Unit-{unit_num}",
                "part": f"Part-{part_match.group(1).upper()}" if part_match else "",
                "type": qtype,
            }

    # Legacy fallback — old titles that started with "qa" but don't
    # follow the Unit/Part structure (e.g. "QA University Question Paper").
    if lower.startswith(LEGACY_QA_PREFIX):
        if unit_match:
            return True, {
                "unit": f"QA Unit-{unit_match.group(1)}",
                "part": "",
                "type": "Q&A",
            }
        return True, {"unit": title.strip(), "part": "", "type": "Q&A"}

    return False, {}


# Main Classifier
def classify_material(title: str):
    title = title.strip()

    # QA (checked first — a QA title also contains "Unit-N", which would
    # otherwise be caught by the notes/assignment patterns below)
    found, label = detect_qa(title)
    if found:
        return "qa", label

    # Assignment (checked before notes — a title like "Unit-1 Assignment"
    # also contains "Unit-1", which the notes pattern would otherwise
    # claim first)
    found, label = detect_assignment(title)
    if found:
        return "assignment", label

    # notes
    found, label = detect_notes(title)
    if found:
        return "notes", label

    return "other", title