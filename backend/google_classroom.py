import os
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from material_classifier import classify_material
from record_builder import RecordBuilder
from utils import format_date


# Google Classroom Scopes
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.course-work.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/classroom.topics.readonly",
]

CREDENTIALS_FILE = "credentials.json"
# TOKEN_FILE = "token.json" 

TOKEN_FILE = os.getenv(
    "GOOGLE_TOKEN_FILE",
    str(Path(__file__).resolve().parent / "token.json")
)

print("google_classroom.py loaded")

class GoogleClassroom:

    def __init__(self):
        self.creds = None
        self.service = self.build_service()

    def build_service(self):
        token_path = Path(TOKEN_FILE)

        if not token_path.exists():
            raise FileNotFoundError(
                f"Google OAuth token file not found: {token_path}. "
                "Provide token.json locally or configure the "
                "GOOGLE_TOKEN_FILE environment variable on Render."
            )

        # Load the previously generated OAuth token.
        self.creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # Refresh an expired token if a refresh token is available.
        if self.creds.expired:

            if not self.creds.refresh_token:
                raise RuntimeError(
                    "Google OAuth token has expired and has no refresh token. "
                    "Generate a new token with offline access."
                )

            try:
                self.creds.refresh(Request())

            except Exception as exc:
                raise RuntimeError(
                    "Unable to refresh the Google OAuth token. "
                    "Check the token, OAuth consent configuration, "
                    "and requested API scopes."
                ) from exc

        if not self.creds.valid:
            raise RuntimeError(
                "Google OAuth credentials are invalid. "
                "Generate a new token and check its permissions."
            )

        # Create the Google Classroom API service.
        return build("classroom", "v1", credentials=self.creds, cache_discovery=False)
    
    # Get All Courses
    def get_courses(self):
        courses = []
        page_token = None

        while True:
            response = self.service.courses().list(courseStates=["ACTIVE"], pageToken=page_token).execute(num_retries=3) # active courses will fetch
            courses.extend(response.get("courses", []))
            page_token = response.get("nextPageToken") # getting next course 
            if not page_token: #  all courses has taken completely
                break

        courses.sort(key=lambda x: x.get("name", "")) 

        return courses

    # Get Teachers
    def get_teachers(self, course_id):
        teachers = []
        response = self.service.courses().teachers().list(courseId=course_id).execute(num_retries=3)

        for teacher in response.get("teachers", []):
            profile = teacher.get("profile", {})
            name = profile.get("name", {})
            teachers.append({
                "id": profile.get("id", ""),
                "name": name.get("fullName", "Unknown"),
                "email": profile.get("emailAddress","")
            })

        teachers.sort(key=lambda x: x["name"])

        return teachers

    # Get Subject Names
    def get_subject_name(self, course_id):
        response = self.service.courses().topics().list(courseId=course_id).execute(num_retries=3)
        subjects = []

        for topic in response.get("topic", []):
            name = topic.get("name", "").strip()

            if not name:
                continue

            lower = name.lower()
            if (lower.startswith("notes") or lower.startswith("assignment") or lower.startswith("qa") or lower.startswith("unit") or "question" in lower):
                continue

            if name not in subjects:
                subjects.append(name)

        return subjects

    # Course Work - Notes, QA, Assignments
    def get_course_work(self, course_id):
        notes = []
        assignments = []
        qa = []

        response = self.service.courses().courseWork().list(courseId=course_id).execute(num_retries=3)

        for item in response.get("courseWork", []):
            title = item.get("title", "").strip()
            created = item.get("creationTime", "")
            material_type, label = classify_material(title)

            if material_type == "notes":
                notes.append({"title": label, "date": format_date(created)})

            elif material_type == "assignment":
                assignments.append({"title": label, "date": format_date(created)})

            elif material_type == "qa":
                qa.append({
                    "unit": label.get("unit", ""),
                    "part": label.get("part", ""),
                    "date": format_date(created) })

            else:
                assignments.append({"title": title, "date": format_date(created)})

        return notes, assignments, qa

    # Course Work Materials
    def get_course_materials(self, course_id):
        notes = []
        assignments = []
        qa = []

        response = self.service.courses().courseWorkMaterials().list(courseId=course_id).execute(num_retries=3)

        for item in response.get("courseWorkMaterial", []):
            title = item.get("title", "").strip()
            created = item.get("creationTime", "")
            material_type, label = classify_material(title)

            if material_type == "notes":
                notes.append({"title": label, "date": format_date(created)})

            elif material_type == "assignment":
                assignments.append({"title": label, "date": format_date(created)})

            elif material_type == "qa":
                qa.append({
                    "unit": label.get("unit", ""),
                    "part": label.get("part", ""),
                    "date": format_date(created)
                })

            else:
                notes.append({"title": title,"date": format_date(created)})

        return notes, assignments, qa


    # Announcements
    def get_announcements(self, course_id):
        notes = []
        assignments = []
        qa = []

        response = self.service.courses().announcements().list(courseId=course_id).execute(num_retries=3)

        for item in response.get("announcements", []):
            title = item.get("text", "").strip()
            created = item.get("creationTime", "")
            material_type, label = classify_material(title)

            if material_type == "notes":
                notes.append({"title": label, "date": format_date(created)})

            elif material_type == "assignment":
                assignments.append({"title": label,
                    "date": format_date(created)})

            elif material_type == "qa":
                qa.append({
                    "unit": label.get("unit", ""),
                    "part": label.get("part", ""),
                    "date": format_date(created)
                })

        return notes, assignments, qa


    # Topics
    def get_topics(self, course_id):
        notes = []
        assignments = []
        qa = []

        response = self.service.courses().topics().list(courseId=course_id).execute(num_retries=3)

        for item in response.get("topic", []):
            title = item.get("name", "").strip()
            material_type, label = classify_material(title)

            if material_type == "notes":
                notes.append({"title": label, "date": "-"})

            elif material_type == "assignment":
                assignments.append({"title": label,"date": "-"})

            elif material_type == "qa":
                qa.append({
                    "unit": label.get("unit", ""),
                    "part": label.get("part", ""),
                    "date": "-"
                })

        return notes, assignments, qa

    # Merge All Materials
    def collect_materials(self, course_id):

        notes = []
        assignments = []
        qa = []

        # Course Work
        n, a, q = self.get_course_work(course_id)
        notes.extend(n)
        assignments.extend(a)
        qa.extend(q)

        # Course Work Materials
        n, a, q = self.get_course_materials(course_id)
        notes.extend(n)
        assignments.extend(a)
        qa.extend(q)

        # Announcements
        n, a, q = self.get_announcements(course_id)
        notes.extend(n)
        assignments.extend(a)
        qa.extend(q)

        # Topics
        n, a, q = self.get_topics(course_id)
        notes.extend(n)
        assignments.extend(a)
        qa.extend(q)

        return {
            "notes": notes,
            "assignments": assignments,
            "qa": qa
        }

    # Process One Course
    def process_course(self, course):
        course_name = course["name"]
        course_id = course["id"]

        yr, sem, dept, sec = self.parse_course(course_name)

        print("=" * 70)
        print("Course :", course_name)

        records = RecordBuilder.build_course_records( self.service, course_id, course_name)

        # Attach the parsed year/semester/department/section to every
        # record so the due-date/requirement report can look up which
        # config applies to it — records previously carried nothing
        # but class_name/staff_name/subject, which isn't enough for
        # that lookup.
        for record in records:
            record["year"] = yr
            record["semester"] = sem
            record["department"] = dept
            record["section"] = sec

        return records

    # Create Dashboard Summary
    def create_summary(self, records): 
        completed = sum(1 for r in records if r["pending"]["status"] == "Completed")
        pending = len(records) - completed

        return {
            "total_classes": len(set(r["class_name"] for r in records)),
            "total_staff": len(records),
            "completed_staff": completed,
            "pending_staff": pending
        }

    # Classifying the Department names as course
    def parse_course(self, course_name):
        """
        Supports real course-name formats such as:

        III-Yr V-Sem CSE A (2024-2028)
        I-Yr I-Sem MBA C
        III-Yr II-SEM ME-PWD A
        IV-Yr VII-Sem AI&DS A (2023-2027)

        NOTE: the "Year" token in real course names is abbreviated
        ("-Yr"), not spelled out ("-Year") — do not match against the
        full word, or every course will fail to parse and get
        silently filtered out.
        """

        text = course_name.upper()

        # Remove batch if present
        if "(" in text:
            text = text.split("(")[0].strip()

        parts = text.split()

        if len(parts) < 4:
            return None, None, None, None

        # Year — take everything before the first hyphen so this works
        # regardless of whether the suffix is "-YR", "-YEAR", etc.
        year = parts[0].split("-")[0]

        # Find "SEM"
        sem_index = None

        for i, part in enumerate(parts):
            if "SEM" in part:
                sem_index = i
                break

        if sem_index is None:
            return None, None, None, None

        # Semester — same "before the first hyphen" trick as Year
        # (e.g. "V-SEM" -> "V", "VII-Sem" -> "VII").
        semester = parts[sem_index].split("-")[0]

        # Department
        if sem_index + 1 >= len(parts):
            return None, None, None, None

        department = parts[sem_index + 1]

        # Section
        section = parts[-1]

        return year, semester, department, section
    
    # Fetch Classroom Data
    def fetch_staff_data(self, department=None, year=None, section=None):
        records = []
        courses = self.get_courses()

        
        print("=" * 60)
        print("Department :", department)
        print("Year       :", year)
        print("Section    :", section)
        print("=" * 60)

        courses = self.get_courses()

        print("TOTAL COURSES :", len(courses))

        for c in courses:
            print(c["name"])

        for course in courses:

            course_name = course["name"]
            yr, sem, dept, sec = self.parse_course(course_name)

            # Debug: show what each course parsed to, so mismatches
            # against the requested filters are easy to spot in logs.
            print(f"Parsed '{course_name}' -> year={yr}, semester={sem}, dept={dept}, section={sec}")

            if year and yr != year.upper():
                continue

            if department and dept != department.upper():
                continue

            if section and sec != section.upper():
                continue

            print("Processing :", course_name)

            records.extend(self.process_course(course))

        return {
            "summary": self.create_summary(records),
            "records": records
        }


    # Fetch All Classes (Excel)
    def fetch_excel_data(self):
        classrooms = []
        courses = self.get_courses()

        for course in courses:
            rows = self.process_course(course)
            classrooms.append({
                "class_name": course.get("name"),
                "records": rows
            })

        return classrooms


    def fetch_selected_excel_data(self, department=None, year=None, section=None):
        records = []
        courses = self.get_courses()

        for course in courses:
            course_name = course['name']
            yr, sem, dept, sec = self.parse_course(course_name)

            if year and  yr != year.upper():
                continue
            if department and dept != department.upper():
                continue
            if section and sec != section.upper():
                continue

            records.extend(self.process_course(course))

        return records


    # Search Staff
    def search_staff(self, keyword):
        keyword = keyword.lower()
        records = self.fetch_staff_data()["records"]
        return [record for record in records if keyword in record["staff_name"].lower() or keyword in record["subject"].lower() or keyword in record["class_name"].lower()]

    # Dashboard
    def dashboard(self):
        return self.fetch_staff_data()["summary"]

    # Get All Staff
    def get_staff(self):
        records = self.fetch_staff_data()["records"]
        staff = sorted(list({r["staff_name"] for r in records}))
        return staff

    # Fetch records from every classroom
    def fetch_all_staff_data(self):
        return self.fetch_staff_data(department=None, year=None, section=None)