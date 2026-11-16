import json
import os

DATA_DIR = "data"
REGULATIONS_FILE = os.path.join(DATA_DIR, "regulations.json")
SUBJECTS_FILE = os.path.join(DATA_DIR, "subjects.json")

# Ships with 2021/2025 defaults so the app works before the Dean configures
# anything. Anything the Dean saves (via POST /regulations or the Excel
# upload) is layered on top of / overrides these.
DEFAULT_REGULATIONS = {
    "2021": {
        "default_unit_count": 5,
        "notes_pattern": "Unit-{unit} Notes",
        "assignment_pattern": "Unit-{unit} Assignment",
        "qa_patterns": [
            {"part": "A", "qa_type": "Q&A"},
            {"part": "B", "qa_type": "Q&A"},
        ],
    },
    "2025": {
        "default_unit_count": 5,
        "notes_pattern": "Unit-{unit} Notes",
        "assignment_pattern": "Unit-{unit} Assignment",
        "qa_patterns": [
            {"part": "A", "qa_type": "MCQ Q&A"},
            {"part": "B", "qa_type": "Q&A"},
            {"part": "C", "qa_type": "Questions"},
        ],
    },
}


class ConfigurationManager:
    """
    Persists Dean-configured academic data (regulations + subjects) as JSON
    files on disk, so it survives a server restart without needing a
    database. This is what /regulations, /subjects, and
    /upload-academic-config in main.py read and write.
    """

    # ---------------- Regulations ----------------

    @staticmethod
    def load_regulations():
        stored = {}

        if os.path.exists(REGULATIONS_FILE):
            with open(REGULATIONS_FILE, "r") as f:
                try:
                    stored = json.load(f)
                except json.JSONDecodeError:
                    stored = {}

        # Built-in defaults stay available even if the Dean hasn't touched
        # a given regulation; anything stored overrides/extends them.
        merged = dict(DEFAULT_REGULATIONS)
        merged.update(stored)
        return merged

    @staticmethod
    def save_regulations(regulations: dict):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(REGULATIONS_FILE, "w") as f:
            json.dump(regulations, f, indent=2)

    # ---------------- Subjects ----------------

    @staticmethod
    def load_subjects():
        if not os.path.exists(SUBJECTS_FILE):
            return []

        with open(SUBJECTS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    @staticmethod
    def save_subjects(subjects: list):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SUBJECTS_FILE, "w") as f:
            json.dump(subjects, f, indent=2)

    @staticmethod
    def find_subject_config(year, department, semester, section, subject):
        """
        Look up a Dean-configured entry matching the given course details.
        Returns None if nothing was configured for it, so the caller can
        fall back to a default regulation/unit_count.

        NOTE: not currently called anywhere yet - see the note at the end
        of this turn's response about wiring this into GoogleClassroom.
        """
        year = str(year).strip().upper()
        department = str(department).strip().upper()
        semester = str(semester).strip().upper()
        section = str(section).strip().upper()
        subject = str(subject).strip().upper()

        for entry in ConfigurationManager.load_subjects():
            if (
                str(entry.get("year", "")).strip().upper() == year
                and str(entry.get("department", "")).strip().upper() == department
                and str(entry.get("semester", "")).strip().upper() == semester
                and str(entry.get("section", "")).strip().upper() == section
                and str(entry.get("subject", "")).strip().upper() == subject
            ):
                return entry

        return None