import json
import os
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE = os.path.join(DATA_DIR, "subject_unit_overrides.json")


class SubjectUnitOverrideManager:
    """
    Manual overrides for a subject's unit count. unit_summary.py's
    auto-detected count is only a proxy (the highest unit number seen
    across uploads) — the dean may know the actual syllabus structure
    and override it here. Subject NAMES always come from Google
    Classroom and are never editable; only the unit count is.

    Keyed by (year, department, subject) — not by regulation, since a
    subject's real unit count doesn't change depending on which
    regulation someone happens to be viewing.
    """

    @staticmethod
    def load() -> List[Dict[str, Any]]:
        if not os.path.exists(FILE):
            return []
        try:
            with open(FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        return [item for item in data if isinstance(item, dict)]

    @staticmethod
    def save(data: List[Dict[str, Any]]) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    @staticmethod
    def _key(year: str, department: str, subject: str):
        return (year, department, subject)

    @staticmethod
    def set_override(year: str, department: str, subject: str, unit_count: int) -> Dict[str, Any]:
        data = SubjectUnitOverrideManager.load()
        record = {"year": year, "department": department, "subject": subject, "unit_count": unit_count}
        key = SubjectUnitOverrideManager._key(year, department, subject)

        for item in data:
            if SubjectUnitOverrideManager._key(item.get("year"), item.get("department"), item.get("subject")) == key:
                item.update(record)
                SubjectUnitOverrideManager.save(data)
                return item

        data.append(record)
        SubjectUnitOverrideManager.save(data)
        return record

    @staticmethod
    def get_override(year: str, department: str, subject: str) -> Optional[int]:
        key = (year, department, subject)
        for item in SubjectUnitOverrideManager.load():
            if (item.get("year"), item.get("department"), item.get("subject")) == key:
                return item.get("unit_count")
        return None

    @staticmethod
    def clear_override(year: str, department: str, subject: str) -> bool:
        data = SubjectUnitOverrideManager.load()
        key = (year, department, subject)
        filtered = [
            item for item in data
            if (item.get("year"), item.get("department"), item.get("subject")) != key
        ]
        if len(filtered) == len(data):
            return False
        SubjectUnitOverrideManager.save(filtered)
        return True