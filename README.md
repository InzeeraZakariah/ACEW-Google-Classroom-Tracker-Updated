<img width="1915" height="860" alt="image" src="https://github.com/user-attachments/assets/6627a714-621c-47b0-87c5-b4ffdc9bc6e5" />#  Google Classroom Tracker

Hi! 👋 This app helps track whether staff are uploading **Notes, Assignments and Q&A** on time across all departments in Google Classroom — no more checking each class manually.

---

<img width="1912" height="868" alt="image" src="https://github.com/user-attachments/assets/89c01feb-45e7-4105-b597-c59936bc1086" />
<img width="1907" height="857" alt="image" src="https://github.com/user-attachments/assets/3c10bae7-23eb-4189-8eb8-a3b5ff97b2ad" />
<img width="1885" height="850" alt="image" src="https://github.com/user-attachments/assets/7438e417-8b06-426e-8774-d7cb0ffd7cc2" />
<img width="1897" height="831" alt="image" src="https://github.com/user-attachments/assets/10d3ad9c-589c-4c33-8dcd-3e4613e05d2d" />
<img width="1907" height="855" alt="image" src="https://github.com/user-attachments/assets/8d6a20c7-849c-4e4e-b470-9e6a3f13c5f3" />
<img width="1915" height="860" alt="image" src="https://github.com/user-attachments/assets/98e109e4-3563-43fc-b385-8d5165496202" />


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
- **Data:** Google Classroom API for the classes; **Supabase** (PostgreSQL) for everything the app stores itself
- **Hosting:** the backend runs on **Render**; the database is on **Supabase**
- **Reports:** openpyxl (Excel) and reportlab (PDF)

---

## Running it yourself

### Backend

1. Install Python 3 and the packages in `requirements.txt` (FastAPI, uvicorn, openpyxl, reportlab, google-api-python-client, google-auth-oauthlib, plus the database package the backend uses for Supabase).
2. Put your Google OAuth file `credentials.json` next to the backend code. Do **not** commit it, or `token.json`, to git.
3. Give the backend the connection details of your Supabase project as environment variables (the names are in the backend code). Never commit them.
4. Start the server:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

5. The first time Google Classroom is used, a browser window opens to sign in with the Google account that can see the classes. This creates `token.json`.

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
- **Data:** everything the dean sets up (regulations, due dates, holidays, the lists of departments, years and sections) is in Supabase. Back it up regularly (see Hosting below).
- **Class names:** a Google Classroom class name needs the format `III-Yr V-Sem CSE A (2023-2027)` (year, semester, department, section) so the app can read it. Names that do not follow it are listed in **Class Availability**.

---

## Hosting

The backend runs on **Render** and the data lives in **Supabase**.

| Where | What to know |
|---|---|
| **Supabase** | On the Free plan, a project that gets too little activity for a week is paused, and the Free plan has no automatic backups. Paid plans are never paused and include daily backups. If the app goes unused for a long break, open the project in the Supabase dashboard to wake it. Export the data from time to time. |
| **Render** | On the Free plan the backend goes to sleep after a period without visits, so the first request afterwards can be slow. A paid plan keeps it running. |
| **Secrets** | Keep the Supabase connection details and the Google sign-in files in Render's environment / secret settings, never in git. Files saved to a Render service's own disk can be lost when it redeploys or restarts, unless a disk is attached. |

To update the live app: push the backend changes to git so Render redeploys; for the Flutter app, rebuild it with `flutter build web --release --dart-define=API_BASE_URL=<backend address>` and upload the new build to wherever it is hosted.

---

## Credits

**Developed by:** Ms. Inzeera Z — B.Tech (Hons.) Artificial Intelligence & Data Science, 2023–2027

