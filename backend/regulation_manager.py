import json
import os
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE = os.path.join(DATA_DIR, "regulations.json")


class RegulationManager:
    """
    Manages regulation templates — the QA Part/Type structure, and
    which Years/Departments it applies to (e.g. a 2025 regulation for
    Years I-II, Departments CSE/IT). Due dates are NOT set here — they
    live exclusively on the Academic Calendar's schedule entries (see
    academic_schedule_manager.py), since the dean sets a due date by
    clicking a specific calendar date, not by editing a regulation.
    Which units/assignments are required is also set per-subject, not
    here, since subjects vary in unit count (see
    subject_requirement_manager.py).

    Note: this only needs to change when the *QA structure or scope*
    changes. The actual title parsing (recognizing "Q&A" vs "Q & A"
    vs "Questions", detecting "Part-A", etc.) stays generic in
    material_classifier.py and does not need a new regulation entry —
    it already matches whatever Unit/Part/Type shows up in an
    uploaded title.
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

        # Defensive: skip any malformed entry (e.g. a plain string left
        # over from earlier manual testing or an older data format)
        # rather than letting one bad record crash every regulation
        # operation that has to scan the list.
        return [item for item in data if isinstance(item, dict)]

    @staticmethod
    def save(data: List[Dict[str, Any]]) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    @staticmethod
    def save_regulation(
        name: str,
        qa_parts: List[Dict[str, str]],
        years: Optional[List[str]] = None,
        departments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new regulation, or fully overwrites an existing one
        with the same name — this is also how editing works: the
        caller re-sends every field (pre-filled with current values
        plus whatever changed), since this replaces the whole record
        rather than patching individual fields.

        qa_parts: the Part/Type structure applied to every required
        unit under this regulation (the "which units" itself is set
        per-subject, not here). Each entry is {"part": "A", "type":
        "Q&A"} or {"part": "A", "type": "MCQ Q&A"}. Example — a
        2025-style regulation:

        [
            {"part": "A", "type": "MCQ Q&A"},
            {"part": "B", "type": "Q&A"},
            {"part": "C", "type": "Q&A"},
        ]

        years / departments: which courses this regulation applies to,
            e.g. years=["I", "II"], departments=["CSE", "IT"].
            Stored upper-cased/trimmed to match how GoogleClassroom
            parses course names (see google_classroom.parse_course).
            An empty list on either means "no restriction on that
            dimension" — e.g. years=[] with departments=["CSE"]
            applies to CSE in every year.
        """
        data = RegulationManager.load()
        record = {
            "name": name,
            "qa_parts": qa_parts,
            "years": [y.strip().upper() for y in (years or []) if y.strip()],
            "departments": [d.strip().upper() for d in (departments or []) if d.strip()],
        }

        for item in data:
            if item.get("name") == name:
                item.update(record)
                RegulationManager.save(data)
                return item

        data.append(record)
        RegulationManager.save(data)
        return record

    @staticmethod
    def get_regulation(name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        for item in RegulationManager.load():
            if item.get("name") == name:
                return item
        return None

    @staticmethod
    def list_regulations() -> List[Dict[str, Any]]:
        return RegulationManager.load()

    @staticmethod
    def delete_regulation(name: str) -> bool:
        data = RegulationManager.load()
        filtered = [item for item in data if item.get("name") != name]
        if len(filtered) == len(data):
            return False
        RegulationManager.save(filtered)
        return True