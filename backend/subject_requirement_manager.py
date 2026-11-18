import os
from typing import Any, Dict, List, Optional
from store_data import load_data, save_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FILE = os.path.join(DATA_DIR, "subject_requirements.json")


class SubjectRequirementManager:
    """
    Per-subject upload requirements — which Notes/Assignment/QA unit
    numbers are required for THIS specific subject, and the due date
    they're required by. Reintroduced because subjects don't uniformly
    have 5 units: some have fewer, some more, so a single regulation-
    wide requirement doesn't fit every subject under it.

    Records are written exclusively by the Academic Calendar's
    schedule flow: the dean clicks a date, picks a regulation plus one
    or more Year/Department combinations, and applies one set of
    requirements — with that clicked date as due_date — to every
    subject in those combinations at once via `bulk_save`.

    There is ONE record per subject (keyed by year, department,
    semester, section, subject). Scheduling a subject on a second date
    therefore overwrites its regulation, due_date and requirements.

    A record is removed with `remove_scheduled` when its subject is
    dropped from a schedule or the schedule is deleted — but only if
    the record still carries THAT schedule's due date, so a subject
    that has since been rescheduled to another date is left alone.

    The QA Part/Type structure and a regulation's Year/Department
    scope still live on the Regulation (regulation_manager.py).
    """

    @staticmethod
    def load() -> List[Dict[str, Any]]:
        if not os.path.exists(FILE):
            return []
        try:
            with open(FILE, "r", encoding="utf-8") as file:
                data = load_json(file)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        return [item for item in data if isinstance(item, dict)]

    @staticmethod
    def save(data: List[Dict[str, Any]]) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(FILE, "w", encoding="utf-8") as file:
            save_json(data, file, indent=4, ensure_ascii=False)

    @staticmethod
    def _key(record: Dict[str, Any]):
        return (
            record.get("year"),
            record.get("department"),
            record.get("semester"),
            record.get("section"),
            record.get("subject"),
        )

    @staticmethod
    def save_one(
        year: str,
        department: str,
        semester: str,
        section: str,
        subject: str,
        regulation: Optional[str],
        notes_required_units: List[int],
        assignment_required_units: List[int],
        qa_required_units: List[int],
        due_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = SubjectRequirementManager.load()
        record = {
            "year": year,
            "department": department,
            "semester": semester,
            "section": section,
            "subject": subject,
            "regulation": regulation,
            "notes_required_units": notes_required_units,
            "assignment_required_units": assignment_required_units,
            "qa_required_units": qa_required_units,
            "due_date": due_date,
        }
        key = SubjectRequirementManager._key(record)

        for item in data:
            if SubjectRequirementManager._key(item) == key:
                item.update(record)
                SubjectRequirementManager.save(data)
                return item

        data.append(record)
        SubjectRequirementManager.save(data)
        return record

    @staticmethod
    def bulk_save(
        subjects: List[Dict[str, str]],
        regulation: Optional[str],
        notes_required_units: List[int],
        assignment_required_units: List[int],
        qa_required_units: List[int],
        due_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        subjects: [{"year", "department", "semester", "section",
                     "subject"}, ...] — may span several
                     Year/Department combinations at once.
        Applies the SAME requirement values (and due_date) to every
        subject in the list. The file is read once and written once,
        however many subjects there are (scheduling whole
        year/department combinations can mean hundreds).
        """
        data = SubjectRequirementManager.load()
        index = {SubjectRequirementManager._key(item): item for item in data}

        saved = []
        for s in subjects:
            record = {
                "year": s["year"],
                "department": s["department"],
                "semester": s["semester"],
                "section": s["section"],
                "subject": s["subject"],
                "regulation": regulation,
                "notes_required_units": notes_required_units,
                "assignment_required_units": assignment_required_units,
                "qa_required_units": qa_required_units,
                "due_date": due_date,
            }
            key = SubjectRequirementManager._key(record)

            existing = index.get(key)
            if existing is not None:
                existing.update(record)
                saved.append(existing)
            else:
                data.append(record)
                index[key] = record
                saved.append(record)

        SubjectRequirementManager.save(data)
        return saved

    @staticmethod
    def remove_scheduled(subjects: List[Dict[str, str]], due_date: str) -> int:
        """
        Deletes the requirement records of the given subjects, but only
        those whose due_date still equals `due_date` — a subject that
        has been rescheduled to a different date since keeps its
        record. Returns how many records were removed.
        """
        if not subjects:
            return 0

        keys = {
            (
                s.get("year"),
                s.get("department"),
                s.get("semester"),
                s.get("section"),
                s.get("subject"),
            )
            for s in subjects
        }

        data = SubjectRequirementManager.load()
        kept = [
            item for item in data
            if not (
                SubjectRequirementManager._key(item) in keys
                and item.get("due_date") == due_date
            )
        ]

        removed = len(data) - len(kept)
        if removed:
            SubjectRequirementManager.save(kept)
        return removed

    @staticmethod
    def get_one(
        year: str, department: str, semester: str, section: str, subject: str
    ) -> Optional[Dict[str, Any]]:
        target = (year, department, semester, section, subject)
        for item in SubjectRequirementManager.load():
            if SubjectRequirementManager._key(item) == target:
                return item
        return None

    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        return SubjectRequirementManager.load()
