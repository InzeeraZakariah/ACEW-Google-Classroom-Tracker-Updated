from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from google_classroom import GoogleClassroom
from excel_generator import ExcelGenerator
from regulation_manager import RegulationManager
from due_date_report import DueDateReportBuilder
from models import RegulationPayload, UnitOverridePayload, AcademicSchedulePayload, HolidayPayload, CommencementPayload
from subject_unit_override_manager import SubjectUnitOverrideManager
from academic_schedule_manager import AcademicScheduleManager
from commencement_manager import CommencementManager
from holiday_manager import HolidayManager
from subject_unit_report import SubjectUnitReportBuilder
from filter_manager import FilterManager, DuplicateError, KINDS
import class_availability 
from unit_summary import compute_unit_summary
from naming_checking import find_mismatches
from naming_report import NamingReportBuilder
from typing import List, Optional, Tuple
import time
import threading

app = FastAPI(
    title="Google Classroom Monitoring API",
    version="1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://acew-classroom-frontend.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gc = GoogleClassroom()

# Filter the department, Year, Section
# below shows up in every dropdown.
@app.get("/filters")
def get_filters():
    return FilterManager.get_all()


def _check_kind(kind: str):
    if kind not in KINDS:
        raise HTTPException(status_code=404, detail=f"Unknown filter '{kind}' - use one of {list(KINDS)}")


@app.post("/filters/{kind}")
def add_filter_option(kind: str, value: str = Body(..., embed=True)):
    """
    Adds a department, year or section. kind is 'departments', 'years'
    or 'sections'; body is {"value": "MECH"}.
    """
    _check_kind(kind)
    try:
        FilterManager.add(kind, value)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FilterManager.get_all()


@app.delete("/filters/{kind}/{value}")
def remove_filter_option(kind: str, value: str):
    """
    Removes a department, year or section. Does NOT cascade — saved
    schedules, overrides and regulations that mention it are left
    as-is. Names containing '&' (e.g. AI&DS) must be URL-encoded.
    """
    _check_kind(kind)
    try:
        removed = FilterManager.remove(kind, value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not removed:
        raise HTTPException(status_code=404, detail=f"'{value}' not found in {kind}")
    return FilterManager.get_all()


# -------------------------------------------------
# CLASS AVAILABILITY — is the class present in Google Classroom?
# -------------------------------------------------
# year / department / section are each optional; leaving one out (or
# sending "All") means every value of that filter. So year=III &
# department=CSE & section=A checks one class, while year=III alone
# checks every department and section of III year.
def _availability(year, department, section):
    filters = FilterManager.get_all()

    def pick(value, every):
        if not value or value.strip().lower() == "all":
            return list(every)
        return [value.strip().upper()]

    departments = pick(department, filters["departments"])
    years = pick(year, filters["years"])
    sections = pick(section, filters["sections"])

    entries = [{"name": d, "years": years, "sections": sections} for d in departments]
    scope = (
        f"Year: {', '.join(years) if len(years) == 1 else 'All'} | "
        f"Department: {departments[0] if len(departments) == 1 else 'All'} | "
        f"Section: {sections[0] if len(sections) == 1 else 'All'}"
    )

    course_names = [c.get("name", "") for c in gc.get_courses()]
    return class_availability.check(course_names, entries), scope


@app.get("/class-availability")
def class_availability_check(
    year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
):
    result, scope = _availability(year, department, section)
    return {
        "scope": scope,
        "summary": result["summary"],
        "missing": class_availability.missing_list(result),
    }


@app.get("/class-availability/pdf")
def class_availability_pdf(
    year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
):
    """PDF listing only the classes NOT found in Google Classroom."""
    result, scope = _availability(year, department, section)
    buffer = class_availability.build_missing_pdf(result, scope)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Unavailable_Classes.pdf"},
    )



# Fetch Complete Data
@app.get("/classroom-data")
def classroom_data(department: str = Query(None), year: str = Query(None), section: str = Query(None)):
    return gc.fetch_staff_data(department, year, section)

# Dashboard Summary
@app.get("/dashboard")
def dashboard():
    return gc.dashboard()

# Search Staff
@app.get("/search")
def search(keyword: str):
    return gc.search_staff(keyword)

# Download Excel for one class 
@app.get("/download-excel")
def download_excel(department: str = Query(None), year: str = Query(None), section: str = Query(None)):
    records = gc.fetch_selected_excel_data(department, year, section)
    file_name = ExcelGenerator.generate(records)
    downloaded_filename = f"ACEW_{year} {department} {section}_Classroom_Report.xlsx" 
    return FileResponse(
        path=file_name,
        filename=downloaded_filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# download excel for all classes
@app.get("/download-all")
def download_all_excel():
    data = gc.fetch_all_staff_data()
    file_name = ExcelGenerator.generate(data["records"])

    return FileResponse(
        path=file_name,
        filename="ACEW_All_Classroom_Report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

TRACKED_SECTION = "A"
 
 
def _parse_pairs(value: str) -> List[Tuple[str, str]]:
    """
    "III:CSE,II:IT" -> [("III", "CSE"), ("II", "IT")] — explicit
    Year:Department pairs, comma-separated. This is deliberately NOT
    two separate comma-lists (year=... & department=...), because that
    shape cross-multiplies: choosing Years [III, II] and Departments
    [CSE, IT] separately would wrongly expand to all four combinations
    instead of just the two pairs the dean actually picked.
    """
    pairs = []
    for piece in value.split(","):
        piece = piece.strip()
        if not piece or ":" not in piece:
            continue
        year, department = piece.split(":", 1)
        year, department = year.strip(), department.strip()
        if year and department:
            pairs.append((year, department))
    return pairs
 
 
# -------------
# REGULATIONS
# -------------
@app.get("/regulations")
def get_regulations():
    return RegulationManager.list_regulations()
 
 
@app.post("/regulations")
def save_regulation(payload: RegulationPayload):
    return RegulationManager.save_regulation(
        name=payload.name,
        qa_parts=[part.dict() for part in payload.qa_parts],
        years=payload.years,
        departments=payload.departments,
    )
 
 
@app.delete("/regulations/{name}")
def delete_regulation(name: str):
    """
    Deletes a regulation. Does NOT cascade — any SubjectRequirement
    records or academic-schedule entries that reference this
    regulation by name are left as-is.
    """
    deleted = RegulationManager.delete_regulation(name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return {"deleted": name}
 
 
# ---------------------
# SUBJECT UNIT COUNTS
# ---------------------
@app.get("/subject-unit-counts")
def get_subject_unit_counts(
    pairs: str = Query(..., description="Comma-separated Year:Department pairs, e.g. 'III:CSE,II:IT'"),
):
    parsed_pairs = _parse_pairs(pairs)
 
    result = []
    for year, department in parsed_pairs:
        records = GoogleClassroom().fetch_staff_data(department=department, year=year)["records"]
        for record in records:
            if (record.get("section") or "").upper() != TRACKED_SECTION:
                continue
 
            subject = record.get("subject", "")
            override = SubjectUnitOverrideManager.get_override(year, department, subject)
            summary = compute_unit_summary(record, override_unit_count=override)
            result.append({
                "year": record.get("year"),
                "department": record.get("department"),
                "semester": record.get("semester"),
                "section": record.get("section"),
                "class_name": record.get("class_name"),
                "subject": subject,
                "staff_name": record.get("staff_name"),
                **summary,
            })
 
    return result
 
 
@app.get("/subject-unit-counts/excel")
def download_subject_unit_counts(
    pairs: str = Query(..., description="Comma-separated Year:Department pairs, e.g. 'III:CSE,II:IT'"),
):
    parsed_pairs = _parse_pairs(pairs)
 
    records = []
    for year, department in parsed_pairs:
        section_records = GoogleClassroom().fetch_staff_data(department=department, year=year)["records"]
        records.extend(
            r for r in section_records
            if (r.get("section") or "").upper() == TRACKED_SECTION
        )
 
    buffer = SubjectUnitReportBuilder.build(records)
 
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=subject_unit_counts.xlsx"},
    )
 
 
@app.post("/subject-unit-counts/override")
def set_subject_unit_override(payload: UnitOverridePayload):
    """
    Manually corrects a subject's unit count — subject NAMES always
    come from Google Classroom and are never editable here.
    """
    return SubjectUnitOverrideManager.set_override(
        payload.year, payload.department, payload.subject, payload.unit_count
    )
 
 
@app.delete("/subject-unit-counts/override")
def clear_subject_unit_override(
    year: str = Query(...),
    department: str = Query(...),
    subject: str = Query(...),
):
    deleted = SubjectUnitOverrideManager.clear_override(year, department, subject)
    if not deleted:
        raise HTTPException(status_code=404, detail="Override not found")
    return {"deleted": True}
 
 
# -----------------
# ACADEMIC SCHEDULE
# -----------------
# Saving a due date only STORES it: date, regulation, Year+Department
# pairs and required units. Nothing is loaded from Google Classroom
# here. Classroom is read later, when the Pending/Completed reports
# are downloaded (see /due-date-report below).
@app.get("/academic-schedule")
def get_academic_schedule(regulation: Optional[str] = Query(None)):
    return AcademicScheduleManager.list_entries(regulation)
 
 
@app.get("/academic-schedule/{date}")
def get_academic_schedule_entry(date: str):
    entry = AcademicScheduleManager.get_entry(date)
    if entry is None:
        raise HTTPException(status_code=404, detail="No schedule for this date")
    return entry
 
 
@app.post("/academic-schedule")
def save_academic_schedule(payload: AcademicSchedulePayload):
    if not payload.pairs:
        raise HTTPException(
            status_code=400,
            detail="Add at least one Year + Department combination",
        )
 
    return AcademicScheduleManager.save_entry(
        date=payload.date,
        regulation=payload.regulation,
        pairs=[p.dict() for p in payload.pairs],
        notes_required_units=payload.notes_required_units,
        assignment_required_units=payload.assignment_required_units,
        qa_required_units=payload.qa_required_units,
    )
 
 
@app.delete("/academic-schedule/{date}")
def delete_academic_schedule(date: str):
    deleted = AcademicScheduleManager.delete_entry(date)
    if not deleted:
        raise HTTPException(status_code=404, detail="No schedule for this date")
    return {"deleted": date}
 
 
# ----------------------------------------------------
# DUE DATE REPORT — two workbooks: Pending and Completed
# ----------------------------------------------------
_REPORT_RECORDS_TTL_SECONDS = 60
_report_records_cache: dict = {}  # pairs key -> (timestamp, {pair: records})
_report_records_lock = threading.Lock()
 
 
def _records_for_pairs(pairs):
    """
    {(year, department): [records of EVERY section]} for exactly the
    given pairs — the only place Google Classroom is read. Choosing
    III + CSE covers sections A, B, ... alike. Grouping by the
    pair that was requested means matching never depends on how a
    record spells its own year/department.
 
    The lock is held across the fetch on purpose: the Pending and
    Completed requests arrive back-to-back, and the second waits and
    reuses the first one's result instead of hitting Classroom again.
    """
    key = tuple(sorted(set(pairs)))
 
    with _report_records_lock:
        now = time.time()
        hit = _report_records_cache.get(key)
        if hit is not None and now - hit[0] < _REPORT_RECORDS_TTL_SECONDS:
            return hit[1]
 
        classroom = GoogleClassroom()
        by_pair = {}
        for year, department in key:
            by_pair[(year, department)] = classroom.fetch_staff_data(
                department=department, year=year
            )["records"]
 
        _report_records_cache[key] = (now, by_pair)
        return by_pair
 
 
@app.get("/due-date-report")
def download_due_date_report(
    regulation: str = Query(...),
    status: str = Query(..., description="'Pending' or 'Completed'"),
    date: Optional[str] = Query(None, description="Only this scheduled due date (YYYY-MM-DD)"),
    fmt: str = Query("xlsx", alias="format", description="'xlsx' or 'pdf'"),
):
    """
    The subjects whose upload status matches `status`, as an .xlsx
    workbook (one sheet per course, so each section of a class gets
    its own sheet) or, with format=pdf, a portrait A4 PDF of the same
    tables.
 
    - With `date`: that schedule entry only.
    - Without `date`: every schedule entry saved under the regulation.
 
    Only the Year+Department pairs of those entries are fetched from
    Google Classroom. The app calls this twice — Pending, then
    Completed.
    """
    normalized_status = status.strip().capitalize()
    if normalized_status not in ("Pending", "Completed"):
        raise HTTPException(status_code=400, detail="status must be 'Pending' or 'Completed'")
 
    fmt = fmt.strip().lower()
    if fmt not in ("xlsx", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'xlsx' or 'pdf'")
 
    regulation_record = RegulationManager.get_regulation(regulation)
    if regulation_record is None:
        raise HTTPException(status_code=404, detail="Regulation not found")
 
    if date:
        entry = AcademicScheduleManager.get_entry(date)
        if entry is None or entry.get("regulation") != regulation:
            raise HTTPException(status_code=404, detail="No schedule for this date and regulation")
        entries = [entry]
    else:
        entries = AcademicScheduleManager.list_entries(regulation)
 
    pairs = [pair for entry in entries for pair in AcademicScheduleManager.pairs_of(entry)]
    records_by_pair = _records_for_pairs(pairs) if pairs else {}
 
    if fmt == "pdf":
        buffer = DueDateReportBuilder.build_pdf(
            records_by_pair, regulation_record, entries, normalized_status
        )
        media_type = "application/pdf"
    else:
        buffer = DueDateReportBuilder.build(
            records_by_pair, regulation_record, entries, normalized_status
        )
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
 
    suffix = f"_{date}" if date else ""
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={
            "Content-Disposition":
                f"attachment; filename=due_date_report_{normalized_status.lower()}{suffix}.{fmt}"
        },
    )
 
 
# ------------------------------------------------
# NAMING MISMATCHES — uploads not in the standard format
# ------------------------------------------------
@app.get("/naming-mismatches")
def download_naming_mismatches(
    pairs: str = Query(..., description="Comma-separated Year:Department pairs, e.g. 'III:CSE,II:IT'"),
    fmt: str = Query("xlsx", alias="format", description="'xlsx' or 'pdf'"),
):
    """
    Every uploaded item (notes / assignment / QA) in the given
    Year+Department pairs — all sections — whose title doesn't follow
    the standard naming format (see naming_checker.py). Returned as an
    Excel workbook (one sheet per department, one table per course) or
    a portrait PDF. Classroom is read only for the given pairs.
    """
    parsed_pairs = _parse_pairs(pairs)
    if not parsed_pairs:
        raise HTTPException(status_code=400, detail="Pick at least one Year + Department combination")
 
    fmt = fmt.strip().lower()
    if fmt not in ("xlsx", "pdf"):
        raise HTTPException(status_code=400, detail="format must be 'xlsx' or 'pdf'")
 
    rows = find_mismatches(_records_for_pairs(parsed_pairs))
 
    if fmt == "pdf":
        buffer = NamingReportBuilder.build_pdf(rows)
        media_type = "application/pdf"
    else:
        buffer = NamingReportBuilder.build_xlsx(rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
 
    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=naming_mismatches.{fmt}"},
    )
 
 
# ----------
# HOLIDAYS
# ----------
@app.get("/holidays")
def get_holidays():
    return HolidayManager.list_holidays()
 
 
@app.post("/holidays")
def add_holiday(payload: HolidayPayload):
    return HolidayManager.add_holiday(payload.date, payload.name)
 
 
@app.delete("/holidays/{date}")
def delete_holiday(date: str):
    deleted = HolidayManager.delete_holiday(date)
    if not deleted:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return {"deleted": date}
 
 
@app.post("/holidays/seed-indian")
def seed_indian_holidays(year: int = Query(...)):
    """
    Adds India's fixed-date national/widely-observed holidays for the
    given year. Movable, lunar-calendar holidays (Diwali, Holi, Eid,
    etc.) shift every year and aren't included — add those manually.
    """
    return HolidayManager.seed_indian_national_holidays(year)
 
 
# -------------------
# COMMENCEMENT DATES
# -------------------
@app.get("/commencement-dates")
def get_commencement_dates():
    return CommencementManager.list_all()
 
 
@app.post("/commencement-dates")
def add_commencement_date(payload: CommencementPayload):
    return CommencementManager.add(payload.date, payload.label)
 
 
@app.delete("/commencement-dates/{date}")
def delete_commencement_date(date: str):
    deleted = CommencementManager.delete(date)
    if not deleted:
        raise HTTPException(status_code=404, detail="Commencement date not found")
    return {"deleted": date}
 
@app.get("/")
def health():
    return {"message":"ACEW Google Classroom Tracker is running"}
