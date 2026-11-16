from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from config import EXCEL_FILE_NAME
from collections import defaultdict

class ExcelGenerator:

    @staticmethod
    def list_to_text(items):
        if not items:
            return "-"

        result = []

        for item in items:

            # Notes / Assignments
            if "title" in item:
                result.append(f"{item['title']} ({item['date']})")
            # Question & Answer
            elif "unit" in item:
                text = item["unit"]
                if item.get("part"):
                    text += f" - {item['part']}"
                text += f" ({item['date']})"
                result.append(text)

        return "\n".join(result)
    
    @staticmethod
    def duplicate_to_text(duplicates):
        if not duplicates:
            return "-"

        result = []

        for item in duplicates:
            if "title" in item:
                result.append(f"{item['title']} ({item['count']} times)")
            elif "unit" in item:
                text = item["unit"]
                if item.get("part"):
                    text += f" - {item['part']}"
                text += f" ({item['count']} times)"
                result.append(text)

        return "\n".join(result)

    @staticmethod
    def pending_to_text(pending):
        result = []

        if pending["notes"]["pending"]:
            result.append("Notes : " + ", ".join(pending["notes"]["pending"]))

        if pending["assignments"]["pending"]:
            result.append("Assignments : " + ", ".join(pending["assignments"]["pending"]))

        if pending["qa"]["pending"]:
            result.append("Question & Answer : " + ", ".join(pending["qa"]["pending"]))

        if not result:
            return "-"

        return "\n".join(result)

    @staticmethod
    def completion_text(pending):

        return (
            f"Notes "
            f"{pending['notes']['uploaded']}/"
            f"{pending['notes']['total']}\n"

            f"Assignments "
            f"{pending['assignments']['uploaded']}/"
            f"{pending['assignments']['total']}\n"

            f"Question & Answer "
            f"{pending['qa']['uploaded']}/"
            f"{pending['qa']['total']}"
        )

    @staticmethod
    def generate(records):
        wb = Workbook()

        # Remove default sheet
        wb.remove(wb.active)

        headers = [
            "Staff",
            "Subject",
            "Notes",
            "Assignments",
            "Question & Answer",
            "Completion",
            "Duplicate Uploads",
            "Pending",
            "Status"
        ]

        # Group records by classroom
        grouped = defaultdict(list)

        for record in records:
            grouped[record["class_name"]].append(record)

        # Create one sheet per classroom
        for class_name, class_records in grouped.items():
            ws = wb.create_sheet(title=class_name[:31])

            # Header Row
            for col, header in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col)
                cell.value = header
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid",fgColor="1F4E78")
                cell.alignment = Alignment(horizontal="center", vertical="center",wrap_text=True)

            row = 2

            # Write Records
            for record in class_records:
                ws.cell(row=row, column=1).value = record["staff_name"]
                ws.cell(row=row, column=2).value = record["subject"]
                ws.cell(row=row, column=3).value = ExcelGenerator.list_to_text(record["notes"])
                ws.cell(row=row, column=4).value = ExcelGenerator.list_to_text(record["assignments"])
                ws.cell(row=row, column=5).value = ExcelGenerator.list_to_text(record["qa"])
                ws.cell(row=row, column=6).value = ExcelGenerator.completion_text(record["pending"])

                duplicates = []

                duplicates.extend(record["duplicates"]["notes"])
                duplicates.extend(record["duplicates"]["assignments"])
                duplicates.extend(record["duplicates"]["qa"])

                ws.cell(row=row, column=7).value = ExcelGenerator.duplicate_to_text(duplicates)
                ws.cell(row=row, column=8).value = ExcelGenerator.pending_to_text(record["pending"])
                ws.cell(row=row, column=9).value = record["pending"]["status"]

                # Alignment
                for col in range(1, 10):
                    ws.cell(row=row, column=col).alignment = Alignment(vertical="top",wrap_text=True)

                row += 1

            # Adjust Column Widths
            widths = {
                "A": 20,   # Staff
                "B": 25,   # Subject
                "C": 35,   # Notes
                "D": 35,   # Assignments
                "E": 40,   # Question & Answer
                "F": 20,   # Completion
                "G": 30,   # Duplicate Uploads
                "H": 40,   # Pending
                "I": 15    # Status
            }
                                
            for column, width in widths.items():
                ws.column_dimensions[column].width = width

            # Freeze Header
            ws.freeze_panes = "A2"

        # Save Workbook
        wb.save(EXCEL_FILE_NAME)

        return EXCEL_FILE_NAME

                                    