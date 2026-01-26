from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
load_dotenv()  # reads backend/.env or project .env if present

# Gemini SDK (google-genai)
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

genai_client = genai.Client(api_key=API_KEY)

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
from agents.lab_manual_generator_agent import LabManualGenerator
from utils.ppt_creator import PPTCreator
from utils.syllabus_store import save_syllabus_pdf, retrieve_topic_context
from utils.lab_manual_creator import LabManualCreator
from utils.image_fetcher import ImageFetcher
# PDF and Document processing utilities
try:
    from utils.pdf_creator import PDFCreator
    from utils.document_processor import DocumentProcessor
    from utils.lab_manual_pdf_creator import LabManualPDFCreator
    PDF_UTILS_AVAILABLE = True
except ImportError:
    PDF_UTILS_AVAILABLE = False
    PDFCreator = None
    DocumentProcessor = None
    LabManualPDFCreator = None
from database.connection import get_db
from database.models.calendar_event import CalendarEvent as CalendarEventDB
from database.models.task import Task as TaskDB
from database.models.simple_todo import SimpleTodo as SimpleTodoDB
from database.models.subject import Subject as SubjectDB
from database.models.academics import LabManual as LabManualDB, ContinuousAssessment as ContinuousAssessmentDB
from database.models.research import FDP as FDPDB, Lecture as LectureDB, Certification as CertificationDB, CurrentProject as CurrentProjectDB, ResearchProposal as ResearchProposalDB
from database.models.attendance import (
    Teacher, DepartmentSemester, AttendanceClass, AttendanceSubject,
    AttendanceStudent, AttendanceSession, AttendanceRecord
)
from database.models.user import User
from sqlalchemy.orm import Session
from fastapi import Depends
from sqlalchemy import and_, or_
import traceback

# Attendance operations (no langchain/crewai dependency)
from agents.attendance_tools import (
    create_session as attendance_create_session,
    mark_attendance as attendance_mark_attendance,
    summary as attendance_summary,
    export_csv as attendance_export_csv,
    ensure_attendance_base,
)

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
lab_manual_generator = LabManualGenerator()
lab_manual_creator = LabManualCreator()
image_fetcher = ImageFetcher()
# Initialize PDF and document processing if available
if PDF_UTILS_AVAILABLE:
    try:
        pdf_creator = PDFCreator()
        document_processor = DocumentProcessor()
        lab_manual_pdf_creator = LabManualPDFCreator()
        print("✅ PDF utilities initialized successfully")
    except Exception as e:
        print(f"⚠️ Warning: Failed to initialize PDF utilities: {e}")
        PDF_UTILS_AVAILABLE = False
        pdf_creator = None
        document_processor = None
        lab_manual_pdf_creator = None
else:
    pdf_creator = None
    document_processor = None
    lab_manual_pdf_creator = None
    print("⚠️ Warning: PDF utilities not available - reportlab may not be installed")

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
    difficulty: str = "medium"  # Overall difficulty, can be "easy", "medium", "hard", or "mixed"
    difficulty_distribution: Optional[Dict[str, int]] = None  # e.g., {"easy": 2, "medium": 5, "hard": 3}
    num_sets: int = 1  # Number of question paper sets to generate

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

# ========= Helper functions for image handling =========

def _attach_images(slide_data: dict, max_images: int = 4, skip_modes: list = None) -> dict:
    """Attach images to slides. Checks for existing image_path first, then preferred_image_url, then image_query.
    
    Args:
        skip_modes: List of mode names to skip (e.g., ['mode_2', 'mode_4'])
    """
    if not isinstance(slide_data, dict):
        return slide_data
    slides = slide_data.get("slides", [])
    if not isinstance(slides, list):
        return slide_data
    
    # CRITICAL: Check if any slide has title_locked (Mode 2/4) - if so, skip auto-image fetching
    has_locked_titles = any(s.get("title_locked") for s in slides if isinstance(s, dict))
    if has_locked_titles:
        print(f"🔍 DEBUG: Detected locked titles (Mode 2/4) - skipping auto image attachment")
        return slide_data
    
    fetched = 0
    for s in slides:
        if fetched >= max_images:
            break
        
        # Skip base/title slide (slide 1) - it shouldn't have images
        if s.get("slide_number", 0) == 1:
            continue
        
        # Priority 0: Skip if image_path already exists (from uploaded images or user-specified)
        # CRITICAL: Never overwrite user-specified images
        if s.get("image_path"):
            if os.path.exists(s.get("image_path")):
                print(f"✓ Slide {s.get('slide_number')} already has user-specified image: {s.get('image_path')}")
                continue  # Don't increment fetched - this image was already provided
            else:
                print(f"⚠ Slide {s.get('slide_number')} has image_path but file doesn't exist: {s.get('image_path')}")
                # Remove invalid path but continue to try other sources
                del s["image_path"]
        
        # Skip if image_number is set (Mode 4 - user-specified image mapping)
        if s.get("image_number"):
            print(f"✓ Slide {s.get('slide_number')} has user-specified image_number ({s.get('image_number')}) - skipping auto image")
            continue
        
        # Priority 1: Check for preferred_image_url (user-provided URL)
        preferred_url = s.get("preferred_image_url")
        if preferred_url:
            path = image_fetcher.download_from_url(preferred_url, f"slide_{s.get('slide_number', 'unknown')}")
            if path:
                s["image_path"] = path
                fetched += 1
                print(f"✓ Downloaded preferred image for slide {s.get('slide_number')} from URL")
                continue
            else:
                print(f"⚠ Failed to download preferred image URL for slide {s.get('slide_number')}")
        
        # MODE 5 IMAGE LOCK: Skip slides that explicitly forbid images
        if s.get("_mode_5_image_mode") == "NONE" or s.get("_no_image"):
            print(f"🚫 MODE 5 IMAGE LOCK: Skipped auto image fetch for slide {s.get('slide_number')} (No image declared)")
            continue
        
        # Priority 2: Fetch from Unsplash using image_query
        # CRITICAL: Only fetch if slide doesn't already have a user-specified image
        query = s.get("image_query")
        if not query:
            continue
        
        # Double-check: Don't overwrite user-specified images
        if s.get("image_path"):
            print(f"⚠ Slide {s.get('slide_number')}: Skipping image_query '{query}' - user-specified image already exists")
            continue
        
        path = image_fetcher.fetch_image(query)
        if path:
            s["image_path"] = path
            fetched += 1
            print(f"✓ Fetched image from query for slide {s.get('slide_number')}: {query}")
        else:
            print(f"⚠ Image fetch failed for query: {query}")
    return slide_data

def _apply_image_requests(slide_data: dict, image_requests: list[dict]) -> dict:
    """Apply user-specified image requests to specific slides."""
    if not image_requests or not isinstance(slide_data, dict):
        print(f"🔍 DEBUG: No image requests or invalid slide_data")
        return slide_data
    slides = slide_data.get("slides", [])
    if not isinstance(slides, list):
        print(f"🔍 DEBUG: slides is not a list")
        return slide_data
    
    print(f"🔍 DEBUG: Processing {len(image_requests)} image requests")
    print(f"🔍 DEBUG: Available slides: {[s.get('slide_number') for s in slides]}")
    
    for req in image_requests:
        if not isinstance(req, dict):
            continue
        sn = req.get("slide_number")
        q = (req.get("query") or "").strip()
        url = (req.get("url") or "").strip()
        local_path = (req.get("local_path") or "").strip()
        
        print(f"🔍 DEBUG: Processing request for slide {sn}, local_path={local_path}, url={url}, query={q}")
        
        if not sn:
            print(f"⚠ DEBUG: No slide_number in request: {req}")
            continue
        
        # slide_number is 1-based
        found_slide = False
        for s in slides:
            slide_num = s.get("slide_number")
            if slide_num == sn:
                found_slide = True
                print(f"🔍 DEBUG: Found slide {sn}, checking image options...")
                # Priority: local_path > url > query
                if local_path:
                    # Convert to absolute path
                    abs_path = os.path.abspath(local_path) if not os.path.isabs(local_path) else local_path
                    if os.path.exists(abs_path):
                        s["image_path"] = abs_path  # Direct local path for uploaded images
                        print(f"✓ Using uploaded image for slide {sn}: {abs_path}")
                        print(f"  File exists: {os.path.exists(abs_path)}, Size: {os.path.getsize(abs_path) if os.path.exists(abs_path) else 0} bytes")
                    else:
                        print(f"⚠ DEBUG: local_path does not exist: {abs_path}")
                        print(f"  Current working directory: {os.getcwd()}")
                        print(f"  Trying relative path check...")
                        # Try relative to current directory
                        rel_path = local_path if os.path.isabs(local_path) else os.path.join(os.getcwd(), local_path)
                        if os.path.exists(rel_path):
                            s["image_path"] = rel_path
                            print(f"✓ Found image using relative path: {rel_path}")
                        else:
                            print(f"❌ Image not found at any path: {local_path}")
                elif url:
                    s["preferred_image_url"] = url
                    print(f"✓ Set preferred_image_url for slide {sn}: {url}")
                elif q:
                    s["image_query"] = q
                    print(f"✓ Set image_query for slide {sn}: {q}")
                break
        
        if not found_slide:
            print(f"⚠ DEBUG: Slide {sn} not found in slides! Available: {[s.get('slide_number') for s in slides]}")
    
    return slide_data

# ========= Assist endpoint (unified PPT/Question Paper generation) =========

@app.post("/api/assist")
async def assist_endpoint(
    request: Request,
    prompt: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None)
):
    """
    Unified endpoint for PPT generation with prompt and optional images.
    Supports all 5 PPT modes via prompt parsing.
    Handles both JSON and FormData requests.
    """
    try:
        saved_image_paths = []
        user_prompt = ""
        
        # Check if it's FormData (has prompt as Form) or JSON
        if prompt is not None:
            # FormData request
            user_prompt = prompt
            if not user_prompt:
                raise HTTPException(status_code=400, detail="Prompt is required")
            
            # Handle uploaded images
            if images:
                temp_dir = Path("storage/temp/images")
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                for idx, img_file in enumerate(images, 1):
                    image_data = await img_file.read()
                    # Get file extension from filename or default to jpg
                    filename = img_file.filename or f"image_{idx}.jpg"
                    image_ext = Path(filename).suffix
                    if not image_ext:
                        image_ext = ".jpg"
                    image_path = temp_dir / f"image_{idx}{image_ext}"
                    with open(image_path, "wb") as f:
                        f.write(image_data)
                    saved_image_paths.append(str(image_path))
                    print(f"📷 Saved image {idx}: {image_path}")
        else:
            # JSON request
            body = await request.json()
            user_prompt = body.get("prompt", "")
            if not user_prompt:
                raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Generate PPT using the agent with user_input
        print(f"🔍 ASSIST: Processing prompt (length: {len(user_prompt)})")
        
        slide_data = content_generator.generate_slide_content(
            topic="",  # Will be extracted from prompt
            content="",  # Will be extracted from prompt
            num_slides=8,  # Default, will be overridden by prompt
            subject=None,
            module=None,
            user_input=user_prompt  # CRITICAL: Pass prompt as user_input for mode detection
        )
        
        # Map uploaded images to slides based on image_number in slide_data
        if saved_image_paths:
            print(f"📷 Mapping {len(saved_image_paths)} images to slides...")
            for slide in slide_data.get("slides", []):
                image_num = slide.get("image_number")
                if image_num and 1 <= image_num <= len(saved_image_paths):
                    image_path = saved_image_paths[image_num - 1]  # image_number is 1-indexed
                    slide["image_path"] = image_path
                    print(f"  ✓ Mapped Image {image_num} to slide {slide.get('slide_number')}: {image_path}")
        
        # Attach additional images if needed (only if not Mode 2/4)
        prompt_lower = str(user_prompt).lower()
        is_mode_2 = "slide titles:" in prompt_lower
        is_mode_4 = "image placement:" in prompt_lower
        
        if not is_mode_2 and not is_mode_4:
            slide_data = _attach_images(slide_data, max_images=4)
        
        # Create PowerPoint file
        storage_dir = Path("storage/presentations")
        creator = PPTCreator(str(storage_dir))
        file_path = creator.create_presentation(slide_data)
        
        filename = os.path.basename(file_path)
        
        # Clean up temporary images
        for img_path in saved_image_paths:
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception as e:
                print(f"⚠ Could not delete temp image {img_path}: {e}")
        
        # Return response in format expected by UI
        download_link = f"/api/download-ppt/{filename}"
        
        return {
            "message": f"PPT generated successfully!",
            "link": download_link,
            "filename": filename,
            "type": "ppt"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        print(f"❌ ASSIST ERROR: {error_detail}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

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

@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """Upload PDF or PPT file and extract text content"""
    if not PDF_UTILS_AVAILABLE or not document_processor:
        raise HTTPException(
            status_code=503,
            detail="Document processing utilities are not available. Please ensure utils/document_processor.py exists."
        )
    
    try:
        # Determine file type from extension
        filename = file.filename.lower()
        if filename.endswith('.pdf'):
            file_type = 'pdf'
        elif filename.endswith(('.ppt', '.pptx')):
            file_type = 'pptx'
        elif filename.endswith(('.doc', '.docx')):
            file_type = 'docx'
        else:
            raise HTTPException(
                status_code=400, 
                detail="Unsupported file type. Please upload PDF, PPT, PPTX, DOC, or DOCX files."
            )
        
        # Read file content
        file_bytes = await file.read()
        
        # Extract text
        extracted_text = document_processor.extract_text(file_bytes, file_type)
        
        if not extracted_text or not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the document. The file might be empty or corrupted."
            )
        
        return {
            "success": True,
            "extracted_text": extracted_text,
            "file_type": file_type,
            "filename": file.filename
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/api/generate-question-paper-pdf")
async def generate_question_paper_pdf(request: QuestionPaperRequest):
    """Complete workflow: Analyze content + Generate questions + Create PDF (supports multiple sets)"""
    if not PDF_UTILS_AVAILABLE or not pdf_creator:
        raise HTTPException(
            status_code=503,
            detail="PDF creation utilities are not available. Please ensure utils/pdf_creator.py exists."
        )
    
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
        
        # Generate multiple sets if requested
        num_sets = request.num_sets if request.num_sets > 0 else 1
        
        if num_sets > 1:
            # Generate multiple sets
            question_sets = question_generator.generate_multiple_sets(
                content_analysis,
                requirements,
                num_sets=num_sets,
                difficulty_distribution=request.difficulty_distribution
            )
            
            # Create PDFs for each set
            pdf_paths = []
            sets_with_marks = []
            
            for q_set in question_sets:
                total_marks = (
                    len(q_set.get("mcq_questions", [])) * request.marks_mcq +
                    len(q_set.get("short_answer_questions", [])) * request.marks_short +
                    len(q_set.get("long_answer_questions", [])) * request.marks_long
                )
                
                # Create PDF for this set
                pdf_path = pdf_creator.create_question_paper(
                    questions_data=q_set,
                    total_marks=total_marks,
                    difficulty=request.difficulty,
                    filename=f"Question_Paper_Set_{q_set.get('set_number', 0)}.pdf"
                )
                
                pdf_paths.append(pdf_path)
                sets_with_marks.append({
                    "set_number": q_set.get("set_number", 0),
                    "set_name": q_set.get("set_name", ""),
                    "questions": q_set,
                    "total_marks": total_marks,
                    "pdf_path": pdf_path,
                    "summary": {
                        "total_mcqs": len(q_set.get("mcq_questions", [])),
                        "total_short": len(q_set.get("short_answer_questions", [])),
                        "total_long": len(q_set.get("long_answer_questions", []))
                    }
                })
            
            return {
                "success": True,
                "content_analysis": content_analysis,
                "num_sets": num_sets,
                "sets": sets_with_marks,
                "pdf_paths": pdf_paths,
                "questions": question_sets[0] if question_sets else {},  # Keep backward compatibility
                "pdf_path": pdf_paths[0] if pdf_paths else None,  # Keep backward compatibility
                "total_marks": sets_with_marks[0]["total_marks"] if sets_with_marks else 0,
                "summary": sets_with_marks[0]["summary"] if sets_with_marks else {}
            }
        else:
            # Generate single set (backward compatible)
            questions = question_generator.generate_questions(
                content_analysis,
                requirements,
                difficulty_distribution=request.difficulty_distribution
            )
            
            # Calculate total marks
            total_marks = (
                len(questions.get("mcq_questions", [])) * request.marks_mcq +
                len(questions.get("short_answer_questions", [])) * request.marks_short +
                len(questions.get("long_answer_questions", [])) * request.marks_long
            )
            
            # Create PDF
            pdf_path = pdf_creator.create_question_paper(
                questions_data=questions,
                total_marks=total_marks,
                difficulty=request.difficulty
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
                },
                "pdf_path": pdf_path,
                "pdf_filename": os.path.basename(pdf_path)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download-question-paper/{filename}")
async def download_question_paper(filename: str):
    """Download a generated question paper PDF"""
    file_path = backend_dir / "storage" / "question_papers" / filename
    # Also try relative path for backward compatibility
    if not file_path.exists():
        alt_path = Path("storage/question_papers") / filename
        if alt_path.exists():
            file_path = alt_path
        else:
            raise HTTPException(status_code=404, detail="File not found")
    
    # Ensure filename has .pdf extension
    download_filename = filename
    if not download_filename.endswith('.pdf'):
        download_filename = f"{filename}.pdf"
    
    return FileResponse(
        path=str(file_path),
        filename=download_filename,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"'
        }
    )

# ========= Lab Manual endpoints =========
@app.post("/api/generate-lab-manual-from-pdf")
async def generate_lab_manual_from_pdf(
    file: UploadFile = File(...),
    num_modules: int = 5,
    user_id: str = "default",  # TODO: Get from Firebase token
    db: Session = Depends(get_db)
):
    """
    Generate a lab manual from a PDF or DOCX file containing prerequisites, objectives, and outcomes.
    Accepts both PDF and DOCX input files.
    Always returns a downloadable PDF file with professional formatting.
    """
    try:
        # Validate file type (accept both PDF and DOCX)
        filename_lower = (file.filename or "").lower()
        if not (filename_lower.endswith(".pdf") or filename_lower.endswith(".docx") or filename_lower.endswith(".doc")):
            raise HTTPException(
                status_code=400, 
                detail="Only PDF or DOCX files are allowed"
            )
        
        # Determine file type
        if filename_lower.endswith(".pdf"):
            file_type = "pdf"
        else:
            file_type = "docx"
        
        # Read file content
        file_data = await file.read()
        
        # Extract text using DocumentProcessor
        if not PDF_UTILS_AVAILABLE or not document_processor:
            raise HTTPException(
                status_code=503,
                detail="Document processing utilities are not available. Please ensure utils/document_processor.py exists."
            )
        
        # Extract text from file
        full_text = document_processor.extract_text(file_data, file_type)
        
        if not full_text or not full_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the document. The file might be empty, corrupted, or image-based (scanned)."
            )
        
        # Parse extracted text to get prerequisites, objectives, outcomes
        parsed_info = lab_manual_generator._parse_pdf_text(full_text)
        
        subject = parsed_info.get("subject", "Unknown Subject")
        course_code = parsed_info.get("course_code")
        prerequisites = parsed_info.get("prerequisites", "")
        lab_objectives = parsed_info.get("lab_objectives", [])
        lab_outcomes = parsed_info.get("lab_outcomes", [])
        
        # Validate extracted data
        if not lab_objectives:
            raise HTTPException(
                status_code=400,
                detail="Could not extract lab objectives from document. Please ensure the document contains lab objectives."
            )
        if not lab_outcomes:
            raise HTTPException(
                status_code=400,
                detail="Could not extract lab outcomes from document. Please ensure the document contains lab outcomes."
            )
        
        # Generate lab manual structure
        manual_content = lab_manual_generator._generate_lab_manual_structure(
            prerequisites=prerequisites,
            lab_objectives=lab_objectives,
            lab_outcomes=lab_outcomes,
            subject=subject,
            course_code=course_code,
            num_modules=num_modules
        )
        
        # Use data from manual_content (may have been refined by AI)
        subject = manual_content.get("subject", subject)
        course_code = manual_content.get("course_code", course_code)
        prerequisites = manual_content.get("prerequisites", prerequisites)
        lab_objectives = manual_content.get("lab_objectives", lab_objectives)
        lab_outcomes = manual_content.get("lab_outcomes", lab_outcomes)
        
        # Always create PDF document (required)
        if not PDF_UTILS_AVAILABLE or not lab_manual_pdf_creator:
            raise HTTPException(
                status_code=503,
                detail="PDF creation utilities are not available. Please ensure utils/lab_manual_pdf_creator.py exists and reportlab is installed."
            )
        
        try:
            pdf_path = lab_manual_pdf_creator.create_lab_manual_pdf(manual_content)
        except Exception as e:
            print(f"Error creating PDF: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create PDF: {str(e)}. Please ensure reportlab is installed and the PDF creator is working correctly."
            )
        
        file_path = pdf_path
        media_type = "application/pdf"
        filename = os.path.basename(pdf_path)
        
        # Ensure filename has .pdf extension
        if not filename.endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        # Save to database
        new_manual = LabManualDB(
            user_id=user_id,
            subject=subject,
            course_code=course_code,
            prerequisites=prerequisites,
            lab_objectives=json.dumps(lab_objectives),
            lab_outcomes=json.dumps(lab_outcomes),
            manual_content=json.dumps(manual_content)
        )
        db.add(new_manual)
        db.commit()
        db.refresh(new_manual)
        
        # Return downloadable file
        def generate():
            with open(file_path, "rb") as f:
                yield from f
        
        return StreamingResponse(
            generate(),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate lab manual: {str(e)}")

@app.get("/api/download-lab-manual/{manual_id}")
async def download_lab_manual(
    manual_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Download a lab manual as PDF file"""
    try:
        manual = db.query(LabManualDB).filter(
            and_(LabManualDB.id == manual_id, LabManualDB.user_id == user_id)
        ).first()
        if not manual:
            raise HTTPException(status_code=404, detail="Lab manual not found")
        
        # Get manual content from database
        manual_content = json.loads(manual.manual_content) if manual.manual_content else {}
        
        # Always create PDF document (required)
        if not PDF_UTILS_AVAILABLE or not lab_manual_pdf_creator:
            raise HTTPException(
                status_code=503,
                detail="PDF creation utilities are not available. Please ensure utils/lab_manual_pdf_creator.py exists and reportlab is installed."
            )
        
        try:
            pdf_path = lab_manual_pdf_creator.create_lab_manual_pdf(manual_content)
        except Exception as e:
            print(f"Error creating PDF for download: {e}")
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create PDF: {str(e)}. Please ensure reportlab is installed and the PDF creator is working correctly."
            )
        
        filename = os.path.basename(pdf_path)
        
        # Ensure filename has .pdf extension
        if not filename.endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        # Return file
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lab-manuals")
def list_lab_manuals(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get all lab manuals for a user"""
    manuals = db.query(LabManualDB).filter(LabManualDB.user_id == user_id).order_by(LabManualDB.created_at.desc()).all()
    return {"manuals": [m.to_dict() for m in manuals]}

@app.get("/api/lab-manuals/{manual_id}")
def get_lab_manual(
    manual_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get a specific lab manual"""
    manual = db.query(LabManualDB).filter(
        and_(LabManualDB.id == manual_id, LabManualDB.user_id == user_id)
    ).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Lab manual not found")
    return {"manual": manual.to_dict()}

# ========= Academics endpoints (excluding Lab Manuals) =========

# Continuous Assessments
class ContinuousAssessmentItem(BaseModel):
    id: Optional[str] = None
    subject_name: str
    assessment_type: str
    marks: int
    total_marks: int
    assessment_date: Optional[str] = None

@app.get("/api/continuous-assessments")
def list_continuous_assessments(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get all continuous assessments for a user"""
    assessments = db.query(ContinuousAssessmentDB).filter(
        ContinuousAssessmentDB.user_id == user_id
    ).order_by(ContinuousAssessmentDB.assessment_date.desc()).all()
    return {"assessments": [a.to_dict() for a in assessments]}

@app.post("/api/continuous-assessments")
def add_continuous_assessment(
    assessment: ContinuousAssessmentItem,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Add a new continuous assessment"""
    assessment_date = None
    if assessment.assessment_date:
        assessment_date = datetime.fromisoformat(assessment.assessment_date).date()
    
    new_assessment = ContinuousAssessmentDB(
        user_id=user_id,
        subject_name=assessment.subject_name,
        assessment_type=assessment.assessment_type,
        marks=assessment.marks,
        total_marks=assessment.total_marks,
        assessment_date=assessment_date
    )
    db.add(new_assessment)
    db.commit()
    db.refresh(new_assessment)
    return {"success": True, "assessment": new_assessment.to_dict()}

@app.delete("/api/continuous-assessments/{assessment_id}")
def delete_continuous_assessment(
    assessment_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Delete a continuous assessment"""
    assessment = db.query(ContinuousAssessmentDB).filter(
        and_(ContinuousAssessmentDB.id == assessment_id, ContinuousAssessmentDB.user_id == user_id)
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    db.delete(assessment)
    db.commit()
    return {"success": True}

# FDPs
class FDPItem(BaseModel):
    id: Optional[str] = None
    title: str
    organization: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    certificate_path: Optional[str] = None

@app.get("/api/fdps")
def list_fdps(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get all FDPs for a user"""
    fdps = db.query(FDPDB).filter(FDPDB.user_id == user_id).order_by(FDPDB.start_date.desc()).all()
    return {"fdps": [f.to_dict() for f in fdps]}

@app.post("/api/fdps")
def add_fdp(
    fdp: FDPItem,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Add a new FDP"""
    start_date = None
    end_date = None
    if fdp.start_date:
        start_date = datetime.fromisoformat(fdp.start_date).date()
    if fdp.end_date:
        end_date = datetime.fromisoformat(fdp.end_date).date()
    
    new_fdp = FDPDB(
        user_id=user_id,
        title=fdp.title,
        organization=fdp.organization,
        start_date=start_date,
        end_date=end_date,
        certificate_path=fdp.certificate_path
    )
    db.add(new_fdp)
    db.commit()
    db.refresh(new_fdp)
    return {"success": True, "fdp": new_fdp.to_dict()}

@app.delete("/api/fdps/{fdp_id}")
def delete_fdp(
    fdp_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Delete an FDP"""
    fdp = db.query(FDPDB).filter(
        and_(FDPDB.id == fdp_id, FDPDB.user_id == user_id)
    ).first()
    if not fdp:
        raise HTTPException(status_code=404, detail="FDP not found")
    db.delete(fdp)
    db.commit()
    return {"success": True}

# Lectures
class LectureItem(BaseModel):
    id: Optional[str] = None
    title: str
    venue: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None

@app.get("/api/lectures")
def list_lectures(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get all lectures for a user"""
    lectures = db.query(LectureDB).filter(LectureDB.user_id == user_id).order_by(LectureDB.date.desc()).all()
    return {"lectures": [l.to_dict() for l in lectures]}

@app.post("/api/lectures")
def add_lecture(
    lecture: LectureItem,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Add a new lecture"""
    lecture_date = None
    if lecture.date:
        lecture_date = datetime.fromisoformat(lecture.date).date()
    
    new_lecture = LectureDB(
        user_id=user_id,
        title=lecture.title,
        venue=lecture.venue,
        date=lecture_date,
        description=lecture.description
    )
    db.add(new_lecture)
    db.commit()
    db.refresh(new_lecture)
    return {"success": True, "lecture": new_lecture.to_dict()}

@app.delete("/api/lectures/{lecture_id}")
def delete_lecture(
    lecture_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Delete a lecture"""
    lecture = db.query(LectureDB).filter(
        and_(LectureDB.id == lecture_id, LectureDB.user_id == user_id)
    ).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    db.delete(lecture)
    db.commit()
    return {"success": True}

# Certifications
class CertificationItem(BaseModel):
    id: Optional[str] = None
    name: str
    issuing_organization: str
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    certificate_path: Optional[str] = None

@app.get("/api/certifications")
def list_certifications(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get all certifications for a user"""
    certifications = db.query(CertificationDB).filter(
        CertificationDB.user_id == user_id
    ).order_by(CertificationDB.issue_date.desc()).all()
    return {"certifications": [c.to_dict() for c in certifications]}

@app.post("/api/upload-certificate")
async def upload_certificate(
    file: UploadFile = File(...),
    user_id: str = "default"
):
    """Upload a certificate file (PDF, JPG, JPEG, PNG)"""
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png"}
    file_ext = Path(file.filename or "").suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF, JPG, JPEG, and PNG files are allowed. Got: {file_ext}"
        )
    
    # Save file - use absolute path relative to backend directory
    file_data = await file.read()
    storage_dir = backend_dir / "storage" / "certificates"
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{user_id}_{timestamp}_{file.filename}"
    file_path = storage_dir / safe_filename
    
    with open(file_path, "wb") as f:
        f.write(file_data)
    
    # Return relative path that can be used in API
    relative_path = f"/api/certificates/{safe_filename}"
    return {"success": True, "path": relative_path, "filename": safe_filename}

@app.get("/api/certificates/{filename}")
async def get_certificate(filename: str):
    """Serve certificate files"""
    # Use absolute path relative to backend directory
    file_path = backend_dir / "storage" / "certificates" / filename
    
    # Also try relative path for backward compatibility
    if not file_path.exists():
        alt_path = Path("storage/certificates") / filename
        if alt_path.exists():
            file_path = alt_path
        else:
            raise HTTPException(status_code=404, detail=f"Certificate file not found: {filename}")
    
    # Determine media type
    ext = file_path.suffix.lower()
    media_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png"
    }
    media_type = media_types.get(ext, "application/octet-stream")
    
    # Extract original filename (remove timestamp prefix if present)
    # Format: {user_id}_{timestamp}_{original_filename}
    original_filename = filename
    if "_" in filename:
        parts = filename.split("_", 2)
        if len(parts) >= 3 and len(parts[1]) == 15:  # timestamp format YYYYMMDD_HHMMSS
            original_filename = parts[2]  # Get the original filename
    
    # Ensure all files download with proper headers
    # Use attachment for all file types to force download
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=original_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{original_filename}"',
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff"
        }
    )

@app.post("/api/certifications")
def add_certification(
    certification: CertificationItem,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Add a new certification"""
    issue_date = None
    expiry_date = None
    if certification.issue_date:
        issue_date = datetime.fromisoformat(certification.issue_date).date()
    if certification.expiry_date:
        expiry_date = datetime.fromisoformat(certification.expiry_date).date()
    
    new_cert = CertificationDB(
        user_id=user_id,
        name=certification.name,
        issuing_organization=certification.issuing_organization,
        issue_date=issue_date,
        expiry_date=expiry_date,
        certificate_path=certification.certificate_path
    )
    db.add(new_cert)
    db.commit()
    db.refresh(new_cert)
    return {"success": True, "certification": new_cert.to_dict()}

@app.delete("/api/certifications/{cert_id}")
def delete_certification(
    cert_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Delete a certification"""
    cert = db.query(CertificationDB).filter(
        and_(CertificationDB.id == cert_id, CertificationDB.user_id == user_id)
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    db.delete(cert)
    db.commit()
    return {"success": True}

# ========= Research endpoints =========

# Current Projects
class CurrentProjectItem(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    status: str = "ongoing"

@app.get("/api/current-projects")
def list_current_projects(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get all current projects for a user"""
    projects = db.query(CurrentProjectDB).filter(
        CurrentProjectDB.user_id == user_id
    ).order_by(CurrentProjectDB.start_date.desc()).all()
    return {"projects": [p.to_dict() for p in projects]}

@app.post("/api/current-projects")
def add_current_project(
    project: CurrentProjectItem,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Add a new current project"""
    start_date = None
    if project.start_date:
        start_date = datetime.fromisoformat(project.start_date).date()
    
    new_project = CurrentProjectDB(
        user_id=user_id,
        title=project.title,
        description=project.description,
        start_date=start_date,
        status=project.status
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return {"success": True, "project": new_project.to_dict()}

@app.delete("/api/current-projects/{project_id}")
def delete_current_project(
    project_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Delete a current project"""
    project = db.query(CurrentProjectDB).filter(
        and_(CurrentProjectDB.id == project_id, CurrentProjectDB.user_id == user_id)
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"success": True}

# Research Proposals
class ResearchProposalItem(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    submission_date: Optional[str] = None
    status: str = "draft"
    proposal_file_path: Optional[str] = None

@app.get("/api/research-proposals")
def list_research_proposals(
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Get all research proposals for a user"""
    proposals = db.query(ResearchProposalDB).filter(
        ResearchProposalDB.user_id == user_id
    ).order_by(ResearchProposalDB.submission_date.desc()).all()
    return {"proposals": [p.to_dict() for p in proposals]}

@app.post("/api/research-proposals")
def add_research_proposal(
    proposal: ResearchProposalItem,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Add a new research proposal"""
    submission_date = None
    if proposal.submission_date:
        submission_date = datetime.fromisoformat(proposal.submission_date).date()
    
    new_proposal = ResearchProposalDB(
        user_id=user_id,
        title=proposal.title,
        description=proposal.description,
        submission_date=submission_date,
        status=proposal.status,
        proposal_file_path=proposal.proposal_file_path
    )
    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)
    return {"success": True, "proposal": new_proposal.to_dict()}

@app.delete("/api/research-proposals/{proposal_id}")
def delete_research_proposal(
    proposal_id: int,
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    """Delete a research proposal"""
    proposal = db.query(ResearchProposalDB).filter(
        and_(ResearchProposalDB.id == proposal_id, ResearchProposalDB.user_id == user_id)
    ).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Research proposal not found")
    db.delete(proposal)
    db.commit()
    return {"success": True}

# ========= Attendance Management endpoints =========

# IMPORTANT: gemini-pro-latest maps to gemini-2.5-pro which can have free-tier quota=0.
# Default to gemini-2.5-flash to avoid 429 quota errors on free tier.
_attendance_router_model_name = os.getenv("ATTENDANCE_ROUTER_MODEL", "gemini-2.5-flash")

class AttendanceMessage(BaseModel):
    message: str

def _extract_json_text(text: str) -> str:
    """Best-effort extraction of JSON from Gemini output."""
    if not text:
        return "{}"
    t = text.strip()
    if "```json" in t:
        t = t.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in t:
        t = t.split("```", 1)[1].split("```", 1)[0].strip()
    return t


def _route_attendance_with_gemini(message: str) -> dict:
    """
    Use Gemini to select TOOL and construct a validated JSON payload.
    Returns:
      {"tool":"...", "payload":{...}} OR {"tool":"ASK","ask":{...}}
    """
    prompt = f"""
You are a strict JSON-only router for an attendance API.

Choose exactly ONE tool:
- create_session
- mark_attendance
- summary
- export_csv
- ASK

Tool payload schemas:
1) create_session
   {{"teacher_id": int, "class_id": int, "subject_id": int, "date_str": "YYYY-MM-DD|today|DD-MM-YYYY"}}
2) mark_attendance
   {{"session_id": int? , "teacher_id": int? , "class_id": int? , "subject_id": int? , "date_str": "YYYY-MM-DD|today|DD-MM-YYYY"?, "present_rolls": "1-30 except 5,10"}}
   Rules:
   - If session_id is missing, you MUST provide teacher_id, class_id, subject_id.
   - present_rolls is REQUIRED.
3) summary
   {{"subject_id": int}}
4) export_csv
   {{"subject_id": int}}

If required fields are missing or ambiguous, respond with:
  {{"tool":"ASK","ask":{{"message":"...", "missing":[...optional...]}}}}

If you can proceed, respond with:
  {{"tool":"<tool_name>","payload":{{...}}}}

Return ONLY valid JSON. No markdown. No extra text.

USER MESSAGE:
{message}
""".strip()

    resp = genai_client.models.generate_content(
        model=_attendance_router_model_name,
        contents=prompt,
    )
    raw = getattr(resp, "text", "") or ""
    json_text = _extract_json_text(raw)
    try:
        data = json.loads(json_text)
        if not isinstance(data, dict):
            return {"tool": "ASK", "ask": {"message": "Invalid router response (not an object)."}}
        return data
    except Exception:
        return {"tool": "ASK", "ask": {"message": "Router returned invalid JSON.", "raw": raw[:500]}}


@app.get("/api/attendance")
def attendance_home():
    """Landing endpoint for attendance API"""
    return {
        "message": "✅ AI Teacher Assistant Attendance API is running.",
        "routes": [
            "/api/attendance/agent",
            "/api/attendance/upload-roster",
        ],
    }

@app.post("/api/attendance/agent")
def attendance_agent_endpoint(payload: AttendanceMessage):
    """AI-powered attendance endpoint (Gemini router + DB operations)."""
    try:
        routed = _route_attendance_with_gemini(payload.message or "")
        tool = (routed.get("tool") or "ASK").strip()

        if tool == "ASK":
            return {"ok": False, "ask": routed.get("ask") or {"message": "Need more information."}}

        payload_obj = routed.get("payload") or {}
        if tool == "create_session":
            result = attendance_create_session(payload_obj)
        elif tool == "mark_attendance":
            result = attendance_mark_attendance(payload_obj)
        elif tool == "summary":
            result = attendance_summary(payload_obj)
        elif tool == "export_csv":
            result = attendance_export_csv(payload_obj)
        else:
            return {"ok": False, "ask": {"message": f"Unknown tool: {tool}"}}

        # Standardize error handling
        if isinstance(result, dict) and result.get("error"):
            return {"tool": tool, "error": result.get("error")}

        return {"tool": tool, **(result if isinstance(result, dict) else {"message": str(result)})}

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


@app.get("/api/attendance/export-csv/{subject_id}")
def download_attendance_csv(subject_id: int):
    """
    Download the exported attendance marksheet (CSV) for a subject.
    This wraps the existing export_csv tool and returns the CSV as a FileResponse.
    """
    try:
        result = attendance_export_csv({"subject_id": subject_id})
        file_path = (result or {}).get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="No attendance data found to export for this subject.")

        p = Path(file_path)
        if not p.is_absolute():
            # Try common bases (backend dir, current working dir)
            candidates = [
                backend_dir / p,
                Path.cwd() / p,
            ]
            for c in candidates:
                if c.exists():
                    p = c
                    break

        if not p.exists():
            raise HTTPException(status_code=404, detail=f"CSV not found on server: {file_path}")

        return FileResponse(
            path=str(p),
            filename=p.name,
            media_type="text/csv",
        )
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/attendance/upload-roster")
async def upload_roster(
    file: UploadFile = File(...),
    class_id: int = 1,
    db: Session = Depends(get_db)
):
    """
    Upload Roster Excel file for a specific division/class.
    Expected columns in Excel: RollNo, Name
    """
    try:
        import pandas as pd
        from io import BytesIO
        
        # Read file content
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))

        # Validate expected columns
        expected = {"RollNo", "Name"}
        if not expected.issubset(df.columns):
            raise HTTPException(
                status_code=400,
                detail=f"Excel must have columns: {', '.join(expected)}"
            )

        # Ensure the class exists (and its required FK parents) before inserting students
        # Defaults: teacher_id=1, subject_id=1 are enough to satisfy FKs for class creation.
        ensure_attendance_base(db, teacher_id=1, class_id=class_id, subject_id=1)

        # Clear existing students (optional per class)
        db.query(AttendanceStudent).filter(AttendanceStudent.class_id == class_id).delete()

        # Insert all students
        for _, row in df.iterrows():
            db.add(
                AttendanceStudent(
                    roll_no=int(row["RollNo"]),
                    name=str(row["Name"]),
                    class_id=class_id,
                )
            )

        db.commit()
        return {
            "filename": file.filename,
            "rows_inserted": len(df),
            "status": "Roster uploaded successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)