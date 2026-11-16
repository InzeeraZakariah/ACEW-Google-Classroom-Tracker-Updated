import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/classroom.courses.readonly",]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR,"test_token.json")


def get_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        print("Loading test_token.json...")
        creds = Credentials.from_authorized_user_file(TOKEN_FILE,SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing Google token...")
        creds.refresh(Request())

    if not creds or not creds.valid:
        print("\nStarting Google authorization...")
        print("Select the Google account that has access to")
        print("your Google Classroom courses.\n")

        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE,SCOPES)
        creds = flow.run_local_server(port=8080)

        # Save separate test token
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

        print("\nTest token saved as:")
        print(TOKEN_FILE)

    # Build Classroom API service
    service = build("classroom","v1",credentials=creds)

    return service

# GET ALL COURSES
def get_all_courses(service):
    courses = []
    page_token = None
    print("\nFetching Google Classroom courses...\n")

    while True:
        response = (service.courses().list(pageSize=100,pageToken=page_token).execute())
        batch = response.get("courses", [])

        courses.extend(batch)

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return courses


# DISPLAY COURSES

def display_courses(courses):
    print("\n")
    print("=" * 80)
    print("GOOGLE CLASSROOM COURSE TEST")
    print("=" * 80)
    print(f"\nTOTAL COURSES FOUND: {len(courses)}\n")

    if not courses:
        print("NO COURSES FOUND.")
        print("\nPossible reasons:")
        print("1. Wrong Google account was authorized.")
        print("2. The account has no Classroom courses.")
        print("3. Classroom API access is not configured correctly.")
        print("4. The authorized account cannot access the courses.")

        print("\n" + "=" * 80)
        return

    for index, course in enumerate(courses,start=1):
        print(f"Course {index}")
        print("-" * 80)
        print("Name      :",course.get("name", ""))
        print("ID        :",course.get("id", ""))
        print("State     :",course.get("courseState", ""))
        print("Section   :",course.get("section", ""))
        print("Room      :",course.get("room", ""))
        print("Owner ID  :",course.get("ownerId", ""))
        print()
    print("=" * 80)
    print("COURSE RETRIEVAL TEST COMPLETED")
    print("=" * 80)


def main():
    print("\n")
    print("=" * 80)
    print("GOOGLE CLASSROOM API COURSE TEST")
    print("=" * 80)

    try:
        service = get_service()
        print("\nGoogle Classroom API connected successfully.")
        courses = get_all_courses(service)
        display_courses(courses)

    except Exception as e:
        print("\n")
        print("=" * 80)
        print("ERROR")
        print("=" * 80)
        print(type(e).__name__,":",e)
        print("=" * 80)


if __name__ == "__main__":
    main()