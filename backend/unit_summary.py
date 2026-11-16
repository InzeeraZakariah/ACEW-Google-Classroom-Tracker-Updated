import re

# Pulls the unit number out of a classified label — "Unit 3" (from
# Notes) or "Unit-3" (from a QA item's "unit" field) alike.
UNIT_NUMBER_PATTERN = re.compile(r"(\d+)")


def compute_unit_summary(record, override_unit_count=None):
    """
    Infers how many units a subject's syllabus actually has, from what
    has been uploaded. There's no external syllabus source the app can
    read, so the highest unit number seen across Notes and QA uploads
    is used as the best available proxy — a teacher who's uploaded
    Unit 6 material has revealed the subject has at least 6 units.

    override_unit_count: if the dean has manually corrected this
        subject's unit count (see subject_unit_override_manager.py),
        pass it here — it takes precedence over the auto-detected
        value for both the count and the bucket, while the
        auto-detected value and the raw units found are still returned
        for reference.

    record: a classroom record (class_name, subject, staff_name,
        notes, assignments, qa, ...) as produced by RecordBuilder.

    Returns {"unit_count": int, "auto_detected_unit_count": int,
    "units_found": [ints], "bucket": str, "overridden": bool}, where
    bucket is one of "5 units", "Less than 5 units", or "Greater than
    5 units" — the three groups the dean sorts subjects into before
    applying requirements.
    """
    unit_numbers = set()

    for item in record.get("notes", []):
        match = UNIT_NUMBER_PATTERN.search(item.get("title", "") or "")
        if match:
            unit_numbers.add(int(match.group(1)))

    for item in record.get("qa", []):
        match = UNIT_NUMBER_PATTERN.search(item.get("unit", "") or "")
        if match:
            unit_numbers.add(int(match.group(1)))

    units_found = sorted(unit_numbers)
    auto_detected_unit_count = max(units_found) if units_found else 0

    overridden = override_unit_count is not None
    unit_count = override_unit_count if overridden else auto_detected_unit_count

    if unit_count == 5:
        bucket = "5 units"
    elif unit_count < 5:
        bucket = "Less than 5 units"
    else:
        bucket = "Greater than 5 units"

    return {
        "unit_count": unit_count,
        "auto_detected_unit_count": auto_detected_unit_count,
        "units_found": units_found,
        "bucket": bucket,
        "overridden": overridden,
    }