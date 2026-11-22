from typing import Any, Dict, List, Optional
from store_data import load_json, save_json

file = "due_date.json"

class DueDateManager:
    """
    Manages the per-subject expected-upload REQUIREMENTS for notes,
    assignments, and QA — which units, how many assignments, which
    regulation's Part/Type structure to expand QA units against.

    The due date itself is NOT stored here anymore. A single due date
    applies to Notes/Assignments/QA uniformly, shared by every class
    under the same regulation — see `regulation_manager.py`, which
    is where the dean sets it. This file only answers "what's
    required for this specific subject", not "by when".
    """
    
    @staticmethod
    def load() -> List[Dict[str, Any]]:
        return load_json(file)

    @staticmethod
    def save(data: List[Dict[str, Any]]) -> None:
        save_json(file,data)
        
    # SAVE / UPDATE RECORD
    @staticmethod
    def save_due_date(
        year: str,
        department: str,
        semester: str,
        section: str,
        subject: str,
        regulation: Optional[str] = None,
        notes_required_units: Optional[List[int]] = None,
        assignment_required_count: Optional[int] = None,
        qa_required_units: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Save or update the requirement record for a subject. If the
        record exists, it is updated; otherwise, a new one is added.

        notes_required_units: which unit numbers' notes are required,
            e.g. [1, 2] for "notes - 2 units".
        assignment_required_count: how many assignments are required,
            e.g. 1.
        qa_required_units: which unit numbers' QA is required — every
            part defined in `regulation`'s template is expanded for
            each of these units. E.g. qa_required_units=[1] with a
            2025-style regulation template expands to Unit-1 Part-A
            MCQ Q&A, Unit-1 Part-B Q&A, and Unit-1 Part-C Q&A all
            being required.
        """
        data = DueDateManager.load()

        record = {
            "year": year,
            "department": department,
            "semester": semester,
            "section": section,
            "subject": subject,
            "regulation": regulation,
            "notes_required_units": notes_required_units or [],
            "assignment_required_count": assignment_required_count or 0,
            "qa_required_units": qa_required_units or [],
        }

        # Update existing record if found
        for item in data:
            if (
                item.get("year") == year
                and item.get("department") == department
                and item.get("semester") == semester
                and item.get("section") == section
                and item.get("subject") == subject
            ):
                item.update(record)
                DueDateManager.save(data)
                return item

        # Add new record
        data.append(record)
        DueDateManager.save(data)
        return record

    # RETRIEVE RECORD
    @staticmethod
    def get_due_date(year: str, department: str, semester: str, section: str, subject: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the requirement record for a subject.
        Returns the record if found, otherwise None.
        """
        data = DueDateManager.load()
        for item in data:
            if (
                item.get("year") == year
                and item.get("department") == department
                and item.get("semester") == semester
                and item.get("section") == section
                and item.get("subject") == subject
            ):
                return item
        return None

    @staticmethod
    def list_all() -> List[Dict[str, Any]]:
        """Every configured subject's requirement record."""
        return DueDateManager.load()
