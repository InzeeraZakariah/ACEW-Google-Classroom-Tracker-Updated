"""
utils.py
Common Utility Functions
"""

from datetime import datetime
from typing import List
from config import DATE_FORMAT


# Format Google Classroom Date
def format_date(date_string: str) -> str:
    """
    Convert Google Classroom datetime to DD/MM/YYYY
    """

    if not date_string:
        return ""

    try:
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt.strftime(DATE_FORMAT)

    except Exception:
        return ""


# Convert String Date to Datetime
def to_datetime(date_string: str):

    if not date_string:
        return None

    try:
        return datetime.strptime(date_string, DATE_FORMAT)

    except Exception:
        return None

# Get Latest Date
def get_latest_date(items: List[dict]) -> str:
    """
    items = [
        {"title":"Unit 1","date":"22/09/2025"},
        {"title":"Unit 2","date":"25/09/2025"}
    ]
    """

    latest = None

    for item in items:

        dt = to_datetime(item.get("date", ""))

        if dt is None:
            continue

        if latest is None or dt > latest:
            latest = dt

    if latest:
        return latest.strftime(DATE_FORMAT)

    return ""


# Remove Duplicate Materials
def remove_duplicates(materials: List[dict]) -> List[dict]:
    """
    Removes duplicate title/date combinations.
    """
    seen = set()
    unique = []

    for item in materials:

        key = (
            item.get("title", "").strip().lower(),
            item.get("date", "").strip()
        )

        if key not in seen:

            seen.add(key)

            unique.append(item)

    return unique


# Sort by Upload Date
def sort_by_date(materials: List[dict]) -> List[dict]:

    return sorted(
        materials,
        key=lambda x: to_datetime(x.get("date", ""))
        or datetime.min
    )


# Convert List of Materials to Display Text
def materials_to_text(materials: List[dict]) -> str:
    """
    Example:

    Unit 1 - 22/09/2025
    Unit 2 - 25/09/2025
    """

    if not materials:
        return "-"

    return "\n".join(
        f"{item['title']} - {item['date']}"
        for item in materials
    )

# Extract Titles Only
def extract_titles(materials: List[dict]) -> List[str]:

    return [
        item["title"]
        for item in materials
    ]


# Count Uploaded Materials
def uploaded_count(materials: List[dict]) -> int:

    return len(materials)


# Safe String
def safe_text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()