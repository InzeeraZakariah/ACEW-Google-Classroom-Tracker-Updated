import json
import os
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE = os.path.join(DATA_DIR, "academic_schedule.json")


class AcademicScheduleManager:
    """
    One schedule entry per calendar date — what the dean set when they
    clicked that date on the Academic Calendar: the regulation, the
    Year+Department PAIRS it applies to, and which Notes/Assignment/QA
    unit numbers are required by that date.

    Pairs are stored as explicit {"year", "department"} items — NOT two
    separate lists, which would cross-multiply into every combination
    instead of the specific pairs the dean picked.

    Nothing is looked up from Google Classroom when an entry is saved.
    The subjects are only found later, when a Pending/Completed report
    is downloaded: the report reads these entries, fetches Classroom
    data for just their pairs, and evaluates each subject against the
    entry's requirements and due date. So this file is the single
    source of truth for due dates — there are no per-subject records
    to keep in sync.

    Older entries stored a `subjects` list instead of `pairs`;
    `pairs_of` still reads those (deriving the pairs from them).
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

        return [item for item in data if isinstance(item, dict) and item.get("date")]

    @staticmethod
    def save(data: List[Dict[str, Any]]) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    @staticmethod
    def pairs_of(entry: Dict[str, Any]) -> List[Tuple[str, str]]:
        """The entry's distinct (year, department) pairs, in order."""
        pairs: List[Tuple[str, str]] = []
        seen = set()

        def add(item: Any) -> None:
            if not isinstance(item, dict):
                return
            year = item.get("year")
            department = item.get("department")
            if not year or not department:
                return
            key = (year, department)
            if key not in seen:
                seen.add(key)
                pairs.append(key)

        for pair in entry.get("pairs") or []:
            add(pair)

        if not pairs:
            # Legacy entries: derive the pairs from the old subjects list.
            for subject in entry.get("subjects") or []:
                add(subject)

        return pairs

    @staticmethod
    def save_entry(
        date: str,
        regulation: str,
        pairs: List[Dict[str, str]],
        notes_required_units: List[int],
        assignment_required_units: List[int],
        qa_required_units: List[int],
    ) -> Dict[str, Any]:
        """date: ISO "yyyy-mm-dd". Replaces any existing schedule for
        that date rather than creating a second entry (and drops any
        legacy `subjects` list it carried)."""
        data = AcademicScheduleManager.load()
        record = {
            "date": date,
            "regulation": regulation,
            "pairs": [
                {"year": p["year"], "department": p["department"]} for p in pairs
            ],
            "notes_required_units": notes_required_units,
            "assignment_required_units": assignment_required_units,
            "qa_required_units": qa_required_units,
        }

        for item in data:
            if item.get("date") == date:
                item.clear()
                item.update(record)
                AcademicScheduleManager.save(data)
                return item

        data.append(record)
        data.sort(key=lambda e: e.get("date", ""))
        AcademicScheduleManager.save(data)
        return record

    @staticmethod
    def get_entry(date: str) -> Optional[Dict[str, Any]]:
        for item in AcademicScheduleManager.load():
            if item.get("date") == date:
                return item
        return None

    @staticmethod
    def delete_entry(date: str) -> bool:
        data = AcademicScheduleManager.load()
        filtered = [item for item in data if item.get("date") != date]
        if len(filtered) == len(data):
            return False
        AcademicScheduleManager.save(filtered)
        return True

    @staticmethod
    def list_entries(regulation: Optional[str] = None) -> List[Dict[str, Any]]:
        data = AcademicScheduleManager.load()
        if regulation:
            return [item for item in data if item.get("regulation") == regulation]
        return data