class DueDateEngine:
    @staticmethod
    def calculate(expected_materials, uploaded_materials, due_date):
        """
        expected_materials:
            List of expected material titles

        uploaded_materials:
            List of uploaded material titles

        Example:

        expected:
        [
            "Unit-1 Notes",
            "Unit-2 Notes",
            "Assignment-1",
            "Unit-1 Part-A Q&A",
            "Unit-1 Part-B Questions"
        ]

        uploaded:
        [
            "Unit-1 Notes",
            "Assignment-1"
        ]
        """

        # Convert uploaded titles to a normalized set
        uploaded_set = {str(title).strip().lower() for title in uploaded_materials}

        uploaded = []
        pending = []

        # Compare expected vs uploaded
        for material in expected_materials:
            material = str(material).strip()
            if material.lower() in uploaded_set:
                uploaded.append(material)
            else:
                pending.append(material)

        # Status
        if len(pending) == 0:
            status = "Completed"
        else:
            status = "Pending"

        return {
            "due_date": due_date,
            "uploaded_count": len(uploaded),
            "uploaded_materials": uploaded,
            "pending_count": len(pending),
            "pending_materials": pending,
            "status": status
        }