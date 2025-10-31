from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
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
class CalendarEvent(BaseModel):
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
    events: List[CalendarEvent]
    tasks: List[TaskItem]

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
async def upload_timetable(file: UploadFile = File(...), scope: Optional[str] = None, day: Optional[str] = None, mode: Optional[str] = None):
    """
    Upload a CSV timetable and sync to calendar events.
    Required headers (case-insensitive): title,start,end
    Optional: location,description,allDay,id
    start/end can be "YYYY-MM-DD HH:MM" or ISO "YYYY-MM-DDTHH:MM".
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    content = (await file.read()).decode("utf-8", errors="ignore")

    # Try DictReader (row-based format)
    reader = csv.DictReader(content.splitlines())
    required = {"title", "start", "end"}
    lowered = {fn.lower() for fn in (reader.fieldnames or [])}

    existing = _load_json(EVENTS_PATH, [])
    existing_ids = {e.get("id") for e in existing if "id" in e}
    new_events: List[dict] = []

    if required.issubset(lowered):
        # Row-based timetable
        for row in reader:
            row_l = { (k or "").lower(): (v or "").strip() for k, v in row.items() }
            try:
                start_dt = _parse_dt(row_l["start"])
                end_dt = _parse_dt(row_l["end"])
            except Exception as ex:
                raise HTTPException(status_code=400, detail=f"Bad date in row: {row} ({ex})")

            eid = row_l.get("id") or f"evt_{len(existing)+len(new_events)+1}"
            if eid in existing_ids:
                continue

            ev = {
                "id": eid,
                "title": row_l.get("title") or "Untitled",
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "location": row_l.get("location") or None,
                "description": row_l.get("description") or None,
                "allDay": (row_l.get("allday") or "").lower() in ("true", "1", "yes"),
            }
            new_events.append(ev)
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
            return {"success": True, "inserted": 0, "total_events": len(existing)}
        time_re = re.compile(r"\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*")
        # Accept only slots that intersect 08:30–15:30
        earliest_total = 8 * 60 + 30
        latest_total = 15 * 60 + 30

        # If mode=replace, remove existing events for targeted day(s) before inserting
        if (mode or "").lower() == "replace":
            if use_today_date:
                target_dates = { today.isoformat() }
            else:
                target_dates = set((_next_weekday(today, w)).isoformat() for (_c, w) in day_cols)
            existing = [ev for ev in existing if (ev.get("start", "")[:10] not in target_dates)]
            existing_ids = {e.get("id") for e in existing if "id" in e}

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

                target_date = today if use_today_date else _next_weekday(today, weekday)
                try:
                    start_dt = datetime.fromisoformat(f"{target_date.isoformat()} {start_t}:00")
                    end_dt = datetime.fromisoformat(f"{target_date.isoformat()} {end_t}:00")
                except Exception:
                    continue

                eid = f"grid_{target_date.isoformat()}_{start_t.replace(':','')}_{subj.replace(' ', '_')}"
                if eid in existing_ids:
                    continue
                ev = {
                    "id": eid,
                    "title": subj if not location else f"{subj} ({location})",
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "location": location,
                    "description": None,
                    "allDay": False,
                }
                new_events.append(ev)

    merged = existing + new_events
    _save_json(EVENTS_PATH, merged)
    return {"success": True, "inserted": len(new_events), "total_events": len(merged)}

@app.get("/api/events")
def list_events(start: Optional[str] = None, end: Optional[str] = None):
    events = _load_json(EVENTS_PATH, [])
    if not start and not end:
        return {"events": events}

    def in_range(ev: dict) -> bool:
        s = datetime.fromisoformat(ev["start"].replace("Z", ""))
        e = datetime.fromisoformat(ev["end"].replace("Z", ""))
        start_dt = datetime.fromisoformat(f"{start} 00:00:00") if start else None
        end_dt = datetime.fromisoformat(f"{end} 23:59:59") if end else None
        if start_dt and e < start_dt:
            return False
        if end_dt and s > end_dt:
            return False
        return True

    return {"events": [ev for ev in events if in_range(ev)]}

@app.post("/api/tasks")
def add_task(task: TaskItem):
    tasks = _load_json(TASKS_PATH, [])
    if any(t.get("id") == task.id for t in tasks):
        raise HTTPException(status_code=400, detail="Task id already exists")
    tasks.append(task.model_dump())
    _save_json(TASKS_PATH, tasks)
    return {"success": True}

@app.get("/api/tasks")
def list_tasks():
    return {"tasks": _load_json(TASKS_PATH, [])}

@app.get("/api/today-overview", response_model=TodayOverview)
def today_overview():
    today = date.today()
    events = _load_json(EVENTS_PATH, [])
    tasks = _load_json(TASKS_PATH, [])

    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    def is_today(ev: dict) -> bool:
        try:
            s = datetime.fromisoformat(ev["start"].replace("Z", ""))
            e = datetime.fromisoformat(ev["end"].replace("Z", ""))
            return not (e < start_dt or s > end_dt)
        except Exception:
            return False

    todays_events = [e for e in events if is_today(e)]
    todays_tasks = [t for t in tasks if t.get("due_date") == today.isoformat() and not t.get("done", False)]

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