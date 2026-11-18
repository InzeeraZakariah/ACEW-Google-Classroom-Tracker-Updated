
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load local environment variables
load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "classroom-data")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials are missing from backend/.env")

# Connect to Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Local JSON directory
DATA_DIR = Path(__file__).parent / "data"

JSON_FILES = [
    "academic_schedule.json",
    "commencement_dates.json",
    "due_date.json",
    "holidays.json",
    "regulations.json",
    "subject_requirements.json",
    "subject_unit_overrides.json",
    "subjects.json",
]


def migrate_files():
    print("Starting JSON migration...\n")

    for filename in JSON_FILES:
        local_path = DATA_DIR / filename

        if not local_path.exists():
            raise FileNotFoundError(
                f"Missing local file: {local_path}"
            )

        # Read and validate the original JSON
        original_content = local_path.read_bytes()
        json.loads(original_content.decode("utf-8"))

        print(f"Uploading: {filename}")

        # Upload original file without modifying its contents
        supabase.storage.from_(BUCKET).upload(
            path=filename,
            file=original_content,
            file_options={
                "content-type": "application/json",
                "upsert": "true"
            }
        )

        # Download and verify the uploaded file
        downloaded_content = (
            supabase.storage.from_(BUCKET).download(filename)
        )

        if downloaded_content != original_content:
            raise RuntimeError(
                f"Verification failed: {filename}"
            )

        print(f"Verified: {filename}\n")

    print("Migration completed successfully!")
    print(f"Total files migrated: {len(JSON_FILES)}")


if __name__ == "__main__":
    migrate_files()
