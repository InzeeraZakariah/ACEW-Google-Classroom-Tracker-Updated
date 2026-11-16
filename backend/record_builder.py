from duplicate_checker import DuplicateChecker
from pending import PendingEngine
from material_classifier import classify_material
from utils import format_date


class RecordBuilder:

    @staticmethod
    def build_course_records(service, course_id, class_name):

        records = []

        # Get Topics
        response = service.courses().topics().list(courseId=course_id).execute()
        topics = response.get("topic", [])

        # Get CourseWork
        cw = service.courses().courseWork().list(courseId=course_id).execute().get("courseWork", [])

        # Get Course Materials
        cm = service.courses().courseWorkMaterials().list(courseId=course_id).execute().get("courseWorkMaterial", [])

        # Merge
        all_materials = cw + cm

        # One Topic = One Subject
        for topic in topics:
            subject = topic["name"]

            if (
                subject.lower().startswith("notes")
                or subject.lower().startswith("assignment")
                or subject.lower().startswith("qa")
                or subject.lower().startswith("unit")
            ):
                continue

            topic_id = topic["topicId"]

            notes = []
            assignments = []
            qa = []

            faculty = "Unknown"

            # Collect materials only under this topic
            for item in all_materials:
                
                if item.get("topicId") != topic_id:
                    continue

                title = item.get("title", "").strip()
                material_type, label = classify_material(title)
                creator = item.get("creatorUserId")

                try:
                    teacher = service.userProfiles().get(userId=creator).execute()
                    faculty = teacher["name"]["fullName"]

                except:
                    pass

                if material_type == "notes":
                    notes.append({
                        "title": label,
                        "date": format_date(item["creationTime"])
                    })

                elif material_type == "assignment":
                    assignments.append({
                        "title": label,
                        "date": format_date(item["creationTime"])
                    })

                elif material_type == "qa":
                    qa.append({
                        "title": title,
                        "unit": label["unit"],
                        "part": label["part"],
                        "type": label["type"],
                        "date": format_date(item["creationTime"])
                    })

            duplicates = {
                "notes": DuplicateChecker.find_duplicates(notes),
                "assignments": DuplicateChecker.find_duplicates(assignments),
                "qa": DuplicateChecker.find_duplicates(qa)
            }

            pending = PendingEngine.generate(notes, assignments,qa)

            records.append({
                "class_name": class_name,
                "staff_name": faculty,
                "subject": subject,
                "notes": notes,
                "assignments": assignments,
                "qa": qa,
                "duplicates": duplicates,
                "pending": pending
            })

        return records