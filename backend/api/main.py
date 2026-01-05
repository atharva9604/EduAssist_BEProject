from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
load_dotenv()  # reads backend/.env or project .env if present

# Prefer Gemini API key (google.generativeai)
import google.generativeai as genai
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")
genai.configure(api_key=API_KEY)

# Import agents
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import re
import csv
import json

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from agents.content_analyzer_agent import ContentAnalyzer
from agents.question_generator_agent import QuestionGenerator
from agents.ppt_generator_agent import PPTContentGenerator
from utils.ppt_creator import PPTCreator
from utils.syllabus_store import save_syllabus_pdf, retrieve_topic_context
from database.connection import get_db
from database.models.calendar_event import CalendarEvent as CalendarEventDB
from database.models.task import Task as TaskDB
from database.models.simple_todo import SimpleTodo as SimpleTodoDB
from database.models.subject import Subject as SubjectDB
from database.models.user import User
from sqlalchemy.orm import Session
from fastapi import Depends
from sqlalchemy import and_, or_

app = FastAPI(title="EduAssist Question Paper Generator API")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
content_analyzer = ContentAnalyzer()
question_generator = QuestionGenerator()
content_generator = PPTContentGenerator()

# Request/Response Models
class ContentAnalysisRequest(BaseModel):
    content: str
    document_type: str = "text"

class QuestionGenerationRequest(BaseModel):
    content: str
    requirements: Dict
    document_type: str = "text"

class QuestionPaperRequest(BaseModel):
    content: str
    document_type: str = "text"
    num_mcq: int = 5
    num_short: int = 3
    num_long: int = 2
    marks_mcq: int = 1
    marks_short: int = 3
    marks_long: int = 5
    difficulty: str = "medium"

# PPT request/response models
class PPTGenerationRequest(BaseModel):
    topic: str
    content: str
    subject: Optional[str] = None
    module: Optional[str] = None
    num_slides: int = 8

class PPTMultiTopicRequest(BaseModel):
    topics: List[str]
    subject: str
    num_slides: Optional[int] = None

class PPTResponse(BaseModel):
    success: bool
    message: str
    presentation_id: Optional[str] = None
    file_path: Optional[str] = None

# ========= Calendar/Timetable models =========
class CalendarEventResponse(BaseModel):
    id: str
    title: str
    start: str  # ISO datetime
    end: str    # ISO datetime
    location: Optional[str] = None
    description: Optional[str] = None
    allDay: Optional[bool] = None

class TaskItem(BaseModel):
    id: str
    title: str
    due_date: str  # ISO date YYYY-MM-DD
    done: bool = False

class TodayOverview(BaseModel):
    date: str
    events: List[CalendarEventResponse]
    tasks: List[TaskItem]

class SimpleTodoItem(BaseModel):
    id: Optional[str] = None
    text: str
    done: bool = False

class SubjectItem(BaseModel):
    id: Optional[str] = None
    name: str
    code: Optional[str] = None

# ========= Calendar/Timetable helpers =========
CAL_STORAGE_DIR = Path("storage/calendar")
CAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_PATH = CAL_STORAGE_DIR / "events.json"
TASKS_PATH = CAL_STORAGE_DIR / "tasks.json"

def _load_json(path: Path, default: Any):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _parse_dt(value: str) -> datetime:
    value = (value or "").strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    for fmt in ("%Y-%m-%d",):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {value}")

# Weekday helpers for grid-style timetable
DAY_IDX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

def _next_weekday(base: date, target_weekday: int) -> date:
    # Monday=0 ... Sunday=6
    days_ahead = (target_weekday - base.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base + timedelta(days=days_ahead)

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "EduAssist Question Paper Generator API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/analyze-content")
async def analyze_content(request: ContentAnalysisRequest):
    """Analyze document content and extract key information"""
    try:
        result = content_analyzer.analyze_content(
            request.content, 
            request.document_type
        )
        return {
            "success": True,
            "analysis": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# PPT Generation Endpoints

@app.post("/api/generate-ppt", response_model=PPTResponse)
async def generate_ppt(request: PPTGenerationRequest):
    try:
        effective_content = request.content
        from_syllabus_context = None
        if not effective_content or not effective_content.strip():
            retrieved = retrieve_topic_context(request.topic, request.module, request.subject, max_chars=3500)
            if retrieved:
                from_syllabus_context = f"Syllabus (for reference):\n{retrieved}"
            effective_content = ""

        if not request.content.strip():
            extra_prompt = f"""
You are an expert teacher. Your task is to generate a complete, educational PowerPoint presentation for the topic: '{request.topic}', subject: '{request.subject or 'General'}', module: '{request.module or 'N/A'}'.

- You must use your own knowledge to create detailed, classroom-style slides.
- The content below (if present) is syllabus reference. Use it only to guide you or check for alignment, but DO NOT simply copy wording or bullet points verbatim.
- If syllabus content isn't available, rely on your own expertise.
- Always explain, elaborate, and create clear slide points for a teacher to present.
"""
            base = from_syllabus_context or "(No syllabus context provided)"
            final_content = f"{extra_prompt}\n\n{base}"
        else:
            final_content = effective_content

        slide_data = content_generator.generate_slide_content(
            topic=request.topic,
            content=final_content,
            num_slides=request.num_slides,
            subject=request.subject,
            module=request.module,
        )

        storage_dir = Path("storage/presentations")
        creator = PPTCreator(str(storage_dir))
        file_path = creator.create_presentation(slide_data)

        return PPTResponse(
            success=True,
            message=f"Presentation generated for topic: {request.topic}",
            presentation_id=os.path.basename(file_path),
            file_path=str(file_path),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-ppt-multi", response_model=PPTResponse)
async def generate_ppt_multi(request: PPTMultiTopicRequest):
    try:
        slide_data = content_generator.generate_slides_for_topics(
            request.topics,
            request.subject,
            total_slides=request.num_slides,
            min_slides_per_topic=3,
        )

        storage_dir = Path("storage/presentations")
        creator = PPTCreator(str(storage_dir))
        file_path = creator.create_presentation(slide_data)

        return PPTResponse(
            success=True,
            message=f"Presentation generated for topics: {', '.join(request.topics)}",
            presentation_id=os.path.basename(file_path),
            file_path=str(file_path),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/list-presentations")
async def list_presentations():
    creator = PPTCreator("storage/presentations")
    return {"presentations": creator.list_presentations()}

@app.post("/api/upload-syllabus")
async def upload_syllabus(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    data = await file.read()
    path = save_syllabus_pdf(data, filename=file.filename)
    return {"success": True, "path": path}

@app.get("/api/download-ppt/{filename}")
async def download_ppt(filename: str):
    file_path = Path("storage/presentations") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

# ========= Timetable (CSV) and Calendar endpoints =========

@app.post("/api/upload-timetable")
async def upload_timetable(
    file: UploadFile = File(...), 
    scope: Optional[str] = None, 
    day: Optional[str] = None, 
    mode: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: str = "default",  # TODO: Get from Firebase token later
    db: Session = Depends(get_db)
):

    semester_start = None
    semester_end=None
    if start_date or end_date:
        if not start_date or not end_date:
            raise HTTPException(status_code=400,detail="Both start_date and end_date must be provided together")
        try:
            semester_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            semester_end =datetime.strptime(end_date,"%Y-%m-%d").date()
            if semester_start > semester_end:
                raise HTTPException(status_code=400, detail="Start Date must be samller than or equal to End Date")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {e}"
)
  
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    content = (await file.read()).decode("utf-8", errors="ignore")

    # Try DictReader (row-based format)
    reader = csv.DictReader(content.splitlines())
    required = {"title", "start", "end"}
    lowered = {fn.lower() for fn in (reader.fieldnames or [])}

    # Will build existing_ids after deletions (if mode=replace)
    existing_ids = set()
    new_events: List[CalendarEventDB] = []

    if required.issubset(lowered):
        # Row-based timetable
        for row in reader:
            row_l = { (k or "").lower(): (v or "").strip() for k, v in row.items() }
            try:
                start_dt = _parse_dt(row_l["start"])
                end_dt = _parse_dt(row_l["end"])
            except Exception as ex:
                raise HTTPException(status_code=400, detail=f"Bad date in row: {row} ({ex})")

            # Check if event already exists in database
            existing_event = db.query(CalendarEventDB).filter(
                and_(
                    CalendarEventDB.user_id == user_id,
                    CalendarEventDB.start == start_dt,
                    CalendarEventDB.title == (row_l.get("title") or "Untitled")
                )
            ).first()
            if existing_event:
                continue

            # Create new event in database
            event = CalendarEventDB(
                user_id=user_id,
                title=row_l.get("title") or "Untitled",
                start=start_dt,
                end=end_dt,
                location=row_l.get("location") or None,
                description=row_l.get("description") or None,
                all_day=(row_l.get("allday") or "").lower() in ("true", "1", "yes"),
            )
            db.add(event)
            new_events.append(event)
    else:
        # Grid-style timetable: first row = days, first column = time ranges
        rows = list(csv.reader(content.splitlines()))
        if not rows:
            raise HTTPException(status_code=400, detail="CSV is empty")
        header = [ (h or "").strip() for h in rows[0] ]
        # Normalize header days
        day_cols: List[tuple[int, int]] = []  # (col_index, weekday_index)
        for idx, h in enumerate(header):
            name = h.strip().lower()
            if name in DAY_IDX:
                day_cols.append((idx, DAY_IDX[name]))
        if not day_cols or len(rows) < 2:
            raise HTTPException(status_code=400, detail="CSV must have day columns (Monday..Sunday) and time ranges in first column")

        today = date.today()
        # Optional explicit day override (e.g., day=friday)
        if day:
            wd = DAY_IDX.get(day.strip().lower())
            if wd is None:
                raise HTTPException(status_code=400, detail="Invalid day. Use Monday..Sunday")
            day_cols = [(c, w) for (c, w) in day_cols if w == wd]
        # Or scope=today filters by current weekday
        elif (scope or "").lower() == "today":
            day_cols = [(c, w) for (c, w) in day_cols if w == today.weekday()]
        # Flag to use today's actual date instead of next weekday
        use_today_date = (scope or "").lower() == "today" and not day
        if not day_cols:
            total_count = db.query(CalendarEventDB).filter(CalendarEventDB.user_id == user_id).count()
            return {"success": True, "inserted": 0, "total_events": total_count}
        time_re = re.compile(r"\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*")
        # Accept only slots that intersect 08:30–15:30
        earliest_total = 8 * 60 + 30
        latest_total = 15 * 60 + 30

        # Build existing_ids if not in replace mode (to avoid duplicates)
        if (mode or "").lower() != "replace":
            existing_events = db.query(CalendarEventDB).filter(CalendarEventDB.user_id == user_id).all()
            for e in existing_events:
                event_id = f"grid_{e.start.date().isoformat()}_{e.start.strftime('%H%M')}_{e.title.replace(' ', '_')}"
                existing_ids.add(event_id)

        # If mode=replace, remove existing events for targeted day(s) before inserting
        if (mode or "").lower() == "replace":
            if semester_start and semester_end:
                # Delete ALL events that overlap with the semester date range
                # An event overlaps if: start <= semester_end AND end >= semester_start
                start_datetime = datetime.combine(semester_start, datetime.min.time())
                end_datetime = datetime.combine(semester_end, datetime.max.time())
                
                # First, delete events in the new date range
                deleted_count = db.query(CalendarEventDB).filter(
                    and_(
                        CalendarEventDB.user_id == user_id,
                        CalendarEventDB.start <= end_datetime,
                        CalendarEventDB.end >= start_datetime
                    )
                ).delete(synchronize_session=False)
                print(f"🗑️ Deleted {deleted_count} events in date range {semester_start} to {semester_end}")
                
                # Also delete events with matching weekday pattern from previous syncs
                # This ensures when you change the date range, old semester events are removed
                csv_weekdays = {w for (_c, w) in day_cols}
                remaining_events = db.query(CalendarEventDB).filter(CalendarEventDB.user_id == user_id).all()
                events_to_delete = []
                for evt in remaining_events:
                    evt_weekday = evt.start.weekday()
                    evt_date = evt.start.date()
                    # Delete if weekday matches CSV AND is outside new range (old semester event)
                    if evt_weekday in csv_weekdays:
                        if evt_date < semester_start or evt_date > semester_end:
                            # Only delete if it looks like a timetable event
                            if evt.location or (evt.start.hour >= 8 and evt.start.hour <= 15):
                                events_to_delete.append(evt.id)
                
                if events_to_delete:
                    additional_deleted = db.query(CalendarEventDB).filter(
                        CalendarEventDB.id.in_(events_to_delete)
                    ).delete(synchronize_session=False)
                    print(f"🗑️ Deleted {additional_deleted} additional old semester events with matching weekdays")
            elif use_today_date:
                # Delete today's events from database
                start_dt = datetime.combine(today, datetime.min.time())
                end_dt = datetime.combine(today, datetime.max.time())
                db.query(CalendarEventDB).filter(
                    and_(
                        CalendarEventDB.user_id == user_id,
                        CalendarEventDB.start >= start_dt,
                        CalendarEventDB.end <= end_dt
                    )
                ).delete(synchronize_session=False)
            else:
                # Delete events for next weekday occurrences
                target_dates = [_next_weekday(today, w) for (_c, w) in day_cols]
                for target_date in target_dates:
                    start_dt = datetime.combine(target_date, datetime.min.time())
                    end_dt = datetime.combine(target_date, datetime.max.time())
                    db.query(CalendarEventDB).filter(
                        and_(
                            CalendarEventDB.user_id == user_id,
                            CalendarEventDB.start >= start_dt,
                            CalendarEventDB.end <= end_dt
                        )
                    ).delete(synchronize_session=False)
            db.commit()  # Commit deletions before adding new events
            
            # Rebuild existing_ids AFTER deletion (only for events still in database)
            remaining_events = db.query(CalendarEventDB).filter(CalendarEventDB.user_id == user_id).all()
            for e in remaining_events:
                event_id = f"grid_{e.start.date().isoformat()}_{e.start.strftime('%H%M')}_{e.title.replace(' ', '_')}"
                existing_ids.add(event_id)

        for r in rows[1:]:
            if not r:
                continue
            time_cell = (r[0] if len(r) > 0 else "").strip()
            if not time_cell:
                continue
            m = time_re.match(time_cell.replace("—", "-").replace("–", "-"))
            if not m:
                # skip non time rows (e.g., header like D16ADB TT)
                continue
            start_t, end_t = m.group(1), m.group(2)
            try:
                st_h, st_m = map(int, start_t.split(":"))
                en_h, en_m = map(int, end_t.split(":"))
                # Heuristic: afternoon slots often written as 1:30, 2:30 -> convert to 13:30, 14:30
                if st_h <= 3:
                    st_h += 12
                if en_h <= 3:
                    en_h += 12
                start_t = f"{st_h:02d}:{st_m:02d}"
                end_t = f"{en_h:02d}:{en_m:02d}"
                st_total = st_h * 60 + st_m
                en_total = en_h * 60 + en_m
                if en_total <= earliest_total or st_total >= latest_total:
                    continue
            except Exception:
                pass

            for col_idx, weekday in day_cols:
                if col_idx >= len(r):
                    continue
                cell = (r[col_idx] or "").strip()
                if not cell:
                    continue
                if cell.lower() in ("break", "lunch"):
                    continue

                # Parse subject and optional location in parentheses e.g., "DL(D16ADB)"
                subj = cell
                location = None
                if "(" in cell and ")" in cell:
                    try:
                        subj_part, loc_part = cell.split("(", 1)
                        subj = subj_part.strip().strip("/")
                        location = loc_part.split(")", 1)[0].strip()
                    except Exception:
                        subj = cell.strip()

                if semester_start and semester_end:
                    target_dates = []
                    first_date = semester_start
                    current_weekday = first_date.weekday()
                    
                    # Calculate days until next occurrence of target weekday
                    days_until_weekday = (weekday - current_weekday + 7) % 7
                    
                    # Start from first occurrence of target weekday >= semester_start
                    current_date = first_date + timedelta(days=days_until_weekday)
                    
                    # Safety check
                    if current_date < first_date:
                        current_date += timedelta(days=7)
                    
                    # Generate ALL dates for this weekday in the entire range
                    while current_date <= semester_end:
                        target_dates.append(current_date)
                        current_date += timedelta(days=7)
                    
                elif use_today_date:
                    target_dates = [today]
                else:
                    target_dates = [_next_weekday(today, weekday)]
                
                # Create events for each target date
                for target_date in target_dates:
                    try:
                        start_dt = datetime.fromisoformat(f"{target_date.isoformat()} {start_t}:00")
                        end_dt = datetime.fromisoformat(f"{target_date.isoformat()} {end_t}:00")
                    except Exception:
                        continue
                    
                    # Check if event already exists in database (only check if not in replace mode or if existing_ids was populated)
                    if existing_ids:
                        event_id = f"grid_{target_date.isoformat()}_{start_t.replace(':','')}_{subj.replace(' ', '_')}"
                        if event_id in existing_ids:
                            continue
                    
                    # Always check by actual database query to avoid duplicates
                    existing_event = db.query(CalendarEventDB).filter(
                        and_(
                            CalendarEventDB.user_id == user_id,
                            CalendarEventDB.start == start_dt,
                            CalendarEventDB.title == (subj if not location else f"{subj} ({location})")
                        )
                    ).first()
                    if existing_event:
                        continue
                    
                    # Create new event in database
                    event = CalendarEventDB(
                        user_id=user_id,
                        title=subj if not location else f"{subj} ({location})",
                        start=start_dt,
                        end=end_dt,
                        location=location,
                        description=None,
                        all_day=False,
                    )
                    db.add(event)
                    new_events.append(event) 

    # Commit all new events to database
    db.commit()
    
    # Refresh events to get their database IDs
    for event in new_events:
        db.refresh(event)
    
    # Get total count from database
    total_count = db.query(CalendarEventDB).filter(CalendarEventDB.user_id == user_id).count()
    
    return {"success": True, "inserted": len(new_events), "total_events": total_count}

@app.get("/api/events")
def list_events(
    start: Optional[str] = None, 
    end: Optional[str] = None,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Get calendar events for a user, optionally filtered by date range"""
    query = db.query(CalendarEventDB).filter(CalendarEventDB.user_id == user_id)
    
    if start or end:
        if start:
            start_dt = datetime.fromisoformat(f"{start} 00:00:00")
            query = query.filter(CalendarEventDB.start >= start_dt)
        if end:
            end_dt = datetime.fromisoformat(f"{end} 23:59:59")
            query = query.filter(CalendarEventDB.end <= end_dt)
    
    events = query.order_by(CalendarEventDB.start).all()
    return {"events": [e.to_dict() for e in events]}

@app.post("/api/tasks")
def add_task(
    task: TaskItem,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Add a new task for a user"""
    # Check if task with same ID already exists
    existing = db.query(TaskDB).filter(
        and_(
            TaskDB.user_id == user_id,
            TaskDB.id == int(task.id) if task.id.isdigit() else None
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Task id already exists")
    
    due_date = datetime.fromisoformat(task.due_date).date()
    new_task = TaskDB(
        user_id=user_id,
        title=task.title,
        due_date=due_date,
        done=task.done
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"success": True, "task": new_task.to_dict()}

@app.get("/api/tasks")
def list_tasks(
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Get all tasks for a user"""
    tasks = db.query(TaskDB).filter(TaskDB.user_id == user_id).order_by(TaskDB.due_date).all()
    return {"tasks": [t.to_dict() for t in tasks]}

# ========= Simple Todos (Dashboard) endpoints =========
@app.get("/api/simple-todos")
def list_simple_todos(
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Get all simple todos for a user"""
    todos = db.query(SimpleTodoDB).filter(SimpleTodoDB.user_id == user_id).order_by(SimpleTodoDB.id).all()
    return {"todos": [t.to_dict() for t in todos]}

@app.post("/api/simple-todos")
def add_simple_todo(
    todo: SimpleTodoItem,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Add a new simple todo"""
    new_todo = SimpleTodoDB(
        user_id=user_id,
        text=todo.text,
        done=todo.done
    )
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    return {"success": True, "todo": new_todo.to_dict()}

@app.put("/api/simple-todos/{todo_id}")
def update_simple_todo(
    todo_id: int,
    todo: SimpleTodoItem,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Update a simple todo (toggle done or update text)"""
    existing = db.query(SimpleTodoDB).filter(
        and_(SimpleTodoDB.id == todo_id, SimpleTodoDB.user_id == user_id)
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    existing.text = todo.text
    existing.done = todo.done
    db.commit()
    db.refresh(existing)
    return {"success": True, "todo": existing.to_dict()}

@app.delete("/api/simple-todos/{todo_id}")
def delete_simple_todo(
    todo_id: int,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Delete a simple todo"""
    todo = db.query(SimpleTodoDB).filter(
        and_(SimpleTodoDB.id == todo_id, SimpleTodoDB.user_id == user_id)
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    db.delete(todo)
    db.commit()
    return {"success": True}

# ========= Subjects endpoints =========
@app.get("/api/subjects")
def list_subjects(
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Get all subjects for a user"""
    subjects = db.query(SubjectDB).filter(SubjectDB.user_id == user_id).order_by(SubjectDB.name).all()
    return {"subjects": [s.to_dict() for s in subjects]}

@app.post("/api/subjects")
def add_subject(
    subject: SubjectItem,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Add a new subject"""
    new_subject = SubjectDB(
        user_id=user_id,
        name=subject.name,
        code=subject.code
    )
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)
    return {"success": True, "subject": new_subject.to_dict()}

@app.delete("/api/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Delete a subject"""
    subject = db.query(SubjectDB).filter(
        and_(SubjectDB.id == subject_id, SubjectDB.user_id == user_id)
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    db.delete(subject)
    db.commit()
    return {"success": True}

@app.get("/api/today-overview", response_model=TodayOverview)
def today_overview(
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """Get today's events and tasks for a user"""
    today = date.today()
    
    # Get today's events from database
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    
    todays_events_db = db.query(CalendarEventDB).filter(
        and_(
            CalendarEventDB.user_id == user_id,
            CalendarEventDB.start >= start_dt,
            CalendarEventDB.end <= end_dt
        )
    ).order_by(CalendarEventDB.start).all()
    
    todays_events = [e.to_dict() for e in todays_events_db]
    
    # Get today's tasks from database
    todays_tasks_db = db.query(TaskDB).filter(
        and_(
            TaskDB.user_id == user_id,
            TaskDB.due_date == today,
            TaskDB.done == False
        )
    ).order_by(TaskDB.due_date).all()
    
    todays_tasks = [t.to_dict() for t in todays_tasks_db]

    return TodayOverview(
        date=today.isoformat(),
        events=todays_events, 
        tasks=todays_tasks,
    )

@app.post("/api/generate-questions")
async def generate_questions(request: QuestionGenerationRequest):
    """Generate questions based on content analysis"""
    try:
        # Analyze content first
        content_analysis = content_analyzer.analyze_content(
            request.content,
            request.document_type
        )
        
        # Generate questions
        questions = question_generator.generate_questions(
            content_analysis,
            request.requirements
        )
        
        return {
            "success": True,
            "analysis": content_analysis,
            "questions": questions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-question-paper")
async def generate_question_paper(request: QuestionPaperRequest):
    """Complete workflow: Analyze content + Generate questions"""
    try:
        # Analyze content
        content_analysis = content_analyzer.analyze_content(
            request.content,
            request.document_type
        )
        
        # Prepare requirements
        requirements = {
            "num_mcq": request.num_mcq,
            "num_short": request.num_short,
            "num_long": request.num_long,
            "marks_mcq": request.marks_mcq,
            "marks_short": request.marks_short,
            "marks_long": request.marks_long,
            "difficulty": request.difficulty
        }
        
        # Generate questions
        questions = question_generator.generate_questions(
            content_analysis,
            requirements
        )
        
        # Calculate total marks
        total_marks = (
            len(questions.get("mcq_questions", [])) * request.marks_mcq +
            len(questions.get("short_answer_questions", [])) * request.marks_short +
            len(questions.get("long_answer_questions", [])) * request.marks_long
        )
        
        return {
            "success": True,
            "content_analysis": content_analysis,
            "questions": questions,
            "total_marks": total_marks,
            "summary": {
                "total_mcqs": len(questions.get("mcq_questions", [])),
                "total_short": len(questions.get("short_answer_questions", [])),
                "total_long": len(questions.get("long_answer_questions", []))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)