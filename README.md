# Google Classroom Tracker

Hi! 👋 This app helps track whether staff are uploading **Notes, Assignments and Q&A** on time across all departments in Google Classroom — no more checking each class manually.

---

## What you can do

### 🔹 Regulation Setup
Set up the academic regulation (like 2021 or 2025): define the Q&A format (Part A, B, C) and which Years and Departments it applies to.

### 🔹 Due Date Setup
Pick a date on the **Academic Calendar**, choose the Year + Department, and set what is required (Notes, Assignments, Q&A). The app applies it to every class in that Year and Department — no need to do it one by one. Holidays and commencement dates can be marked on the same calendar.

### 🔹 Class Availability
Check which classes actually exist in Google Classroom for each Year, Department and Section, and spot any that are missing. This is helpful when a new department or section has not been added to Classroom yet. The result can be downloaded as Excel or PDF.

### 🔹 Reports
Once set up, download a simple report any time showing what is **Pending** ⏳ and what is **Completed** ✅:

- **Check Schedule Completion** — tap a scheduled due date to download its Pending and Completed reports, each as Excel and as PDF.
- **Check Naming Mismatches** — lists uploads whose names do not follow the standard format, grouped by department and course.
- **Home dashboard** — filter by Department, Year and Section, view each class's uploads, and download Excel for one class or for all classes.

### 🔹 Departments, Years and Sections
New departments, years and sections can be added straight from the dropdowns on the home screen (**Add new ...**), or managed in **Settings**.

---

## How it works (the short version)

1. The dean sets up a **regulation** and schedules **due dates** on the calendar.
2. Staff upload their material to Google Classroom.
3. The app reads Google Classroom, matches each upload to the requirement and decides if a subject is **Pending** or **Completed**.
4. Download the reports whenever you need them.

### How uploads should be named

The app reads the names of uploads in Google Classroom. Capital, small and sentence case are all fine.

| Material | Example name |
|---|---|
| Notes | `Unit-1 Notes` |
| Assignment | `Assignment-1` |
| Question & Answer | `Unit-1 Part-A Q&A` |

Uploads that do not follow the format can be found with **Check Naming Mismatches**.

---

## Built with

- **App:** Flutter (web and desktop)
- **Backend:** Python, FastAPI
- **Data:** Google Classroom API; the app's own settings are kept in JSON files in the `data/` folder
- **Reports:** openpyxl (Excel) and reportlab (PDF)

---

## Running it yourself

### Backend

1. Install Python 3 and the packages in `requirements.txt` (FastAPI, uvicorn, openpyxl, reportlab, google-api-python-client, google-auth-oauthlib).
2. Put your Google OAuth file `credentials.json` next to the backend code. Do **not** commit it, or `token.json`, to git.
3. Start the server (use **one worker**, because the data files and the report cache live on one machine):

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

4. The first time Google Classroom is used, a browser window opens to sign in with the Google account that can see the classes. This creates `token.json`.

### App

```bash
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

To build the web app:

```bash
flutter build web --release --dart-define=API_BASE_URL=https://your-server-address
```

`API_BASE_URL` falls back to `http://127.0.0.1:8000` when it is not set.

---

## Notes for whoever looks after it

- **Google sign-in:** if reports suddenly fail with a Google authorisation error, delete `token.json` and sign in again. While the Google app is in *Testing* mode the sign-in expires about every 7 days.
- **Data:** everything the dean sets up (regulations, due dates, holidays, the lists of departments, years and sections) is in the `data/` folder. Back it up regularly.
- **One server:** run a single backend process, and keep the backend and `data/` folder on the same machine.
- **Class names:** a Google Classroom class name needs the format `III-Yr V-Sem CSE A (2023-2027)` (year, semester, department, section) so the app can read it. Names that do not follow it are listed in **Class Availability**.

---

## Credits

**Developed by:** Ms. Inzeera Z — B.Tech (Hons.) Artificial Intelligence & Data Science, 2023–2027


*Arunachala College of Engineering for Women (ACEW) — Empowering academic excellence through digital innovation.*

Let me know if anything's unclear! 🙂
