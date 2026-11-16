"""
Run this file locally to generate token.json for Google Classroom.

Requirements:
    pip install -r requirements.txt

Place your downloaded Google OAuth Desktop client JSON file beside this
script and name it credentials.json.

Do not upload credentials.json or token.json to GitHub.
"""

import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
    "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
    "https://www.googleapis.com/auth/classroom.topics.readonly",
    "https://www.googleapis.com/auth/classroom.profile.emails",
]

BASE_DIR = Path(__file__).resolve().parent

CREDENTIALS_FILE = Path(
    os.getenv("GOOGLE_CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))
)
TOKEN_FILE = Path(
    os.getenv("GOOGLE_TOKEN_FILE", str(BASE_DIR / "token.json"))
)


def main():
    if not CREDENTIALS_FILE.is_file():
        raise FileNotFoundError(
            f"OAuth client file not found: {CREDENTIALS_FILE}\n"
            "Download your OAuth Desktop client JSON from Google Cloud "
            "and save it as credentials.json beside this script."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        SCOPES
    )

    # Requests offline access so the token includes a refresh token.
    # The browser opens only when this script is run locally.
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent"
    )

    if not credentials.refresh_token:
        raise RuntimeError(
            "Google did not return a refresh token. Revoke the app's access "
            "from your Google Account permissions and run this script again."
        )

    if not credentials.has_scopes(SCOPES):
        raise RuntimeError(
            "The generated token is missing one or more required scopes. "
            "Check the OAuth consent screen and regenerate the token."
        )

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    print(f"OAuth token created successfully: {TOKEN_FILE}")
    print("Keep this file private. Do not commit it to GitHub.")


if __name__ == "__main__":
    main()
