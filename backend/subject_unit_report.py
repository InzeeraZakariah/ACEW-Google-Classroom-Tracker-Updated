import io
from openpyxl import Workbook
from openpyxl.styles import Font

from unit_summary import compute_unit_summary
from subject_unit_override_manager import SubjectUnitOverrideManager


class SubjectUnitReportBuilder:
    """
    Builds the "subject name with unit count" Excel sheet — for one or
    more Year + Department combinations, lists every subject with how
    many units were detected from its uploads (or the dean's manual
    correction, if one was made — see subject_unit_override_manager.py),
    so subjects that deviate from the assumed 5-unit structure are
    visible before requirements are scheduled for them.
    """

    @staticmethod
    def build(records):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Subject Unit Counts"

        headers = [
            "Course Name",
            "Subject Name",
            "Staff Name",
            "Unit Count",
            "Units Found",
            "Bucket",
            "Manually Set",
        ]
        sheet.append(headers)
        for cell in sheet[1]:
            cell.font = Font(bold=True)

        for record in records:
            year = record.get("year", "") or ""
            department = record.get("department", "") or ""
            subject = record.get("subject", "") or ""

            override = SubjectUnitOverrideManager.get_override(year, department, subject)
            summary = compute_unit_summary(record, override_unit_count=override)

            sheet.append([
                record.get("class_name", ""),
                subject,
                record.get("staff_name", ""),
                summary["unit_count"],
                ", ".join(str(u) for u in summary["units_found"]) or "-",
                summary["bucket"],
                "Yes" if summary["overridden"] else "No",
            ])

        for column_cells in sheet.columns:
            length = max(len(str(cell.value)) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = length + 4

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return buffer