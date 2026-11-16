from config import EXPECTED_NOTES, EXPECTED_ASSIGNMENTS, EXPECTED_QA, STATUS_COMPLETED, STATUS_PENDING


class PendingEngine:

    @staticmethod
    def _upload_key(item):
        # Notes / Assignments are matched by title.
        if "title" in item:
            return item["title"].strip()

        # QA items are matched by the full Unit -> Part -> Type composite,
        # e.g. "Unit-3 Part-B Q&A" or "Unit-1 Part-A MCQ Q&A".
        # EXPECTED_QA entries in config.py must use this exact format.
        return " ".join(
            piece for piece in [
                item.get("unit", ""),
                item.get("part", ""),
                item.get("type", "")
            ] if piece
        ).strip()

    @staticmethod
    def _calculate(uploaded, expected):
        uploaded_titles = {
            PendingEngine._upload_key(item)
            for item in uploaded
        }

        pending = [item for item in expected if item not in uploaded_titles]
        completed = len(expected) - len(pending)

        return {
            "uploaded": completed,
            "total": len(expected),
            "pending": pending
        }

    # Notes
    @staticmethod
    def notes(uploaded_notes):
        return PendingEngine._calculate(
            uploaded_notes,
            EXPECTED_NOTES
        )

    # Assignments
    @staticmethod
    def assignments(uploaded_assignments):
        return PendingEngine._calculate(
            uploaded_assignments,
            EXPECTED_ASSIGNMENTS
        )

    # Question & Answer
    @staticmethod
    def qa(uploaded_qa):
        return PendingEngine._calculate(
            uploaded_qa,
            EXPECTED_QA
        )

    # Overall Result
    @staticmethod
    def generate(notes, assignments, qa):
        notes_result = PendingEngine.notes(notes)
        assignment_result = PendingEngine.assignments(assignments)
        qa_result = PendingEngine.qa(qa)

        pending_exists = (
            notes_result["pending"] or
            assignment_result["pending"] or
            qa_result["pending"]
        )

        status = (
            STATUS_PENDING
            if pending_exists
            else STATUS_COMPLETED
        )

        return {
            "notes": notes_result,
            "assignments": assignment_result,
            "qa": qa_result,
            "status": status
        }

    # WhatsApp Message (for future enhancement)
    @staticmethod
    def whatsapp_text(staff_name, result):

        notes = (
            "\n".join(result["notes"]["pending"])
            if result["notes"]["pending"]
            else "None"
        )

        assignments = (
            "\n".join(result["assignments"]["pending"])
            if result["assignments"]["pending"]
            else "None"
        )

        qa = (
            "\n".join(result["qa"]["pending"])
            if result["qa"]["pending"]
            else "None"
        )

        return f"""Dear {staff_name},

The following Google Classroom uploads are pending.

Notes:
{notes}

Assignments:
{assignments}

Question & Answer:
{qa}

Kindly upload them as soon as possible.

Thank you.
"""