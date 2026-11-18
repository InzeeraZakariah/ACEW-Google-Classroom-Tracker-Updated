import os
import json
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client

# Load local .env when running on your computer.
# Render environment variables are read automatically.
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "classroom-data")


@lru_cache(maxsize=1)
def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL or SUPABASE_KEY is missing."
        )

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def load_json(filename):
    """
    Download a JSON file from Supabase Storage and return
    its contents as a Python object.
    """
    try:
        client = get_supabase_client()

        response = client.storage.from_(SUPABASE_BUCKET).download(filename)

        return json.loads(response.decode("utf-8"))

    except Exception as e:
        raise RuntimeError(
            f"Could not load {filename} from Supabase: {e}"
        ) from e


def save_json(filename, data):
    """
    Convert a Python object to JSON and upload it to Supabase.
    Existing files are overwritten.
    """
    try:
        client = get_supabase_client()

        json_content = json.dumps(
            data,
            ensure_ascii=False,
            indent=4
        ).encode("utf-8")

        client.storage.from_(SUPABASE_BUCKET).upload(
            path=filename,
            file=json_content,
            file_options={
                "upsert": "true",
                "content-type": "application/json"
            }
        )

    except Exception as e:
        raise RuntimeError(
            f"Could not save {filename} to Supabase: {e}"
        ) from e