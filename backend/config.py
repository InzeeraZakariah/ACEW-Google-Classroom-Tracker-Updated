# App Configuration File

"""
config.py
Application Configuration
"""

# Google Classroom Login Mode
LOGIN_MODE = "dean"


# Expected Notes
EXPECTED_NOTES = [
    "Unit 1",
    "Unit 2",
    "Unit 3",
    "Unit 4",
    "Unit 5",
]

# Expected Assignments
EXPECTED_ASSIGNMENTS = [
    "Assignment 1",
    "Assignment 2",
    "Assignment 3",
]



# Expected Question & Answer
EXPECTED_QA = {
    "QA Unit-1",
    "QA Unit-2",
    "QA Unit-3",
    "QA Unit-4",
    "QA Unit-5"
}

# Excel Report
EXCEL_FILE_NAME = "Google_Classroom_Report.xlsx"
EXCEL_SHEET_NAME = "Classroom Report"


# API Configuration
API_TITLE = "Google Classroom Monitoring API"
API_VERSION = "1.0.0"


# Date Format
DATE_FORMAT = "%d/%m/%Y"


# Flutter Dialog Labels
NOTES_LABEL = "Notes"
ASSIGNMENT_LABEL = "Assignments"
QA_LABEL = "Question & Answer"


# Status Labels
STATUS_COMPLETED = "Completed"
STATUS_PENDING = "Pending"


# WhatsApp Message
WHATSAPP_TEMPLATE = """
Dear {staff},

The following Google Classroom uploads are pending.

Notes:
{notes}

Assignments:
{assignments}

Question & Answer:
{qa}

Kindly upload the pending materials at the earliest.

Thank you.
"""