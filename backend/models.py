from typing import List, Optional
from pydantic import BaseModel


# Material Model
class Material(BaseModel):
    title: str
    date: str


# QA Material model
class QAMaterial(BaseModel):
    unit: str
    part: str
    date: str


# Duplicate Model
class Duplicate(BaseModel):
    title: str
    count: int


# Pending Section
class PendingSection(BaseModel):
    uploaded: int
    total: int
    pending: List[str]


# Pending Result
class PendingResult(BaseModel):
    notes: PendingSection
    assignments: PendingSection
    qa: PendingSection
    status: str


# Duplicate Result
class DuplicateResult(BaseModel):
    notes: List[Duplicate]
    assignments: List[Duplicate]
    qa: List[Duplicate]


# Staff Record
class StaffRecord(BaseModel):
    class_name: str
    staff_name: str
    subject: str
    notes: List[Material]
    assignments: List[Material]
    qa: List[Material]
    duplicates: DuplicateResult
    pending: PendingResult


class DashboardSummary(BaseModel):
    total_classes: int
    total_staff: int
    completed_staff: int
    pending_staff: int
    total_notes: int
    total_assignments: int
    total_qa: int
    duplicate_uploads: int


class ClassroomResponse(BaseModel):
    summary: DashboardSummary
    records: List[StaffRecord]


class QaPart(BaseModel):
    part: str
    type: str


# years / departments: an empty list means "applies to all".
class RegulationPayload(BaseModel):
    name: str
    qa_parts: List[QaPart]
    years: List[str] = []
    departments: List[str] = []


class UnitOverridePayload(BaseModel):
    year: str
    department: str
    subject: str
    unit_count: int


class SubjectKey(BaseModel):
    year: str
    department: str
    semester: str
    section: str
    subject: str


class PairKey(BaseModel):
    year: str
    department: str


# A schedule is just a date, a regulation, the Year+Department pairs it
# applies to, and the required units. No subjects are stored.
class AcademicSchedulePayload(BaseModel):
    date: str
    regulation: str
    pairs: List[PairKey]
    notes_required_units: List[int] = []
    assignment_required_units: List[int] = []
    qa_required_units: List[int] = []


class HolidayPayload(BaseModel):
    date: str
    name: str


class CommencementPayload(BaseModel):
    date: str
    label: str