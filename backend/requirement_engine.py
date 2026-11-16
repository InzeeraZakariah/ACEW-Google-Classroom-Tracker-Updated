from due_date import DueDateEngine
from material_classifier import qa_composite_key


class RequirementEngine:
    """
    Evaluates one subject's uploads against its requirement config.
    Requirement fields (notes_required_units, assignment_required_units,
    qa_required_units) come from a per-subject requirement record
    (subject_requirement_manager.py) — these vary per subject since
    subjects don't uniformly have 5 units. `qa_parts` and `due_date`
    come from the regulation the subject references — those genuinely
    are the same across every subject under a regulation.

    "Required units" fields are explicit lists of numbers the dean
    typed in — e.g. notes_required_units=[1, 2] means Unit 1 AND
    Unit 2 are required, exactly those two, not "the first 2 units" or
    "only unit number 2". Assignment numbers don't need to be
    sequential either — [1, 3] is valid.

    QA is further different in that its denominator counts UNITS, not
    individual Part items: a unit only counts as done once every part
    defined in qa_parts has been uploaded for it. qa_required_units=
    [1, 2] with qa_parts=[A, B] means 2 units × 2 parts = 4 individual
    items must exist, but the fraction shown is "how many of the 2
    required units are fully complete" (0, 1, or 2), not "how many of
    the 4 items exist".

    QA also needs normalized comparison rather than plain title
    matching — a teacher might upload "Unit-1 Part-A Q & A" while the
    requirement says "Unit-1 Part-A Q&A"; those must be treated as the
    same item. So QA items are always compared via the "Unit-1 Part-A
    Q&A" composite from qa_composite_key, never as raw titles.
    """

    @staticmethod
    def _qa_items_by_unit(qa_required_units, qa_parts):
        """
        Turn an explicit list of required unit numbers + a
        regulation's qa_parts into
        {unit_number: [expected_composite_keys_for_that_unit]}. E.g.
        units=[1, 2] with a 2025-style qa_parts:

        {
            1: ["Unit-1 Part-A MCQ Q&A", "Unit-1 Part-B Q&A", "Unit-1 Part-C Q&A"],
            2: ["Unit-2 Part-A MCQ Q&A", "Unit-2 Part-B Q&A", "Unit-2 Part-C Q&A"],
        }
        """
        by_unit = {}
        for unit in qa_required_units:
            by_unit[unit] = [
                f"Unit-{unit} Part-{part_def['part']} {part_def['type']}".strip()
                for part_def in qa_parts
            ]
        return by_unit

    @staticmethod
    def _evaluate_qa(qa_required_units, qa_parts, qa, due_date):
        qa_by_unit = RequirementEngine._qa_items_by_unit(qa_required_units, qa_parts)
        qa_expected_flat = [item for items in qa_by_unit.values() for item in items]
        qa_uploaded_keys = [qa_composite_key(item) for item in qa]
        qa_uploaded_set = set(qa_uploaded_keys)

        # Item-level result (which individual "Unit-N Part-X Type"
        # entries were actually found) — used only for display, e.g.
        # the report's "QA Uploaded List" column.
        item_result = DueDateEngine.calculate(qa_expected_flat, qa_uploaded_keys, due_date)

        # Unit-level result (did EVERY part for a unit show up) — this
        # is what the fraction and status reflect, per the "the
        # denominator counts units, not individual items" rule.
        completed_units = [
            unit for unit, items in qa_by_unit.items()
            if items and all(item in qa_uploaded_set for item in items)
        ]
        pending_units = [unit for unit in qa_by_unit if unit not in completed_units]

        return {
            "due_date": due_date,
            "uploaded_count": len(completed_units),
            "uploaded_materials": item_result["uploaded_materials"],
            "pending_count": len(pending_units),
            "pending_materials": item_result["pending_materials"],
            "status": "Completed" if not pending_units else "Pending",
        }

    @staticmethod
    def evaluate(requirement, qa_parts, due_date, notes, assignments, qa):
        """
        requirement: the per-subject requirement record (from
            SubjectRequirementManager) — contains
            notes_required_units, assignment_required_units,
            qa_required_units.
        qa_parts / due_date: from the regulation the subject
            references — shared across every subject under it.
        notes / assignments / qa: the uploaded lists from a classroom
            record, as produced by RecordBuilder.
        """
        notes_expected = [
            f"Unit {n}" for n in requirement.get("notes_required_units", [])
        ]
        assignment_expected = [
            f"Assignment {n}" for n in requirement.get("assignment_required_units", [])
        ]

        notes_uploaded_titles = [item.get("title", "") for item in notes]
        assignment_uploaded_titles = [item.get("title", "") for item in assignments]

        notes_result = DueDateEngine.calculate(notes_expected, notes_uploaded_titles, due_date)
        assignment_result = DueDateEngine.calculate(assignment_expected, assignment_uploaded_titles, due_date)
        qa_result = RequirementEngine._evaluate_qa(
            requirement.get("qa_required_units", []),
            qa_parts,
            qa,
            due_date,
        )

        overall_status = (
            "Completed"
            if notes_result["status"] == "Completed"
            and assignment_result["status"] == "Completed"
            and qa_result["status"] == "Completed"
            else "Pending"
        )

        return {
            "notes": notes_result,
            "assignments": assignment_result,
            "qa": qa_result,
            "status": overall_status,
        }