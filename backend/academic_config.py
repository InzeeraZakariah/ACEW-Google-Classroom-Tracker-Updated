import os
import json


CONFIG_FILE = "academic_configuration.json"


class AcademicConfig:

    # ========================================================
    # DEFAULT CONFIGURATION
    # ========================================================

    DEFAULT = {

        "2021": {
            "unit_count": 5,

            "notes": "Unit-{unit} Notes",

            "assignments": "Unit-{unit} Assignment",

            "qa": [
                "Part-A Q&A",
                "Part-B Questions"
            ]
        },

        "2025": {
            "unit_count": 5,

            "notes": "Unit-{unit} Notes",

            "assignments": "Unit-{unit} Assignment",

            "qa": [
                "Part-A MCQ-Q&A",
                "Part-B Q&A",
                "Part-C Questions"
            ]
        }
    }


    # ========================================================
    # LOAD CONFIGURATION
    # ========================================================

    @classmethod
    def load(cls):

        if not os.path.exists(CONFIG_FILE):

            return cls.DEFAULT.copy()

        try:

            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                if not isinstance(data, dict):

                    return cls.DEFAULT.copy()

                return data

        except Exception as e:

            print(
                f"Error loading academic configuration: {e}"
            )

            return cls.DEFAULT.copy()


    # ========================================================
    # SAVE CONFIGURATION
    # ========================================================

    @classmethod
    def save(cls, data):

        with open(
            CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )


    # ========================================================
    # GET REGULATION DEFAULT
    # ========================================================

    @classmethod
    def get_regulation_config(
        cls,
        regulation
    ):

        regulation = str(
            regulation
        ).strip()

        config = cls.load()

        if regulation in config:

            return config[regulation]

        # Future regulation fallback

        return {
            "unit_count": 5,

            "notes": "Unit-{unit} Notes",

            "assignments":
                "Unit-{unit} Assignment",

            "qa": [
                "Part-A MCQ-Q&A",
                "Part-B Q&A",
                "Part-C Questions"
            ]
        }


    # ========================================================
    # GET SUBJECT CONFIGURATION
    # ========================================================

    @classmethod
    def get_subject_config(
        cls,
        regulation,
        year=None,
        department=None,
        semester=None,
        subject=None
    ):

        config = cls.load()

        regulation = str(
            regulation
        ).strip()

        regulation_config = config.get(
            regulation
        )

        if not regulation_config:

            return cls.get_regulation_config(
                regulation
            )

        # ----------------------------------------------------
        # Subject-specific configuration
        # ----------------------------------------------------

        subjects = regulation_config.get(
            "subjects",
            {}
        )

        if subject:

            subject_key = subject.strip()

            if subject_key in subjects:

                return subjects[subject_key]

        # ----------------------------------------------------
        # Regulation default
        # ----------------------------------------------------

        return {
            "unit_count":
                regulation_config.get(
                    "unit_count",
                    5
                ),

            "notes":
                regulation_config.get(
                    "notes",
                    "Unit-{unit} Notes"
                ),

            "assignments":
                regulation_config.get(
                    "assignments",
                    "Unit-{unit} Assignment"
                ),

            "qa":
                regulation_config.get(
                    "qa",
                    []
                )
        }