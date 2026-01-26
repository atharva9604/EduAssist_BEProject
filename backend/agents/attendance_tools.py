from typing import List
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, case
import json
import pandas as pd
from sqlalchemy import text

from database.connection import SessionLocal
from database.models.attendance import (
    Teacher,
    DepartmentSemester,
    AttendanceClass,
    AttendanceSubject,
    AttendanceStudent,
    AttendanceSession,
    AttendanceRecord,
)


# -------------------------------------------------
# Helper functions
# -------------------------------------------------
def expand_roll_spec(spec: str) -> List[int]:
    """
    Expand roll-number patterns like "1,2,5-10 except 7"
    into a clean list of integers.
    """
    spec = (spec or "").lower().replace("except", "|except|")
    tokens = [t.strip() for t in spec.replace(",", " ").split() if t.strip()]
    include, exclude, mode = [], [], "include"
    for t in tokens:
        if t == "|except|":
            mode = "exclude"
            continue
        if "-" in t:
            a, b = t.split("-")
            nums = list(range(int(a), int(b) + 1))
        else:
            nums = [int(t)]
        (exclude if mode == "exclude" else include).extend(nums)
    return sorted(set(include) - set(exclude))


def iso(s: str | None) -> str:
    """
    Normalize various date formats to ISO (YYYY-MM-DD).
    """
    if not s or s.lower() == "today":
        return date.today().isoformat()
    if "-" in s and len(s.split("-")[0]) == 2:  # DD-MM-YYYY → YYYY-MM-DD
        dd, mm, yy = s.split("-")
        return f"{yy}-{mm}-{dd}"
    return s


# -------------------------------------------------
# Pydantic input models
# -------------------------------------------------
class CreateSessionIn(BaseModel):
    teacher_id: int
    class_id: int
    subject_id: int
    date_str: str = Field(default_factory=lambda: date.today().isoformat())


class MarkIn(BaseModel):
    session_id: int | None = None
    teacher_id: int | None = None
    class_id: int | None = None
    subject_id: int | None = None
    date_str: str | None = None
    present_rolls: str


class SummaryIn(BaseModel):
    subject_id: int


class ExportIn(BaseModel):
    subject_id: int


# -------------------------------------------------
# Internal helper
# -------------------------------------------------
def _parse_payload(model: type[BaseModel], payload: str | dict) -> BaseModel:
    """Accept either JSON string payload or a dict payload."""
    if isinstance(payload, str):
        return model.model_validate_json(payload)
    return model.model_validate(payload)

def _maybe_bump_pk_sequence(db: Session, table_name: str) -> None:
    """
    If running on PostgreSQL and IDs were inserted manually, ensure the sequence is bumped
    to at least MAX(id). This prevents future inserts failing with duplicate keys.
    """
    try:
        if db.bind is None or db.bind.dialect.name != "postgresql":
            return
        db.execute(
            text(
                """
                SELECT setval(
                  pg_get_serial_sequence(:tbl, 'id'),
                  COALESCE((SELECT MAX(id) FROM """ + table_name + """), 1),
                  true
                );
                """
            ),
            {"tbl": table_name},
        )
        db.commit()
    except Exception:
        # Best-effort only; don't fail business logic on sequence bump
        db.rollback()


def ensure_attendance_base(
    db: Session,
    teacher_id: int,
    class_id: int,
    subject_id: int,
    *,
    dept_sem_id: int = 1,
) -> None:
    """
    Ensure FK targets exist so attendance operations never fail with FK violations.
    Creates default rows if missing:
    - attendance_dept_semesters id=dept_sem_id
    - attendance_teachers id=teacher_id
    - attendance_classes id=class_id
    - attendance_subjects id=subject_id
    """
    # Dept/Semester
    dept = db.query(DepartmentSemester).filter(DepartmentSemester.id == dept_sem_id).first()
    if not dept:
        db.add(DepartmentSemester(id=dept_sem_id, department="General", semester=1))

    # Teacher
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        db.add(Teacher(id=teacher_id, name=f"Teacher {teacher_id}", email=None))

    # Class
    cls = db.query(AttendanceClass).filter(AttendanceClass.id == class_id).first()
    if not cls:
        db.add(
            AttendanceClass(
                id=class_id,
                division="A",
                teacher_id=teacher_id,
                dept_sem_id=dept_sem_id,
            )
        )

    # Subject
    subj = db.query(AttendanceSubject).filter(AttendanceSubject.id == subject_id).first()
    if not subj:
        db.add(
            AttendanceSubject(
                id=subject_id,
                name=f"Subject {subject_id}",
                dept_sem_id=dept_sem_id,
            )
        )

    db.commit()

    # Keep sequences sane if IDs were inserted manually
    _maybe_bump_pk_sequence(db, "attendance_dept_semesters")
    _maybe_bump_pk_sequence(db, "attendance_teachers")
    _maybe_bump_pk_sequence(db, "attendance_classes")
    _maybe_bump_pk_sequence(db, "attendance_subjects")


def _get_or_create_session(db: Session, t: int, c: int, s: int, d: str) -> int:
    # Ensure FK rows exist before session creation
    ensure_attendance_base(db, teacher_id=t, class_id=c, subject_id=s)
    d_iso = iso(d)
    sess = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.teacher_id == t,
            AttendanceSession.class_id == c,
            AttendanceSession.subject_id == s,
            AttendanceSession.date == date.fromisoformat(d_iso),
        )
        .first()
    )
    if not sess:
        sess = AttendanceSession(
            teacher_id=t, class_id=c, subject_id=s, date=date.fromisoformat(d_iso)
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
    return sess.id


# -------------------------------------------------
# Operations (no LangChain dependency)
# -------------------------------------------------
def create_session(payload: str | dict) -> dict:
    """
    Create a class session for a specific teacher, class, and subject on a given date.
    Input:  {"teacher_id":1, "class_id":1, "subject_id":1, "date_str":"2025-10-20"}
    Output: {"session_id":3, "message":"Session created"}
    """
    db = SessionLocal()
    try:
        args = _parse_payload(CreateSessionIn, payload)
        ensure_attendance_base(db, teacher_id=args.teacher_id, class_id=args.class_id, subject_id=args.subject_id)
        sess = AttendanceSession(
            teacher_id=args.teacher_id,
            class_id=args.class_id,
            subject_id=args.subject_id,
            date=date.fromisoformat(iso(args.date_str)),
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
        return {"session_id": sess.id, "message": "Session created"}
    finally:
        db.close()


def mark_attendance(payload: str | dict) -> dict:
    """
    Mark attendance for a session using either session_id or (teacher_id, class_id, subject_id, date_str).
    Accepts roll patterns like '1-10 except 7'.
    Input:  {"session_id":1, "present_rolls":"1,2,3,5-10 except 7"}
    Output: {"session_id":1, "present":9, "total":10}
    """
    db = SessionLocal()
    try:
        args = _parse_payload(MarkIn, payload)
        if not args.session_id:
            for k in ["teacher_id", "class_id", "subject_id"]:
                if getattr(args, k) is None:
                    return {"error": f"Missing {k}"}
            sid = _get_or_create_session(
                db,
                args.teacher_id,
                args.class_id,
                args.subject_id,
                args.date_str or "today",
            )
        else:
            sid = args.session_id

        sess = db.query(AttendanceSession).filter(AttendanceSession.id == sid).first()
        if not sess:
            return {"error": "Invalid session_id"}

        students = db.query(AttendanceStudent).filter(AttendanceStudent.class_id == sess.class_id).all()
        rolls = set(expand_roll_spec(args.present_rolls))

        db.query(AttendanceRecord).filter(AttendanceRecord.session_id == sid).delete()
        for s in students:
            status = "Present" if s.roll_no in rolls else "Absent"
            db.add(AttendanceRecord(session_id=sid, student_id=s.id, status=status))
        db.commit()
        present_count = sum(1 for s in students if s.roll_no in rolls)
        return {"session_id": sid, "present": present_count, "total": len(students)}
    finally:
        db.close()


def summary(payload: str | dict) -> dict:
    """
    Generate a subject-wise summary showing each student's total classes and attendance percentage.
    Input:  {"subject_id":1}
    Output: {"summary":[{"roll_no":1,"name":"Asha","percentage":95.0},...]}
    """
    db = SessionLocal()
    try:
        args = _parse_payload(SummaryIn, payload)
        rows = (
            db.query(
                AttendanceStudent.roll_no,
                AttendanceStudent.name,
                func.count(AttendanceRecord.id).label("total"),
                func.sum(case((AttendanceRecord.status == "Present", 1), else_=0)).label(
                    "present"
                ),
            )
            .join(AttendanceRecord, AttendanceStudent.id == AttendanceRecord.student_id)
            .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
            .filter(AttendanceSession.subject_id == args.subject_id)
            .group_by(AttendanceStudent.roll_no, AttendanceStudent.name)
            .order_by(AttendanceStudent.roll_no.asc())
            .all()
        )

        data = []
        for r in rows:
            pct = round((r.present / r.total) * 100, 2) if r.total else 0.0
            data.append(
                {
                    "roll_no": r.roll_no,
                    "name": r.name,
                    "total": int(r.total),
                    "present": int(r.present),
                    "percentage": pct,
                }
            )
        return {"summary": data}
    finally:
        db.close()


def export_csv(payload: str | dict) -> dict:
    """
    Export the attendance summary for a subject to a CSV file.
    Input:  {"subject_id":1}
    Output: {"file_path": "storage/attendance_summary_subject_1.csv"}
    """
    args = _parse_payload(ExportIn, payload)
    rows = summary({"subject_id": args.subject_id}).get("summary", [])
    if not rows:
        return {"file_path": None, "status": "NO_DATA"}

    df = pd.DataFrame(rows)
    fn = f"storage/attendance_summary_subject_{args.subject_id}.csv"
    import os
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    df.to_csv(fn, index=False)
    return {"file_path": fn}


# Backwards-compatible aliases (older CrewAI integration used these names)
create_session_tool = create_session
mark_attendance_tool = mark_attendance
summary_tool = summary
export_csv_tool = export_csv
