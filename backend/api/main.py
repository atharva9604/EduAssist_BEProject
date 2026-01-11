# Helper to attach images if image_query present
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
from fastapi import FastAPI, HTTPException, UploadFile, File, Request as FastAPIRequest
from starlette.requests import Request as StarletteRequest
from starlette.requests import Request as StarletteRequest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv
load_dotenv()  # reads backend/.env or project .env if present

# Configure Gemini API key (optional - can use Groq instead)
import google.generativeai as genai
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# At least one API key must be set
if not GEMINI_API_KEY and not GROQ_API_KEY:
    raise RuntimeError("Either GEMINI_API_KEY or GROQ_API_KEY must be set in environment variables. Please create backend/.env file with at least one API key.")

# Configure Gemini if API key is available
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✓ Gemini API configured")
else:
    print("⚠ Gemini API key not set - will use Groq for all requests")

if GROQ_API_KEY:
    print("✓ Groq API configured")
else:
    print("⚠ Groq API key not set - will use Gemini for all requests")

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
from utils.model_manager import ModelManager, ModelType
from utils.image_fetcher import ImageFetcher
import requests

app = FastAPI(title="EduAssist Question Paper Generator API")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents (ContentAnalyzer and QuestionGenerator require Gemini, PPT generator can use either)
try:
    content_analyzer = ContentAnalyzer()
    question_generator = QuestionGenerator()
    print("✓ Content Analyzer and Question Generator initialized (Gemini)")
except RuntimeError as e:
    print(f"⚠ Content Analyzer and Question Generator not available: {e}")
    print("⚠ Question Paper Generator will not work, but PPT Generator will work with Groq")
    content_analyzer = None
    question_generator = None

# PPT Generator works with either Gemini or Groq
content_generator = PPTContentGenerator()
print("✓ PPT Generator initialized")
model_manager = ModelManager()
image_fetcher = ImageFetcher()

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
class PreferredImageUrl(BaseModel):
    slide_number: int
    url: str

class CustomSlideContent(BaseModel):
    """User-provided content for a specific slide"""
    slide_number: int
    title: str
    content: List[str]  # Bullet points
    image_url: Optional[str] = None
    speaker_notes: Optional[str] = None

class SlideStructure(BaseModel):
    """User-defined slide structure/titles"""
    slide_number: int
    title: str

class PPTGenerationRequest(BaseModel):
    topic: str
    content: str
    subject: Optional[str] = None
    module: Optional[str] = None
    num_slides: int = 8
    model_type: Optional[str] = None  # "gemini" or "groq_llama"
    use_groq: Optional[bool] = None  # Legacy: if True, use Groq
    preferred_image_urls: Optional[List[PreferredImageUrl]] = None  # User-provided image URLs per slide
    custom_slides: Optional[List[CustomSlideContent]] = None  # User-provided slide content
    slide_structure: Optional[List[SlideStructure]] = None  # User-defined slide titles/structure

class PPTMultiTopicRequest(BaseModel):
    topics: List[str]
    subject: str
    num_slides: Optional[int] = None
    model_type: Optional[str] = None  # "gemini" or "groq_llama"
    use_groq: Optional[bool] = None  # Legacy: if True, use Groq
    preferred_image_urls: Optional[List[PreferredImageUrl]] = None  # User-provided image URLs per slide
    custom_slides: Optional[List[CustomSlideContent]] = None  # User-provided slide content
    slide_structure: Optional[List[SlideStructure]] = None  # User-defined slide titles/structure

class PPTResponse(BaseModel):
    success: bool
    message: str
    presentation_id: Optional[str] = None
    file_path: Optional[str] = None

# Assist (chat) models
class AssistRequest(BaseModel):
    prompt: str
    model_type: Optional[str] = None  # "gemini" or "groq_llama"
    use_groq: Optional[bool] = None   # Legacy flag

class AssistResponse(BaseModel):
    success: bool
    type: str
    message: str
    link: Optional[str] = None
    filename: Optional[str] = None
    questions: Optional[dict] = None
    summary: Optional[dict] = None
    raw: Optional[dict] = None

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
    if content_analyzer is None:
        raise HTTPException(
            status_code=503, 
            detail="Content Analyzer requires GEMINI_API_KEY. Please set it in backend/.env file or use PPT Generator which works with Groq."
        )
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

        # Determine model type
        model_type = None
        if request.model_type:
            model_type = request.model_type.lower()
        elif request.use_groq:
            model_type = "groq_llama"
        
        # Combine user inputs for model detection
        user_input = f"{request.topic} {request.subject or ''} {request.module or ''} {request.content[:100]}"
        
        # Convert custom slides and structure to dict format
        custom_slides_dict = None
        if request.custom_slides:
            custom_slides_dict = [
                {
                    "slide_number": cs.slide_number,
                    "title": cs.title,
                    "content": cs.content,
                    "image_url": cs.image_url,
                    "speaker_notes": cs.speaker_notes
                }
                for cs in request.custom_slides
            ]
        
        slide_structure_dict = None
        if request.slide_structure:
            slide_structure_dict = [
                {
                    "slide_number": ss.slide_number,
                    "title": ss.title
                }
                for ss in request.slide_structure
            ]
        
        # Detect mode for legacy endpoint
        ppt_mode = "auto_generate"
        if custom_slides_dict or slide_structure_dict:
            ppt_mode = "user_specified"
        
        # Use new redesigned generation method
        slide_data = content_generator.generate_slide_content_new(
            topic=request.topic,
            content=final_content,
            num_slides=request.num_slides,
            subject=request.subject,
            module=request.module,
            model_type=model_type,
            user_input=user_input,
            custom_slides=custom_slides_dict,
            slide_structure=slide_structure_dict,
            ppt_mode=ppt_mode,
        )
        # Apply preferred image URLs if provided (for slides without custom content)
        if request.preferred_image_urls:
            preferred_dicts = [{"slide_number": img.slide_number, "url": img.url} for img in request.preferred_image_urls]
            slide_data = _apply_image_requests(slide_data, preferred_dicts)
        slide_data = _attach_images(slide_data, max_images=4)

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
        # Determine model type
        model_type = None
        if request.model_type:
            model_type = request.model_type.lower()
        elif request.use_groq:
            model_type = "groq_llama"
        
        # Combine user inputs for model detection
        user_input = f"{' '.join(request.topics)} {request.subject}"
        
        # Convert custom slides and structure to dict format
        custom_slides_dict = None
        if request.custom_slides:
            custom_slides_dict = [
                {
                    "slide_number": cs.slide_number,
                    "title": cs.title,
                    "content": cs.content,
                    "image_url": cs.image_url,
                    "speaker_notes": cs.speaker_notes
                }
                for cs in request.custom_slides
            ]
        
        slide_structure_dict = None
        if request.slide_structure:
            slide_structure_dict = [
                {
                    "slide_number": ss.slide_number,
                    "title": ss.title
                }
                for ss in request.slide_structure
            ]
        
        slide_data = content_generator.generate_slides_for_topics(
            request.topics,
            request.subject,
            total_slides=request.num_slides,
            min_slides_per_topic=3,
            model_type=model_type,
            user_input=user_input,
            custom_slides=custom_slides_dict,
            slide_structure=slide_structure_dict,
        )
        # Apply preferred image URLs if provided (for slides without custom content)
        if request.preferred_image_urls:
            preferred_dicts = [{"slide_number": img.slide_number, "url": img.url} for img in request.preferred_image_urls]
            slide_data = _apply_image_requests(slide_data, preferred_dicts)
        slide_data = _attach_images(slide_data, max_images=4)

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

# ========= Assist (chat) endpoint =========

def _safe_int(val, default=0):
    try:
        iv = int(val)
        return iv if iv >= 0 else default
    except Exception:
        return default

def _detect_ppt_mode(prompt: str, slide_structure: List[Dict], custom_slides: List[Dict], image_requests: List[Dict]) -> str:
    """Detect which mode to use: 'user_specified' (Mode 1) or 'auto_generate' (Mode 2).
    
    Mode 1 (user_specified): User provided explicit instructions
    - Has slide structure (titles)
    - Has custom content/bullets
    - Has image assignments
    - Has detailed instructions
    
    Mode 2 (auto_generate): Simple prompt, agent should auto-generate
    - Just topic, subject, num_slides
    - No explicit structure or content
    """
    # Check for explicit user specifications
    has_structure = slide_structure and len(slide_structure) > 0
    has_custom_content = custom_slides and len(custom_slides) > 0
    has_image_assignments = image_requests and len(image_requests) > 0
    
    # Check for explicit instructions in prompt
    prompt_lower = str(prompt).lower()
    explicit_keywords = [
        "slide", "title:", "use exactly", "use these bullets", "for slide",
        "structure:", "with this structure", "custom content", "exactly these",
        "do not change", "as specified", "use the", "uploaded image"
    ]
    has_explicit_instructions = any(keyword in prompt_lower for keyword in explicit_keywords)
    
    # Mode 1: User has provided explicit specifications
    if has_structure or has_custom_content or has_image_assignments or has_explicit_instructions:
        print(f"🔍 MODE DETECTION: Mode 1 (User-Specified) detected")
        print(f"  - Has structure: {has_structure} ({len(slide_structure) if slide_structure else 0} entries)")
        print(f"  - Has custom content: {has_custom_content} ({len(custom_slides) if custom_slides else 0} entries)")
        print(f"  - Has image assignments: {has_image_assignments} ({len(image_requests) if image_requests else 0} entries)")
        print(f"  - Has explicit instructions: {has_explicit_instructions}")
        return "user_specified"
    
    # Mode 2: Simple prompt, auto-generate
    print(f"🔍 MODE DETECTION: Mode 2 (Auto-Generate) detected - simple prompt, will use intelligent generation")
    return "auto_generate"

def _extract_custom_slides_from_prompt(prompt: str, slide_structure: Optional[List[Dict]] = None) -> List[Dict]:
    """Extract custom slide content from user prompt.
    
    Handles patterns like:
    - Slide 1 title: Introduction
    Content bullets:
    1. Point one
    2. Point two
    - For slide 2, use exactly these bullets:
    1. Point one
    2. Point two
    """
    import re
    custom_slides = []
    
    # Create a map of slide_number -> title from slide_structure (if provided)
    structure_title_map = {}
    if slide_structure:
        for ss in slide_structure:
            if isinstance(ss, dict) and ss.get("slide_number") and ss.get("title"):
                structure_title_map[ss.get("slide_number")] = ss.get("title")
    
    # Pattern 1: "Slide X title: Y" followed by content bullets
    # Matches: "Slide 1 title: Introduction to CNNs" or "Slide 2 title: Architecture"
    # Handle markdown quotes (>) and bullet points (-, *)
    slide_pattern = r'(?:^|\n)[>]?\s*[-*]?\s*Slide\s+(\d+)\s+title:\s*([^\n]+)'
    
    # Find all slide title matches
    matches = list(re.finditer(slide_pattern, prompt, re.IGNORECASE | re.MULTILINE))
    print(f"🔍 DEBUG: Found {len(matches)} slide title matches in prompt")
    
    for match in matches:
        slide_num = int(match.group(1))
        title = match.group(2).strip()
        print(f"🔍 DEBUG: Processing slide {slide_num}: title='{title}'")
        
        # Find content bullets after this slide title
        # Look for "Content bullets:" or "Content:" or numbered list starting after the title
        start_pos = match.end()
        next_slide_match = None
        if matches.index(match) + 1 < len(matches):
            next_slide_match = matches[matches.index(match) + 1]
            end_pos = next_slide_match.start()
        else:
            end_pos = len(prompt)
        
        content_section = prompt[start_pos:end_pos]
        print(f"🔍 DEBUG: Content section for slide {slide_num} (length={len(content_section)}):\n{content_section[:200]}")
        
        # Extract bullets - look for numbered list (1., 2., etc.) or bullet points (-, *)
        bullets = []
        
        # Pattern for numbered bullets: "1. text" or "1) text"
        numbered_pattern = r'^\s*\d+[.)]\s+(.+)$'
        # Pattern for bullet points: "- text" or "* text"
        bullet_pattern = r'^\s*[-*]\s+(.+)$'
        
        for line in content_section.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Skip "Content bullets:" or "Content:" headers
            if re.match(r'^content\s*(?:bullets?)?:?\s*$', line, re.IGNORECASE):
                continue
            
            # Try numbered pattern
            num_match = re.match(numbered_pattern, line)
            if num_match:
                bullet_text = num_match.group(1).strip()
                bullets.append(bullet_text)
                print(f"  ✓ Extracted bullet: {bullet_text[:50]}...")
                continue
            
            # Try bullet pattern
            bullet_match = re.match(bullet_pattern, line)
            if bullet_match:
                bullet_text = bullet_match.group(1).strip()
                bullets.append(bullet_text)
                print(f"  ✓ Extracted bullet: {bullet_text[:50]}...")
                continue
        
        # CRITICAL: Only create custom_slides entry if we have ACTUAL CONTENT (bullets)
        # If only title is found (no bullets), it should go to slide_structure, not custom_slides
        if title and bullets and len(bullets) > 0:
            custom_slides.append({
                "slide_number": slide_num,
                "title": title,
                "content": bullets
            })
            print(f"✓ Added custom slide {slide_num} with {len(bullets)} bullets")
        elif title:
            # Title found but no content - this should be handled by slide_structure extraction, not custom_slides
            print(f"⚠ Skipping slide {slide_num} - has title '{title}' but no content bullets (will be handled by slide_structure)")
        else:
            print(f"⚠ Skipping slide {slide_num} - no title found")
    
    # Pattern 2: "For slide X, use exactly these bullets:" or "For slide X, use these bullets:"
    # This pattern handles cases where the title is mentioned separately in the structure
    # More flexible: allows optional punctuation and doesn't require immediate newline
    # Handle markdown quotes (>) and bullet points (-, *)
    for_slide_pattern = r'(?:^|\n)[>]?\s*[-*]?\s*For\s+slide\s+(\d+)[,.]?\s*(?:use\s+)?(?:exactly\s+)?(?:these\s+)?(?:bullets?|points?|content)[:.]?\s*(?:\n|$)'
    for_slide_matches = list(re.finditer(for_slide_pattern, prompt, re.IGNORECASE | re.MULTILINE))
    print(f"🔍 DEBUG: Found {len(for_slide_matches)} 'For slide X' matches in prompt")
    for match in for_slide_matches:
        print(f"  - Match: '{prompt[max(0, match.start()-20):match.end()+20]}'")
    
    for match in for_slide_matches:
        slide_num = int(match.group(1))
        print(f"🔍 DEBUG: Processing 'For slide {slide_num}' pattern")
        
        # Get title from structure map if available
        title = structure_title_map.get(slide_num, "")
        if title:
            print(f"  ✓ Found title from structure map: '{title}'")
        
        if not title:
            # Try to find title in the prompt near this slide number
            # Look for "Slide X title: Y" before this match
            before_text = prompt[:match.start()]
            title_match = re.search(rf'Slide\s+{slide_num}\s+title:\s*([^\n]+)', before_text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up title (remove trailing punctuation)
                title = re.sub(r'[.,;:]+$', '', title).strip()
                print(f"  ✓ Found title from prompt: '{title}'")
        
        if not title:
            print(f"  ⚠ WARNING: No title found for slide {slide_num} - will try to extract without title")
            # Don't skip - we can still extract bullets and use slide number
        
        # Find content bullets after this "For slide X" statement
        start_pos = match.end()
        # Look for next "For slide" or "Slide" or end of prompt
        next_pattern = rf'(?:For\s+slide|Slide\s+\d+|$)'
        next_match = re.search(next_pattern, prompt[start_pos:], re.IGNORECASE | re.MULTILINE)
        if next_match:
            end_pos = start_pos + next_match.start()
        else:
            end_pos = len(prompt)
        
        content_section = prompt[start_pos:end_pos]
        print(f"🔍 DEBUG: Content section for slide {slide_num} (length={len(content_section)}):\n{content_section[:200]}")
        
        # Extract bullets - look for numbered list (1., 2., etc.) or bullet points (-, *)
        bullets = []
        
        # Pattern for numbered bullets: "1. text" or "1) text"
        numbered_pattern = r'^\s*\d+[.)]\s+(.+)$'
        # Pattern for bullet points: "- text" or "* text"
        bullet_pattern = r'^\s*[-*]\s+(.+)$'
        
        for line in content_section.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Skip "Content bullets:" or "Content:" headers
            if re.match(r'^content\s*(?:bullets?)?:?\s*$', line, re.IGNORECASE):
                continue
            
            # Skip "For slide" or "Slide" lines
            if re.match(r'^(?:For\s+)?slide\s+\d+', line, re.IGNORECASE):
                continue
            
            # Try numbered pattern
            num_match = re.match(numbered_pattern, line)
            if num_match:
                bullet_text = num_match.group(1).strip()
                bullets.append(bullet_text)
                print(f"  ✓ Extracted bullet: {bullet_text[:50]}...")
                continue
            
            # Try bullet pattern
            bullet_match = re.match(bullet_pattern, line)
            if bullet_match:
                bullet_text = bullet_match.group(1).strip()
                bullets.append(bullet_text)
                print(f"  ✓ Extracted bullet: {bullet_text[:50]}...")
                continue
        
        # Add custom slide if we have bullets
        if bullets and len(bullets) > 0:
            # Check if we already have this slide in custom_slides (from pattern 1)
            existing_idx = None
            for idx, cs in enumerate(custom_slides):
                if cs.get("slide_number") == slide_num:
                    existing_idx = idx
                    break
            
            if existing_idx is not None:
                # Update existing entry with bullets
                if title:
                    custom_slides[existing_idx]["title"] = title
                custom_slides[existing_idx]["content"] = bullets
                print(f"✓ Updated custom slide {slide_num} with {len(bullets)} bullets" + (f" and title '{title}'" if title else ""))
            else:
                # Create new entry (even without title, we can use it from structure later)
                custom_slides.append({
                    "slide_number": slide_num,
                    "title": title or "",  # Allow empty title - will be filled from structure
                    "content": bullets
                })
                print(f"✓ Added custom slide {slide_num} with {len(bullets)} bullets" + (f" and title '{title}'" if title else " (title will come from structure)"))
    
    print(f"🔍 DEBUG: Extracted {len(custom_slides)} custom slides total")
    return custom_slides

def _extract_slide_structure_from_prompt(prompt: str) -> List[Dict]:
    """Extract slide structure (titles) from user prompt.
    
    Handles patterns like:
    - Slide 1 title: Introduction
    - Slide 2 title: Architecture
    - Slide 1: Introduction to Computer Networks (Mode 2 format)
    - Use the first uploaded image on slide 1 title Introduction to CNNs
    - slide 1 title Introduction to CNNs
    """
    import re
    slide_structure = []
    
    # Pattern 0: "Slide titles:" section with "Slide X: Title" (Mode 2 format)
    # This is the most common format from PPT Modes UI
    titles_section_match = re.search(r'Slide\s+titles?\s*:?\s*\n', prompt, re.IGNORECASE | re.MULTILINE)
    if titles_section_match:
        titles_section = prompt[titles_section_match.end():]
        # Stop at "Generate" or end of prompt
        generate_match = re.search(r'\n\s*[Gg]enerate', titles_section, re.IGNORECASE)
        if generate_match:
            titles_section = titles_section[:generate_match.start()]
        
        # Pattern: "Slide 1: Title" in the titles section
        mode2_pattern = r'Slide\s+(\d+)\s*:\s*([^\n]+?)(?=\s*(?:Slide\s+\d+|Generate|$))'
        mode2_matches = list(re.finditer(mode2_pattern, titles_section, re.IGNORECASE | re.MULTILINE))
        for match in mode2_matches:
            slide_num = int(match.group(1))
            title = match.group(2).strip().rstrip('.,;')
            # Remove "Generate content" if present
            if 'generate' in title.lower():
                title = re.split(r'\s+[Gg]enerate', title, maxsplit=1)[0].strip()
            if title and len(title) > 2:
                slide_structure.append({
                    "slide_number": slide_num,
                    "title": title
                })
        if slide_structure:
            print(f"🔍 DEBUG: Found {len(slide_structure)} titles using Mode 2 pattern")
            return slide_structure
    
    # Pattern 1: "Slide X title: Y" (may or may not have content)
    # Handle markdown quotes (>) and bullet points (-, *)
    pattern1 = r'(?:^|\n)[>]?\s*[-*]?\s*Slide\s+(\d+)\s+title:\s*([^\n]+)'
    matches1 = list(re.finditer(pattern1, prompt, re.IGNORECASE | re.MULTILINE))
    
    # Pattern 2: "slide X title Y" (without colon, e.g., "slide 1 title Introduction")
    # This should match "slide 1 title Introduction to CNNs" (capture everything after "title")
    # Handle markdown quotes (>) and bullet points (-, *)
    pattern2 = r'(?:^|\n)[>]?\s*[-*]?\s*slide\s+(\d+)\s+title\s+([^\n,]+?)(?:\s*$|\s*[,;]|\s*title|\s*Content)'
    matches2 = list(re.finditer(pattern2, prompt, re.IGNORECASE | re.MULTILINE))
    
    # Pattern 3: "on slide X title Y" (e.g., "use image on slide 1 title Introduction to CNNs")
    # This should capture the full title after "title" - improved to handle more cases
    pattern3 = r'(?:use|using|put|place).*?on\s+slide\s+(\d+)\s+title\s+([^\n\-]+?)(?:\s*$|\s*[-]|\s*[,;]|\s*You|\s*Content|\s*Use)'
    matches3 = list(re.finditer(pattern3, prompt, re.IGNORECASE | re.MULTILINE))
    
    # Pattern 4: More flexible - "slide X title Y" anywhere in the line
    # Handle markdown quotes (>) and bullet points (-, *)
    pattern4 = r'(?:^|\n)[>]?\s*[-*]?\s*.*?slide\s+(\d+)\s+title\s+([^\n\-]+?)(?:\s*$|\s*[-]|\s*[,;]|\s*You|\s*Content|\s*Use)'
    matches4 = list(re.finditer(pattern4, prompt, re.IGNORECASE | re.MULTILINE))
    
    # Combine all matches
    all_matches = matches1 + matches2 + matches3 + matches4
    
    # Create a map to avoid duplicates (prefer later matches if same slide number)
    structure_map = {}
    for match in all_matches:
        slide_num = int(match.group(1))
        title = match.group(2).strip()
        # Clean up title (remove trailing punctuation, etc.)
        title = re.sub(r'[.,;:]+$', '', title).strip()
        if title:
            structure_map[slide_num] = title
    
    # Convert to list
    for slide_num, title in structure_map.items():
        slide_structure.append({
            "slide_number": slide_num,
            "title": title
        })
    
    # Debug logging
    if slide_structure:
        print(f"🔍 DEBUG: Extracted {len(slide_structure)} slide structure entries:")
        for ss in slide_structure:
            print(f"  - Slide {ss.get('slide_number')}: '{ss.get('title')}'")
    
    return slide_structure

@app.post("/api/assist", response_model=AssistResponse)
async def assist(req: StarletteRequest):
    """
    Routing assistant: classify prompt into PPT / Question Paper / General,
    extract params, call existing generators, and return result.
    Supports both JSON body (legacy) and multipart/form-data with image uploads.
    """
    content_type = req.headers.get("content-type", "")
    
    if "multipart/form-data" in content_type:
        # Handle multipart/form-data with file uploads
        form = await req.form()
        prompt = form.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        if isinstance(prompt, list):
            prompt = prompt[0]
        
        # Handle uploaded images - can be single file or list
        uploaded_image_paths = []
        
        # Debug: Check what form fields we have
        print(f"🔍 DEBUG: Form fields: {list(form.keys())}")
        
        # Try multiple ways to get images
        images_data = []
        
        # Method 1: Try getlist
        try:
            images_list = form.getlist("images")
            if images_list:
                images_data = images_list
                print(f"🔍 DEBUG: Got {len(images_data)} images via getlist")
        except Exception as e:
            print(f"⚠ DEBUG: getlist failed: {e}")
        
        # Method 2: Try single get
        if not images_data:
            try:
                single_image = form.get("images")
                if single_image:
                    images_data = [single_image]
                    print(f"🔍 DEBUG: Got 1 image via get")
            except Exception as e:
                print(f"⚠ DEBUG: get failed: {e}")
        
        # Method 3: Check all form entries for files
        if not images_data:
            print(f"🔍 DEBUG: Checking all form entries for files...")
            for key, value in form.items():
                print(f"  Key: {key}, Type: {type(value)}, Is UploadFile: {isinstance(value, UploadFile)}")
                if isinstance(value, UploadFile) and value.filename:
                    images_data.append(value)
                    print(f"  Found file: {value.filename}")
        
        print(f"🔍 DEBUG: Final images_data: {len(images_data)} items")
        
        if images_data:
            import uuid
            import shutil
            upload_dir = Path("storage/presentations/images/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle both single file and multiple files
            if not isinstance(images_data, list):
                images_data = [images_data]
            
            for idx, img_file in enumerate(images_data):
                print(f"🔍 DEBUG: Processing image {idx}: type={type(img_file)}, filename={getattr(img_file, 'filename', 'N/A')}")
                
                # Check if it's an UploadFile by checking for required attributes
                # FastAPI's UploadFile is actually starlette.datastructures.UploadFile
                has_filename = hasattr(img_file, 'filename') and img_file.filename
                has_read = hasattr(img_file, 'read')
                
                if has_filename and has_read:
                    if not img_file.filename:
                        print(f"⚠ DEBUG: Image {idx} has no filename, skipping")
                        continue
                    
                    # Validate image file
                    if not any(img_file.filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                        print(f"⚠ DEBUG: Image {idx} has invalid extension: {img_file.filename}")
                        continue
                    
                    # Save uploaded image
                    file_ext = Path(img_file.filename).suffix or '.jpg'
                    unique_name = f"{uuid.uuid4().hex}{file_ext}"
                    file_path = upload_dir / unique_name
                    
                    # Read file content
                    content = await img_file.read()
                    
                    # Check if it's WEBP format (not supported by python-pptx)
                    file_ext_lower = file_ext.lower()
                    if file_ext_lower == '.webp':
                        # Convert WEBP to PNG using PIL/Pillow
                        try:
                            from PIL import Image
                            import io
                            
                            # Open WEBP image from bytes
                            webp_image = Image.open(io.BytesIO(content))
                            # Convert to RGB if necessary (WEBP can have transparency)
                            if webp_image.mode in ('RGBA', 'LA', 'P'):
                                # Create white background for transparency
                                rgb_image = Image.new('RGB', webp_image.size, (255, 255, 255))
                                if webp_image.mode == 'P':
                                    webp_image = webp_image.convert('RGBA')
                                rgb_image.paste(webp_image, mask=webp_image.split()[-1] if webp_image.mode == 'RGBA' else None)
                                webp_image = rgb_image
                            elif webp_image.mode != 'RGB':
                                webp_image = webp_image.convert('RGB')
                            
                            # Save as PNG
                            file_ext = '.png'
                            unique_name = f"{uuid.uuid4().hex}{file_ext}"
                            file_path = upload_dir / unique_name
                            
                            webp_image.save(file_path, 'PNG')
                            print(f"✓ Converted WEBP to PNG: {file_path}")
                        except ImportError:
                            print(f"⚠ PIL/Pillow not installed. Cannot convert WEBP. Please install: pip install Pillow")
                            # Fallback: save as-is (will fail later, but at least we tried)
                            with open(file_path, "wb") as f:
                                f.write(content)
                        except Exception as e:
                            print(f"⚠ Failed to convert WEBP: {e}. Saving as-is (may fail in PPT)")
                            with open(file_path, "wb") as f:
                                f.write(content)
                    else:
                        # Save other formats as-is
                        with open(file_path, "wb") as f:
                            f.write(content)
                    
                    # Store absolute path
                    abs_file_path = os.path.abspath(file_path)
                    uploaded_image_paths.append(abs_file_path)
                    print(f"✓ Uploaded image saved: {abs_file_path}")
                    print(f"  File exists: {os.path.exists(abs_file_path)}, Size: {os.path.getsize(abs_file_path)} bytes")
                else:
                    print(f"⚠ DEBUG: Image {idx} is not UploadFile, type: {type(img_file)}")
        
        print(f"🔍 DEBUG: Total uploaded images: {len(uploaded_image_paths)}")
        
        # Get model type from form
        model_type_form = form.get("model_type")
        use_groq_form = form.get("use_groq")
        
        effective_model_type = None
        if model_type_form:
            effective_model_type = str(model_type_form).lower()
        elif use_groq_form:
            effective_model_type = "groq_llama"
        if effective_model_type is None:
            effective_model_type = model_manager.detect_model_preference(str(prompt), model_manager.gemini_api_key and "gemini" or "groq_llama")
    else:
        # Handle JSON body (legacy)
        try:
            body = await req.json()
            request = AssistRequest(**body)
            prompt = request.prompt
            effective_model_type = None
            if request.model_type:
                effective_model_type = request.model_type.lower()
            elif request.use_groq:
                effective_model_type = "groq_llama"
            if effective_model_type is None:
                effective_model_type = model_manager.detect_model_preference(prompt, model_manager.gemini_api_key and "gemini" or "groq_llama")
            uploaded_image_paths = []
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")

    # LLM prompt to extract structure
    router_prompt = f"""
You are an assistant that routes teacher requests.
Return ONLY JSON (no text) with this shape:
{{
  "intent": "ppt" | "question_paper" | "general",
  "ppt": {{
    "topics": ["topic1","topic2"],
    "subject": "subject name",
    "num_slides": 10,
    "content": "optional content or empty",
    "module": ""
  }},
  "question_paper": {{
    "content": "text to generate questions from",
    "num_mcq": 5,
    "num_short": 3,
    "num_long": 2,
    "marks_mcq": 1,
    "marks_short": 3,
    "marks_long": 5,
    "difficulty": "medium"
  }},
  "image_requests": [
    {{"slide_number": 2, "query": "cats overview"}},
    {{"slide_number": 4, "query": "rnn architecture diagram"}},
    {{"slide_number": 3, "url": "https://example.com/architecture.png"}}
  ],
  "custom_slides": [
    {{"slide_number": 3, "title": "Architecture", "content": ["bullet 1", "bullet 2"], "image_url": "https://example.com/img.png"}}
  ],
  "slide_structure": [
    {{"slide_number": 1, "title": "Introduction"}},
    {{"slide_number": 2, "title": "Architecture"}},
    {{"slide_number": 3, "title": "Applications"}}
  ],
  "answer": "short helpful answer for general intent"
}}

Rules:
- If the user asks for PPT or slides → intent = "ppt"
- If asks for questions, exam, quiz, paper → intent = "question_paper"
- Otherwise intent = "general"
- If multiple lines look like topics, put them in ppt.topics
- CRITICAL: Extract num_slides from user prompt (e.g., "5 slides", "10-slide", "create 8 slides") - if user provides custom content for specific slides, use the highest slide number as num_slides
- CRITICAL: If user provides FULL content for slides (e.g., "Slide 1 title: X, Content bullets: 1. ... 2. ..."), extract ALL of it in custom_slides with exact title and content array
- CRITICAL: If user says "I will provide content for each slide" or "you only format it", extract ALL custom_slides with exact titles and content provided
- CRITICAL: If user provides slide structure with titles (e.g., "slide 1 title: Intro, slide 2 title: Architecture"), extract in slide_structure
- If user provides image URLs for a specific slide, extract in image_requests with "url" field AND slide_number
- If user mentions "slide X title Y" with an image URL, also add to image_requests with that slide_number
- Architecture slides are typically slide_number 2-4, so prioritize URLs there if mentioned
- Examples: "Slide 1 title: Introduction, Content bullets: 1. Point one 2. Point two" → custom_slides with slide_number=1, title="Introduction", content=["Point one", "Point two"]
- Examples: "slide 3 title Architecture, add these points: [list], image: [url]" → custom_slides
- Examples: "use this image url [url] on slide 3 title Architecture" → image_requests with slide_number 3 and url
- Examples: "create 4 slides: slide 1 Intro, slide 2 Architecture" → slide_structure
"""
    raw = {}
    try:
        resp_text = model_manager.generate_content(router_prompt + "\nUSER PROMPT:\n" + prompt, effective_model_type)
        if "```json" in resp_text:
            resp_text = resp_text.split("```json")[1].split("```", 1)[0].strip()
        elif "```" in resp_text:
            resp_text = resp_text.split("```", 1)[1].split("```", 1)[0].strip()
        raw = json.loads(resp_text)
    except Exception:
        raw = {}

    intent = (raw.get("intent") or "").lower() if isinstance(raw, dict) else ""
    ppt_cfg = raw.get("ppt") if isinstance(raw, dict) else {}
    qp_cfg = raw.get("question_paper") if isinstance(raw, dict) else {}
    image_requests = raw.get("image_requests") if isinstance(raw, dict) else []
    custom_slides_raw = raw.get("custom_slides") if isinstance(raw, dict) else []
    slide_structure_raw = raw.get("slide_structure") if isinstance(raw, dict) else []
    
    # CRITICAL: Extract slide structure FIRST (titles) so custom slides can use it
    # Debug: Show first 500 chars of prompt to see format
    prompt_preview = str(prompt)[:500].replace('\n', '\\n')
    print(f"🔍 DEBUG: Prompt preview (first 500 chars): {prompt_preview}")
    
    # CRITICAL: Skip old extraction for Mode 1 and Mode 2 - they use structured parsing
    # Mode 1 prompt contains "Use the default slide structure" and "Generate all content yourself"
    # Mode 2 prompt contains "Slide titles:" section
    prompt_lower = str(prompt).lower()
    is_mode_1 = "use the default slide structure" in prompt_lower and "generate all content yourself" in prompt_lower
    # CRITICAL: Check for Mode 4 FIRST (has "Image placement:") - skip old extraction for Mode 4
    is_mode_4_old_check = "image placement:" in prompt_lower
    is_mode_2 = "slide titles:" in prompt_lower
    is_mode_3 = "use exact content" in prompt_lower and "do not modify" in prompt_lower
    is_mode_5 = "slide instructions:" in prompt_lower
    
    # Skip old extraction if any of the new modes are detected (they have their own parsers)
    extracted_structure = []
    if is_mode_4_old_check or is_mode_3 or is_mode_5:
        print(f"🔍 DEBUG: Mode 4/3/5 detected - skipping old extraction (uses mode-based parser)")
        # Don't run old extraction - mode-based generation will handle it
    elif not is_mode_1 and not is_mode_2:
        extracted_structure = _extract_slide_structure_from_prompt(str(prompt))
    else:
        if is_mode_1:
            print(f"🔍 DEBUG: Mode 1 detected - skipping old extraction (uses default structure)")
        if is_mode_2:
            print(f"🔍 DEBUG: Mode 2 detected - skipping old extraction (uses structured parser)")
    
    if extracted_structure:
        print(f"🔍 Extracted {len(extracted_structure)} slide structure entries from prompt")
        for es in extracted_structure:
            print(f"  - Slide {es.get('slide_number')}: '{es.get('title')}'")
        # Merge with LLM-extracted structure (prefer extracted ones)
        if not slide_structure_raw:
            slide_structure_raw = []
        # Create a map of slide_number -> structure
        existing_structure_map = {ss.get("slide_number"): ss for ss in slide_structure_raw if isinstance(ss, dict)}
        for extracted in extracted_structure:
            slide_num = extracted.get("slide_number")
            if slide_num:
                existing_structure_map[slide_num] = extracted
                print(f"  ✓ Added/updated structure for slide {slide_num}: '{extracted.get('title')}'")
        slide_structure_raw = list(existing_structure_map.values())
        print(f"🔍 Final slide_structure_raw: {len(slide_structure_raw)} slides")
        for ss in slide_structure_raw:
            print(f"  Final structure: Slide {ss.get('slide_number')} → '{ss.get('title')}'")
    else:
        # CRITICAL: For Mode 2/3/4/5, DO NOT use LLM-extracted structure - it's ILLEGAL
        # Mode 2: User titles are LAW - no LLM structure allowed
        # Mode 3: Exact content is LAW - no LLM structure allowed
        # Mode 4: User titles + images are LAW - no LLM structure allowed
        # Mode 5: User instructions are LAW - no LLM structure allowed
        if is_mode_4_old_check or is_mode_3 or is_mode_5 or is_mode_2:
            mode_list = []
            if is_mode_2: mode_list.append("Mode 2")
            if is_mode_3: mode_list.append("Mode 3")
            if is_mode_4_old_check: mode_list.append("Mode 4")
            if is_mode_5: mode_list.append("Mode 5")
            print(f"🔍 DEBUG: {', '.join(mode_list)} detected - IGNORING LLM-extracted structure (user titles/content are LAW)")
            slide_structure_raw = []  # Clear LLM structure - user titles are the only source
        else:
            print(f"⚠ WARNING: No structure extracted from prompt - checking if structure exists in LLM response")
            if slide_structure_raw:
                print(f"  Found {len(slide_structure_raw)} structure entries from LLM")
    
    # CRITICAL: Also extract custom slides directly from prompt (more reliable than LLM extraction)
    # BUT skip this for Mode 2/3/4/5 as they have their own parsers
    extracted_custom_slides = []
    if not is_mode_4_old_check and not is_mode_3 and not is_mode_5 and not is_mode_2:
        # Pass slide_structure so it can look up titles for "For slide X" patterns
        extracted_custom_slides = _extract_custom_slides_from_prompt(str(prompt), slide_structure=slide_structure_raw)
    else:
        mode_list = []
        if is_mode_2: mode_list.append("Mode 2")
        if is_mode_3: mode_list.append("Mode 3")
        if is_mode_4_old_check: mode_list.append("Mode 4")
        if is_mode_5: mode_list.append("Mode 5")
        print(f"🔍 DEBUG: Skipping old custom slides extraction for {', '.join(mode_list)} (uses mode-based parser)")
    if extracted_custom_slides:
        print(f"🔍 Extracted {len(extracted_custom_slides)} custom slides from prompt")
        # Merge with LLM-extracted custom slides (prefer extracted ones as they're more accurate)
        if not custom_slides_raw:
            custom_slides_raw = []
        # Create a map of slide_number -> custom slide
        existing_map = {cs.get("slide_number"): cs for cs in custom_slides_raw if isinstance(cs, dict)}
        for extracted in extracted_custom_slides:
            slide_num = extracted.get("slide_number")
            if slide_num:
                existing_map[slide_num] = extracted
        custom_slides_raw = list(existing_map.values())
        print(f"🔍 Final custom_slides_raw: {len(custom_slides_raw)} slides")
    
    # Handle uploaded images - map them to slides based on prompt
    print(f"🔍 DEBUG: uploaded_image_paths = {uploaded_image_paths}")
    if uploaded_image_paths:
        import re
        # Extract slide numbers from prompt - look for "slide X" patterns
        slide_num_pattern = r'slide\s+(\d+)'
        prompt_lower = str(prompt).lower()
        slide_matches = list(re.finditer(slide_num_pattern, prompt_lower))
        print(f"🔍 DEBUG: Found {len(slide_matches)} slide number matches in prompt: {[m.group(1) for m in slide_matches]}")
        
        # Check if this is Mode 4 - Mode 4 handles image mapping differently
        is_mode_4_prompt = "image placement:" in prompt_lower
        
        # Map uploaded images to slides
        for idx, img_path in enumerate(uploaded_image_paths):
            slide_num = None
            
            # For Mode 4: Extract "Use Image X on Slide Y" format
            if is_mode_4_prompt:
                image_num = idx + 1  # Image 1, Image 2, etc.
                image_pattern = rf'Use\s+Image\s+{image_num}\s+on\s+Slide\s+(\d+)'
                image_match = re.search(image_pattern, prompt_lower, re.IGNORECASE)
                if image_match:
                    user_slide_num = int(image_match.group(1))
                    # For Mode 4, keep user's slide number (generator will shift it to actual slide number)
                    slide_num = user_slide_num
                    print(f"✓ Mode 4: Found Image {image_num} → user's slide {user_slide_num} (generator will shift to actual slide {user_slide_num + 1})")
                else:
                    print(f"⚠ Mode 4: Could not find 'Use Image {image_num} on Slide X' in prompt")
            else:
                # Non-Mode 4: Use ordinal words or other patterns
                ordinal_words = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]
                ordinal_word = ordinal_words[idx] if idx < len(ordinal_words) else None
                
                if ordinal_word:
                    # Pattern: "Use the first/second/third uploaded image on slide X"
                    ordinal_pattern = rf'(?:also\s+)?(?:and\s+)?use\s+(?:the\s+)?{ordinal_word}\s+(?:uploaded\s+)?image.*?slide\s+(\d+)'
                    ordinal_match = re.search(ordinal_pattern, prompt_lower, re.IGNORECASE)
                    if ordinal_match:
                        user_slide_num = int(ordinal_match.group(1))
                        # Shift by +1: user's slide 1 → actual slide 2 (since slide 1 is base)
                        slide_num = user_slide_num + 1
                        print(f"✓ Found slide number for {ordinal_word} image: user's slide {user_slide_num} → actual slide {slide_num}")
                
                # Fallback: Try to find slide number mentioned in prompt
                if slide_num is None and slide_matches:
                    # Check if prompt mentions "use this image on slide X"
                    image_mention_pattern = r'use\s+(?:this\s+)?image.*?slide\s+(\d+)'
                    image_mention_match = re.search(image_mention_pattern, prompt_lower)
                    if image_mention_match:
                        user_slide_num = int(image_mention_match.group(1))
                        slide_num = user_slide_num + 1  # Shift by +1
                        print(f"✓ Found explicit slide number for image: user's slide {user_slide_num} → actual slide {slide_num}")
                    else:
                        # Use the slide number from matches in order
                        if idx < len(slide_matches):
                            user_slide_num = int(slide_matches[idx].group(1))
                            slide_num = user_slide_num + 1  # Shift by +1
                            print(f"✓ Using slide number from match {idx}: user's slide {user_slide_num} → actual slide {slide_num}")
                        else:
                            # Default: assign sequentially starting from slide 2
                            slide_num = idx + 2  # idx 0 → slide 2, idx 1 → slide 3, etc.
                            print(f"✓ Using sequential slide number: slide {slide_num} (user's slide {idx+1})")
                elif slide_num is None:
                    # No slide numbers mentioned - assign sequentially starting from slide 2
                    slide_num = idx + 2  # idx 0 → slide 2, idx 1 → slide 3, etc.
                    print(f"✓ No slide numbers found, using sequential: slide {slide_num} (user's slide {idx+1})")
            
            # Add to image_requests
            if not isinstance(image_requests, list):
                image_requests = []
            
            if is_mode_4_prompt:
                # For Mode 4, store user's slide number (not shifted) - generator will handle shifting
                image_requests.append({
                    "slide_number": slide_num,  # User's slide number (will be shifted by generator)
                    "local_path": img_path,
                    "image_number": idx + 1  # Image 1, Image 2, etc.
                })
                print(f"✓ Mode 4: Mapped Image {idx + 1} (uploaded) to user's slide {slide_num}: {img_path}")
            else:
                image_requests.append({
                    "slide_number": slide_num,  # Already shifted (actual slide number)
                    "local_path": img_path
                })
                print(f"✓ Mapped uploaded image to actual slide {slide_num}: {img_path}")
    else:
        print(f"🔍 DEBUG: No uploaded images found")

    # IMPORTANT: For chat-based PPT generation we now rely ONLY on directly uploaded
    # images (local_path). Ignore URL-based image extraction here to keep behaviour
    # simple and predictable for teachers.
    # Check if this is Mode 4 - if so, don't shift slide numbers (Mode 4 handles this internally)
    is_mode_4_prompt = False
    if prompt:
        prompt_lower = str(prompt).lower()
        is_mode_4_prompt = "image placement:" in prompt_lower
    
    # CRITICAL: Shift all image_requests slide numbers by +1 (user's slide 1 → actual slide 2)
    # EXCEPT for Mode 4, where slide numbers are already handled by the generator
    if isinstance(image_requests, list):
        filtered_requests = []
        for ir in image_requests:
            if isinstance(ir, dict):
                # For Mode 4, don't shift - the generator will handle it
                if is_mode_4_prompt and ir.get("image_number"):
                    # Mode 4: Keep as-is (will be handled by Mode 4 generator)
                    filtered_requests.append(ir)
                elif ir.get("local_path"):
                    # Already shifted in uploaded image mapping above for non-Mode 4
                    filtered_requests.append(ir)
                elif ir.get("slide_number"):
                    # Shift slide numbers from LLM router (user's slide 1 → actual slide 2)
                    # EXCEPT for Mode 4
                    if not is_mode_4_prompt:
                        user_slide_num = ir.get("slide_number")
                        if user_slide_num > 0:
                            ir["slide_number"] = user_slide_num + 1
                            print(f"🔍 Shifted image request: user's slide {user_slide_num} → actual slide {ir['slide_number']}")
                            filtered_requests.append(ir)
                    else:
                        # Mode 4: Don't shift, generator handles it
                        filtered_requests.append(ir)
        image_requests = filtered_requests

    # Heuristic fallback intent
    txt = prompt.lower()
    if not intent:
        if any(k in txt for k in ["ppt", "slides", "presentation"]):
            intent = "ppt"
        elif any(k in txt for k in ["question", "quiz", "exam", "paper"]):
            intent = "question_paper"
        else:
            intent = "general"

    # PPT intent
    if intent == "ppt":
        topics = []
        if isinstance(ppt_cfg, dict):
            topics = ppt_cfg.get("topics") or []
            if isinstance(topics, str):
                topics = [t.strip() for t in topics.split("\n") if t.strip()]
        if not topics:
            # try to split lines from prompt
            lines = [l.strip() for l in prompt.split("\n") if l.strip()]
            if len(lines) > 1:
                topics = lines
        subject = (ppt_cfg or {}).get("subject") or ""
        content = (ppt_cfg or {}).get("content") or ""
        module = (ppt_cfg or {}).get("module") or None
        num_slides = _safe_int((ppt_cfg or {}).get("num_slides"), 10)
        
        # CRITICAL: Also extract num_slides directly from prompt (e.g., "5-slide", "5 slides", "create 5 slides")
        import re
        prompt_lower = str(prompt).lower()
        slide_count_patterns = [
            r'(\d+)[-\s]slide',  # "5-slide" or "5 slide"
            r'create\s+(\d+)\s+slides?',  # "create 5 slides"
            r'(\d+)\s+slides?',  # "5 slides"
        ]
        for pattern in slide_count_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                extracted_num = int(match.group(1))
                if extracted_num > 0:
                    num_slides = extracted_num
                    print(f"🔍 Extracted num_slides={num_slides} from prompt using pattern: {pattern}")
                    break
        
        # CRITICAL: If custom slides or slide structure are provided, use the highest slide number as num_slides
        max_custom_slide = 0
        if custom_slides_raw and isinstance(custom_slides_raw, list):
            for cs in custom_slides_raw:
                if isinstance(cs, dict):
                    slide_num = cs.get("slide_number")
                    if isinstance(slide_num, int):
                        max_custom_slide = max(max_custom_slide, slide_num)
        
        max_structure_slide = 0
        if slide_structure_raw and isinstance(slide_structure_raw, list):
            for ss in slide_structure_raw:
                if isinstance(ss, dict):
                    slide_num = ss.get("slide_number")
                    if isinstance(slide_num, int):
                        max_structure_slide = max(max_structure_slide, slide_num)
        
        # Use the maximum slide number found (this takes priority over extracted num_slides)
        # CRITICAL: Always use the maximum to ensure we don't lose any slides
        if max_custom_slide > 0 or max_structure_slide > 0:
            num_slides = max(num_slides, max_custom_slide, max_structure_slide)
            print(f"🔍 Updated num_slides to {num_slides} based on custom slides/structure (max_custom={max_custom_slide}, max_structure={max_structure_slide})")
        
        # CRITICAL: Double-check - if we have custom slides, ensure num_slides covers all of them
        if custom_slides_raw and isinstance(custom_slides_raw, list):
            all_custom_numbers = [cs.get("slide_number") for cs in custom_slides_raw if isinstance(cs, dict) and cs.get("slide_number")]
            if all_custom_numbers:
                max_found = max(all_custom_numbers)
                if max_found > num_slides:
                    print(f"🔍 WARNING: Found custom slide {max_found} but num_slides is {num_slides}, updating to {max_found}")
                    num_slides = max_found
        
        print(f"🔍 FINAL num_slides: {num_slides}")

        try:
            # CRITICAL: For Mode 2, ALWAYS use mode-based generation (generate_slide_content)
            # Check if this is Mode 2 BEFORE deciding which generator to use
            prompt_lower_mode_check = str(prompt).lower() if prompt else ""
            is_mode_2_early_check = "slide titles:" in prompt_lower_mode_check
            is_mode_4_early_check = "image placement:" in prompt_lower_mode_check
            is_mode_5_early_check = "slide instructions:" in prompt_lower_mode_check
            
            # MODE 5 TOPIC NORMALIZATION: Extract single topic from prompt (subject is NOT a topic)
            if is_mode_5_early_check:
                # For Mode 5, extract topic from prompt properly (not from line splitting)
                # Subject is metadata, NOT a topic - filter it out
                import re
                
                # First, filter out "Subject:" lines from topics list
                filtered_topics = []
                for t in topics:
                    if t and isinstance(t, str):
                        t_lower = t.lower().strip()
                        # Skip lines that are clearly subjects or metadata
                        if not (t_lower.startswith("subject:") or 
                                t_lower.startswith("subject ") or
                                t_lower == "subject" or
                                "module:" in t_lower or
                                "content:" in t_lower):
                            filtered_topics.append(t.strip())
                
                # Extract topic from prompt using patterns
                topic_patterns = [
                    r'(?:create|make|generate).*?(?:\d+[-\s]?slide|ppt).*?on\s+([^\n]+?)(?:\s+subject|$)',  # "Create 3-slide PPT on TOPIC"
                    r'ppt.*?on\s+([^\n]+?)(?:\s+subject|$)',  # "PPT on TOPIC"
                    r'topic[:\s]+([^\n]+?)(?:\s+subject|$)',  # "Topic: TOPIC"
                ]
                extracted_topic = None
                prompt_str = str(prompt) if prompt else ""
                for pattern in topic_patterns:
                    match = re.search(pattern, prompt_str, re.IGNORECASE)
                    if match:
                        extracted_topic = match.group(1).strip()
                        # Remove trailing punctuation
                        extracted_topic = re.sub(r'[.,;:]\s*$', '', extracted_topic)
                        if extracted_topic and len(extracted_topic) > 3:  # Valid topic
                            break
                
                # If extraction failed, use first filtered topic from list
                if not extracted_topic:
                    if filtered_topics:
                        extracted_topic = filtered_topics[0]
                    elif topics:
                        # Last resort: use first topic but warn
                        extracted_topic = topics[0]
                        if isinstance(extracted_topic, str) and extracted_topic.lower().startswith("subject"):
                            print(f"⚠️  Mode 5: Warning - topic extraction may have included subject line")
                    else:
                        extracted_topic = (ppt_cfg or {}).get("topic") or "General Topic"
                
                # Normalize: topic must be a STRING, not a list
                topic = str(extracted_topic).strip()
                if not topic or len(topic) < 3:
                    topic = "General Topic"
                
                print(f"ℹ️  Mode 5: normalized to single topic: '{topic}'")
                
                # Assertion: topic must be a string before generation
                assert isinstance(topic, str), f"MODE 5 ASSERTION FAILED: topic must be str, got {type(topic)}"
                
                # Clear topics list to prevent downstream confusion
                topics = [topic]  # Keep as list for compatibility, but only one item
            
            # MODE 5 GUARD: Never use generate_slides_for_topics for Mode 5 (it creates too many slides)
            if len(topics) > 1 and not is_mode_2_early_check and not is_mode_4_early_check and not is_mode_5_early_check:
                # Only use generate_slides_for_topics for multi-topic requests that are NOT Mode 2/4/5
                slide_data = content_generator.generate_slides_for_topics(
                    topics,
                    subject or "General",
                    total_slides=num_slides,
                    min_slides_per_topic=3,
                    model_type=effective_model_type,
                    user_input=prompt,
                )
            else:
                # For Mode 5, topic is already normalized above
                if not is_mode_5_early_check:
                    topic = topics[0] if topics else (ppt_cfg or {}).get("topic") or "General Topic"
                
                # MODE 5 GUARD: Never use custom_slides_raw or slide_structure_raw for Mode 5
                # Mode 5 uses mode-based parser which extracts slide instructions directly
                is_mode_5_check = "slide instructions:" in prompt_lower_mode_check
                
                # Convert custom slides and structure to dict format (ONLY if NOT Mode 5)
                custom_slides_dict = None
                if not is_mode_5_check and custom_slides_raw and isinstance(custom_slides_raw, list):
                    custom_slides_dict = []
                    for cs in custom_slides_raw:
                        if isinstance(cs, dict) and cs.get("slide_number"):
                            custom_slides_dict.append({
                                "slide_number": cs.get("slide_number"),
                                "title": cs.get("title", ""),
                                "content": cs.get("content", []) if isinstance(cs.get("content"), list) else [],
                                "image_url": cs.get("image_url"),
                                "speaker_notes": cs.get("speaker_notes")
                            })
                elif is_mode_5_check:
                    print(f"🔒 MODE 5 GUARD: Skipping custom_slides_raw (Mode 5 uses mode-based parser)")
                
                slide_structure_dict = None
                if not is_mode_5_check and slide_structure_raw and isinstance(slide_structure_raw, list):
                    slide_structure_dict = []
                    for ss in slide_structure_raw:
                        if isinstance(ss, dict) and ss.get("slide_number") and ss.get("title"):
                            slide_structure_dict.append({
                                "slide_number": ss.get("slide_number"),
                                "title": ss.get("title")
                            })
                    print(f"🔍 DEBUG: Passing {len(slide_structure_dict)} structure entries to PPT generator:")
                    for ss in slide_structure_dict:
                        print(f"  - Slide {ss.get('slide_number')}: '{ss.get('title')}'")
                elif is_mode_5_check:
                    print(f"🔒 MODE 5 GUARD: Skipping slide_structure_raw (Mode 5 uses mode-based parser)")
                
                # Also check if slide_structure mentions Architecture and we have image_requests for that slide
                # This handles cases like "slide 3 title Architecture" with an image URL
                if slide_structure_dict:
                    for ss in slide_structure_dict:
                        slide_num = ss.get("slide_number")
                        title_lower = (ss.get("title") or "").lower()
                        # If it's an architecture slide and we have an image URL for this slide
                        if "architect" in title_lower:
                            # Check if image_requests has a URL for this slide
                            for ir in image_requests:
                                if isinstance(ir, dict) and ir.get("slide_number") == slide_num and ir.get("url"):
                                    print(f"✓ Architecture slide {slide_num} will use provided image URL")
                                    break
                
                # CRITICAL: For Mode 2/4/5, DO NOT use any extracted structure - mode-based generation will extract titles
                # Check if this is Mode 2, 4, or 5 BEFORE using any extracted structure
                prompt_lower_check = str(prompt).lower() if prompt else ""
                is_mode_2_check = "slide titles:" in prompt_lower_check
                is_mode_4_check = "image placement:" in prompt_lower_check
                is_mode_5_check = "slide instructions:" in prompt_lower_check
                
                if is_mode_2_check or is_mode_4_check or is_mode_5_check:
                    mode_name = "Mode 2" if is_mode_2_check else ("Mode 4" if is_mode_4_check else "Mode 5")
                    print(f"🔍 DEBUG: {mode_name} detected - IGNORING all extracted structure (mode-based parser will extract titles)")
                    # Clear all extracted structure - Mode 2/4/5 parser will extract titles from prompt
                    slide_structure_dict = None
                    custom_slides_dict = None
                    final_structure = []
                    final_custom = []
                else:
                    # For other modes, use extracted structure
                    final_structure = slide_structure_dict or []
                    final_custom = custom_slides_dict or []
                    
                    # If we have structure or custom slides from extraction, use them for mode detection
                    # Otherwise, check if LLM router found any (ONLY for non-Mode 4)
                    if not final_structure and slide_structure_raw:
                        print(f"🔍 Using LLM-extracted structure for mode detection: {len(slide_structure_raw)} entries")
                        final_structure = slide_structure_dict or []
                    if not final_custom and custom_slides_raw:
                        print(f"🔍 Using LLM-extracted custom slides for mode detection: {len(custom_slides_raw)} entries")
                        final_custom = custom_slides_dict or []
                
                # CRITICAL: ALWAYS use mode-based generation when user_input is available
                # Get the FULL prompt - use the original prompt variable from the request
                prompt_full = str(prompt) if prompt else ""
                
                print(f"🚀 MODE-BASED GENERATION: Starting...")
                print(f"🔍 Prompt preview (first 500 chars): {prompt_full[:500]}")
                print(f"🔍 Prompt full length: {len(prompt_full)}")
                print(f"🔍 Prompt contains 'Image placement:': {'Image placement:' in prompt_full or 'image placement:' in prompt_full.lower()}")
                print(f"🔍 Prompt contains 'Slide structure:': {'Slide structure:' in prompt_full or 'slide structure:' in prompt_full.lower()}")
                
                # Show the actual prompt content to debug
                if "Slide structure:" in prompt_full or "slide structure:" in prompt_full.lower():
                    structure_idx = prompt_full.lower().find("slide structure:")
                    if structure_idx >= 0:
                        print(f"🔍 Found 'Slide structure:' at index {structure_idx}")
                        print(f"🔍 Text around 'Slide structure:': {prompt_full[max(0, structure_idx-50):structure_idx+300]}")
                
                # STEP 1: TRACE DATA FLOW - API request handler boundary
                user_input_str = prompt_full if prompt_full and len(prompt_full.strip()) > 0 else None
                print(f"🔍 API HANDLER | user_input_str type={type(user_input_str)}, len={len(user_input_str) if user_input_str else 0}, preview={repr(user_input_str)[:300] if user_input_str else 'None/Empty'}")
                print(f"🔍 API HANDLER | prompt_full type={type(prompt_full)}, len={len(prompt_full) if prompt_full else 0}, preview={repr(prompt_full)[:300] if prompt_full else 'None/Empty'}")
                
                # STEP 2: HARD FAIL RULE - Mode 2 requires user_input
                if is_mode_2_check:
                    if not user_input_str or len(str(user_input_str).strip()) == 0:
                        error_msg = "Mode 2 requires user_input but received None/empty. Cannot generate PPT without user-provided titles."
                        print(f"❌ HARD FAIL: {error_msg}")
                        raise ValueError(error_msg)
                    print(f"✅ API HANDLER: Mode 2 detected, user_input validated (len={len(user_input_str)})")
                    print(f"🔍 API HANDLER: user_input_str contains 'Slide titles:': {'Slide titles:' in str(user_input_str)}")
                
                if not user_input_str:
                    print(f"❌ CRITICAL ERROR: user_input is empty or None! Cannot detect mode.")
                    print(f"   prompt type: {type(prompt)}, prompt value: {repr(prompt)[:200]}")
                    raise ValueError("Prompt is empty or None - cannot generate PPT")
                
                # STEP 1: TRACE DATA FLOW - Router boundary (before generator call)
                print(f"🔍 ROUTER | About to call generate_slide_content with user_input parameter")
                print(f"🔍 ROUTER | user_input parameter: type={type(user_input_str)}, len={len(user_input_str)}, preview={repr(user_input_str)[:200]}")
                print(f"🔍 ROUTER | Checking user_input_str is not None/empty: {user_input_str is not None and len(str(user_input_str).strip()) > 0}")
                
                # MODE 5 ASSERTION: topic must be a string before generation
                is_mode_5_router_check = "slide instructions:" in str(prompt_full).lower() if prompt_full else False
                if is_mode_5_router_check:
                    assert isinstance(topic, str), f"MODE 5 ASSERTION FAILED before generation: topic must be str, got {type(topic)}: {topic}"
                    print(f"✅ MODE 5: topic verified as string before generation: '{topic}'")
                
                # CRITICAL: Call mode-based generation - this MUST run
                try:
                    print(f"🔍 ROUTER | CALLING generate_slide_content NOW with user_input={repr(user_input_str)[:100]}...")
                    slide_data = content_generator.generate_slide_content(
                        topic=topic,
                        content=content,
                        num_slides=num_slides,
                        subject=subject or "General",
                        module=module,
                        model_type=effective_model_type,
                        user_input=user_input_str  # Pass the FULL string - SAME parameter name
                    )
                    print(f"🔍 ROUTER | generate_slide_content RETURNED, slide_data type: {type(slide_data)}")
                    print(f"🔍 ROUTER | generate_slide_content returned, slide_data type: {type(slide_data)}, slides count: {len(slide_data.get('slides', []))}")
                    print(f"✅ MODE-BASED GENERATION COMPLETE: Generated {len(slide_data.get('slides', []))} slides")
                    generated_titles = [s.get('title') for s in slide_data.get('slides', [])]
                    print(f"🔍 Slide titles from generator: {generated_titles}")
                    
                    # CRITICAL: For Mode 2, verify IMMEDIATELY that titles are correct
                    if is_mode_2_check:
                        generated_slides = slide_data.get('slides', [])
                        expected_count = num_slides + 1
                        if len(generated_slides) != expected_count:
                            raise ValueError(f"Mode 2 generation failed! Expected {expected_count} slides (1 base + {num_slides} user), but got {len(generated_slides)}. This should never happen.")
                        print(f"✅ Mode 2 slide count verified immediately after generation: {len(generated_slides)} slides")
                        
                        # CRITICAL: Verify titles match user-provided titles EXACTLY
                        prompt_str = str(prompt) if prompt else ""
                        import re
                        title_pattern = r"Slide\s+(\d+)\s*:\s*(.+)"
                        user_titles = {}
                        for match in re.finditer(title_pattern, prompt_str, re.IGNORECASE):
                            slide_num = int(match.group(1))
                            title = match.group(2).strip().rstrip()
                            user_titles[slide_num] = title
                        
                        print(f"🔍 User-provided titles from prompt: {user_titles}")
                        
                        # Verify each user slide has the correct title
                        for slide in generated_slides:
                            slide_num = slide.get("slide_number", 0)
                            if slide_num > 1:  # Skip base slide
                                user_slide_num = slide_num - 1  # Convert to user's slide number
                                expected_title = user_titles.get(user_slide_num)
                                actual_title = slide.get("title")
                                if expected_title:
                                    if actual_title != expected_title:
                                        print(f"❌ CRITICAL: Mode 2 title mismatch detected!")
                                        print(f"   Slide {slide_num} (user's slide {user_slide_num})")
                                        print(f"   Expected: '{expected_title}'")
                                        print(f"   Actual: '{actual_title}'")
                                        raise ValueError(f"Mode 2 title mismatch! Slide {slide_num} (user's slide {user_slide_num}) has title '{actual_title}' but expected '{expected_title}'. User titles are LAW!")
                                    else:
                                        print(f"  ✅ Mode 2: Slide {slide_num} title matches: '{actual_title}'")
                except Exception as e:
                    print(f"❌ CRITICAL ERROR in generate_slide_content: {str(e)}")
                    print(f"   Exception type: {type(e).__name__}")
                    import traceback
                    print(f"   Traceback: {traceback.format_exc()}")
                    raise  # Re-raise to see the full error - DO NOT fall back to old generation

            # Check if this is Mode 2 or Mode 4 - skip auto images for these modes
            is_mode_2 = False
            is_mode_4 = False
            if prompt:
                prompt_lower = str(prompt).lower()
                is_mode_2 = "slide titles:" in prompt_lower
                is_mode_4 = "image placement:" in prompt_lower
            
            # MODE 4 IMAGE LOCK: Map uploaded images to slides based on image_number
            # This is the ONLY place where Mode 4 images should be attached
            if is_mode_4 and uploaded_image_paths and isinstance(uploaded_image_paths, list):
                print(f"🔒 MODE 4 IMAGE LOCK: Mapping {len(uploaded_image_paths)} uploaded images to slides based on image_number")
                slides = slide_data.get("slides", [])
                
                # Extract image mappings from prompt: "Use Image X on Slide Y"
                import re
                image_mapping_pattern = r'Use\s+Image\s+(\d+)\s+on\s+Slide\s+(\d+)'
                prompt_lower = str(prompt).lower()
                image_mappings = list(re.finditer(image_mapping_pattern, prompt_lower, re.IGNORECASE))
                
                # MODE 4 IMAGE LOCK: Create whitelist of allowed slides
                allowed_image_slides = set()
                user_image_mappings = {}  # Track: image_num -> user_slide_num
                for mapping in image_mappings:
                    image_num = int(mapping.group(1))
                    user_slide_num = int(mapping.group(2))
                    actual_slide_num = user_slide_num + 1  # Shift by +1 for base slide
                    allowed_image_slides.add(actual_slide_num)
                    user_image_mappings[image_num] = user_slide_num
                
                print(f"🔒 MODE 4 IMAGE LOCK: Allowed slides for images: {allowed_image_slides}")
                print(f"🔒 MODE 4 IMAGE LOCK: User image mappings: {user_image_mappings}")
                
                # MODE 4 IMAGE LOCK: Track used images to prevent reuse
                used_image_paths = set()
                
                print(f"🔍 DEBUG: Found {len(image_mappings)} image mappings in prompt")
                for mapping in image_mappings:
                    image_num = int(mapping.group(1))
                    user_slide_num = int(mapping.group(2))
                    actual_slide_num = user_slide_num + 1  # Shift by +1 for base slide
                    
                    print(f"🔍 DEBUG: Looking for slide {actual_slide_num} with image_number {image_num}")
                    
                    # Find the slide with this slide_number and image_number
                    found = False
                    for slide in slides:
                        slide_num = slide.get("slide_number")
                        slide_img_num = slide.get("image_number")
                        
                        # Match by slide number AND image number
                        if slide_num == actual_slide_num and slide_img_num == image_num:
                            # MODE 4 IMAGE LOCK: Assert slide is in whitelist
                            if actual_slide_num not in allowed_image_slides:
                                print(f"🔒 MODE 4 IMAGE LOCK: Blocked image attachment to slide {actual_slide_num} (not user-specified)")
                                continue
                            
                            # Map uploaded image (image_num - 1 because images are 0-indexed in list)
                            if image_num <= len(uploaded_image_paths):
                                img_path = uploaded_image_paths[image_num - 1]
                                
                                # MODE 4 IMAGE LOCK: Ensure image is used only once
                                if img_path in used_image_paths:
                                    print(f"🔒 MODE 4 IMAGE LOCK: Image {image_num} already used, skipping duplicate attachment to slide {actual_slide_num}")
                                    continue
                                
                                used_image_paths.add(img_path)
                                
                                slide["image_path"] = img_path
                                print(f"✓ Mode 4: Mapped Image {image_num} (uploaded) to slide {actual_slide_num} (user's slide {user_slide_num}): {img_path}")
                                found = True
                                break
                    
                    if not found:
                        print(f"⚠ WARNING: Could not find slide {actual_slide_num} (user's slide {user_slide_num}) with image_number {image_num}")
                        print(f"   Available slides: {[(s.get('slide_number'), s.get('image_number'), s.get('title')) for s in slides]}")
                
                # MODE 4 IMAGE LOCK: Remove any images from slides that don't have image_number set (no auto images for Mode 4)
                # Also remove images from slides not in whitelist
                for slide in slides:
                    if slide.get("slide_number", 0) > 1:  # Skip base slide
                        slide_num = slide.get("slide_number")
                        # Remove images from slides not in whitelist
                        if slide_num not in allowed_image_slides and slide.get("image_path"):
                            print(f"🔒 MODE 4 IMAGE LOCK: Blocked image attachment to slide {slide_num} (not user-specified)")
                            del slide["image_path"]
                            if "image_query" in slide:
                                del slide["image_query"]
                        # Remove images from slides without image_number (auto-added)
                        elif "image_number" not in slide and "image_path" in slide:
                            print(f"🔒 MODE 4 IMAGE LOCK: Removing auto image from slide {slide.get('slide_number')} (Mode 4: no auto images)")
                            del slide["image_path"]
                            if "image_query" in slide:
                                del slide["image_query"]
                
                # MODE 4 IMAGE LOCK: Hard assertion - verify image count matches user mappings
                slides_with_images = [s for s in slides if s.get("image_path") and s.get("slide_number", 0) > 1]
                expected_image_count = len(user_image_mappings)
                actual_image_count = len(slides_with_images)
                if actual_image_count != expected_image_count:
                    error_msg = f"MODE 4 IMAGE LOCK violation! Expected {expected_image_count} images (from user mappings) but found {actual_image_count} images attached. This is FORBIDDEN."
                    print(f"❌ {error_msg}")
                    print(f"   User mappings: {user_image_mappings}")
                    print(f"   Slides with images: {[(s.get('slide_number'), s.get('image_number'), s.get('image_path')) for s in slides_with_images]}")
                    raise ValueError(error_msg)
                print(f"✅ MODE 4 IMAGE LOCK: Verified {actual_image_count} images attached (matches {expected_image_count} user mappings)")
            
            # CRITICAL: Enforce slide count FIRST (before any image logic that might corrupt slides)
            # This prevents slide expansion/regeneration from corrupting Mode 2/4 titles
            final_slides = slide_data.get("slides", [])
            expected_total = num_slides + 1  # 1 base slide (slide 1) + num_slides user slides (slides 2 to num_slides+1)
            
            if len(final_slides) != expected_total:
                print(f"⚠ CRITICAL: Slide count is {len(final_slides)}, expected {expected_total} (1 base + {num_slides} user)")
                # Separate base slide (slide 1) from user slides (slides 2 to num_slides+1)
                base_slides = [s for s in final_slides if isinstance(s, dict) and s.get("slide_number", 0) == 1]
                user_slides = [s for s in final_slides if isinstance(s, dict) and s.get("slide_number", 0) > 1]
                
                # Ensure we have exactly num_slides user slides (slides 2 through num_slides+1)
                user_slides = [s for s in user_slides if s.get("slide_number", 0) <= num_slides + 1]
                user_slides.sort(key=lambda s: s.get("slide_number", 0))
                
                # Trim to exactly num_slides user slides
                if len(user_slides) > num_slides:
                    print(f"⚠ Trimming {len(user_slides)} user slides to {num_slides}")
                    user_slides = user_slides[:num_slides]
                
                # Rebuild slide_data with correct slides
                slide_data["slides"] = base_slides + user_slides
                print(f"✓ Enforced exactly {len(slide_data['slides'])} slides (1 base slide 1 + {len(user_slides)} user slides 2-{len(user_slides)+1})")
            
            # CRITICAL: Lock titles for Mode 2/4 BEFORE any image logic
            # TITLE-PURE: For Mode 2, verify titles match user-provided titles BEFORE locking
            if is_mode_2 or is_mode_4:
                slides = slide_data.get("slides", [])
                
                # TITLE-PURE: For Mode 2, extract user titles from prompt and verify
                if is_mode_2:
                    import re
                    prompt_str = str(prompt) if prompt else ""
                    title_pattern = r"Slide\s+(\d+)\s*:\s*(.+)"
                    user_titles_api = {}
                    for match in re.finditer(title_pattern, prompt_str, re.IGNORECASE):
                        slide_num = int(match.group(1))
                        title = match.group(2).strip().rstrip()
                        user_titles_api[slide_num] = title
                    
                    print(f"🔍 API: Mode 2 TITLE-PURE verification - user titles: {user_titles_api}")
                
                for slide in slides:
                    if slide.get("slide_number", 0) > 1:  # Skip base slide
                        slide_num = slide.get("slide_number")
                        original_title = slide.get("title")
                        
                        # TITLE-PURE: For Mode 2, verify title matches user-provided title BEFORE locking
                        if is_mode_2 and original_title:
                            user_slide_num = slide_num - 1  # Convert to user's slide number
                            expected_title = user_titles_api.get(user_slide_num)
                            if expected_title and original_title != expected_title:
                                error_msg = f"Mode 2 TITLE-PURE violation in API! Slide {slide_num} (user's slide {user_slide_num}) has title '{original_title}' but expected '{expected_title}'. Titles must NEVER be modified."
                                print(f"❌ {error_msg}")
                                raise ValueError(error_msg)
                            print(f"  ✅ API: Mode 2 slide {slide_num} title verified: '{original_title}' == '{expected_title}'")
                        
                        if original_title:
                            slide["title_locked"] = True
                            slide["original_title"] = original_title
                            print(f"  🔒 Locked title for slide {slide.get('slide_number')}: '{original_title}'")
            
            # MODE 4 IMAGE LOCK: Skip _apply_image_requests entirely for Mode 4
            # Mode 4 generator already handles image mapping correctly via image_number
            # The API layer mapping (lines 1685-1732) also handles it
            # Calling _apply_image_requests would cause duplicate/incorrect mappings
            if image_requests and isinstance(image_requests, list) and len(image_requests) > 0:
                if is_mode_4:
                    print(f"🔒 MODE 4 IMAGE LOCK: Skipping _apply_image_requests (generator already mapped images via image_number)")
                    print(f"🔒 MODE 4 IMAGE LOCK: Images are handled by generator and API layer mapping only")
                    # Extract allowed slides from "Image placement:" for verification
                    import re
                    prompt_str = str(prompt) if prompt else ""
                    image_mapping_pattern = r'Use\s+Image\s+\d+\s+on\s+Slide\s+(\d+)'
                    allowed_slides = set()
                    for match in re.finditer(image_mapping_pattern, prompt_str, re.IGNORECASE):
                        user_slide_num = int(match.group(1))
                        actual_slide_num = user_slide_num + 1  # Shift for base slide
                        allowed_slides.add(actual_slide_num)
                    print(f"🔒 MODE 4 IMAGE LOCK: Allowed slides for images: {allowed_slides}")
                    
                    # Verify no images are on disallowed slides
                    slides = slide_data.get("slides", [])
                    for slide in slides:
                        slide_num = slide.get("slide_number", 0)
                        if slide_num > 1 and slide.get("image_path") and slide_num not in allowed_slides:
                            print(f"🔒 MODE 4 IMAGE LOCK: Blocked image attachment to slide {slide_num} (not user-specified)")
                            del slide["image_path"]
                            if "image_query" in slide:
                                del slide["image_query"]
                else:
                    print(f"🔍 DEBUG: Applying {len(image_requests)} user-specified image requests")
                    slide_data = _apply_image_requests(slide_data, image_requests)
            
            # CRITICAL: Fetch additional images ONLY if NOT Mode 2 or Mode 4
            # Mode 2: No auto images (per spec)
            # Mode 4: Only user-specified images (per spec)
            if not is_mode_2 and not is_mode_4:
                max_images = max(num_slides, len(image_requests) if isinstance(image_requests, list) else 0)
                print(f"🔍 DEBUG: Fetching additional images (max={max_images})")
                slide_data = _attach_images(slide_data, max_images=max_images)
            else:
                mode_name = "Mode 2" if is_mode_2 else "Mode 4"
                print(f"🔍 DEBUG: {mode_name} detected - Auto image fetching DISABLED (user titles/content are LAW)")
            
            # MODE 4 IMAGE LOCK: Final cleanup pass - ensure no images on disallowed slides
            if is_mode_4:
                import re
                prompt_str = str(prompt) if prompt else ""
                image_mapping_pattern = r'Use\s+Image\s+\d+\s+on\s+Slide\s+(\d+)'
                allowed_slides_final = set()
                for match in re.finditer(image_mapping_pattern, prompt_str, re.IGNORECASE):
                    user_slide_num = int(match.group(1))
                    actual_slide_num = user_slide_num + 1  # Shift for base slide
                    allowed_slides_final.add(actual_slide_num)
                
                print(f"🔒 MODE 4 IMAGE LOCK: Final cleanup - allowed slides: {allowed_slides_final}")
                slides_final = slide_data.get("slides", [])
                removed_count = 0
                for slide in slides_final:
                    slide_num = slide.get("slide_number", 0)
                    if slide_num > 1 and slide.get("image_path") and slide_num not in allowed_slides_final:
                        print(f"🔒 MODE 4 IMAGE LOCK: Final cleanup - blocked image on slide {slide_num} (not user-specified)")
                        del slide["image_path"]
                        removed_count += 1
                        if "image_query" in slide:
                            del slide["image_query"]
                
                if removed_count > 0:
                    print(f"🔒 MODE 4 IMAGE LOCK: Final cleanup - removed {removed_count} images from disallowed slides")
                
                # Final assertion: verify image count
                slides_with_images_final = [s for s in slides_final if s.get("image_path") and s.get("slide_number", 0) > 1]
                expected_count = len(allowed_slides_final)
                actual_count = len(slides_with_images_final)
                if actual_count != expected_count:
                    error_msg = f"MODE 4 IMAGE LOCK final violation! Expected {expected_count} images but found {actual_count}. Images: {[(s.get('slide_number'), s.get('image_path')) for s in slides_with_images_final]}"
                    print(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                print(f"✅ MODE 4 IMAGE LOCK: Final verification passed - {actual_count} images on allowed slides only")
            
            # CRITICAL: Final validation - ensure titles are still correct for Mode 2/4
            if is_mode_2 or is_mode_4:
                slides = slide_data.get("slides", [])
                for slide in slides:
                    if slide.get("title_locked"):
                        original_title = slide.get("original_title")
                        current_title = slide.get("title")
                        if current_title != original_title:
                            raise ValueError(f"Mode 2/4 title corruption detected! Slide {slide.get('slide_number')} title changed from '{original_title}' to '{current_title}'. This should never happen.")
                        print(f"  ✅ Verified locked title for slide {slide.get('slide_number')}: '{current_title}'")
            
            # CRITICAL: Final slide count assertion (should already be enforced above, but double-check)
            final_slides = slide_data.get("slides", [])
            expected_total = num_slides + 1  # 1 base slide (slide 1) + num_slides user slides (slides 2 to num_slides+1)
            
            # CRITICAL ASSERTION: For Mode 2/4, slide count MUST be exact
            if is_mode_2 or is_mode_4:
                if len(final_slides) != expected_total:
                    raise ValueError(f"Mode 2/4 slide count violation! Expected {expected_total} slides (1 base + {num_slides} user), but got {len(final_slides)}. This should never happen.")
                print(f"✅ Mode 2/4 slide count verified: {len(final_slides)} slides (exactly {expected_total} expected)")
                
                # CRITICAL: Final title assertion for Mode 2
                if is_mode_2:
                    # Extract user titles from prompt for verification
                    prompt_str = str(prompt) if prompt else ""
                    import re
                    title_pattern = r"Slide\s+(\d+)\s*:\s*(.+)"
                    user_titles = {}
                    for match in re.finditer(title_pattern, prompt_str, re.IGNORECASE):
                        slide_num = int(match.group(1))
                        title = match.group(2).strip().rstrip()
                        user_titles[slide_num] = title
                    
                    # Verify each user slide has the correct title
                    for slide in final_slides:
                        slide_num = slide.get("slide_number", 0)
                        if slide_num > 1:  # Skip base slide
                            user_slide_num = slide_num - 1  # Convert to user's slide number
                            expected_title = user_titles.get(user_slide_num)
                            actual_title = slide.get("title")
                            if expected_title and actual_title != expected_title:
                                raise ValueError(f"Mode 2 title mismatch! Slide {slide_num} (user's slide {user_slide_num}) has title '{actual_title}' but expected '{expected_title}'. User titles are LAW!")
                            print(f"  ✅ Mode 2: Slide {slide_num} title verified: '{actual_title}'")
            
            if len(final_slides) != expected_total:
                print(f"⚠ CRITICAL: Final slide count is {len(final_slides)}, expected {expected_total} (1 base + {num_slides} user)")
                # Separate base slide (slide 1) from user slides (slides 2 to num_slides+1)
                base_slides = [s for s in final_slides if isinstance(s, dict) and s.get("slide_number", 0) == 1]
                user_slides = [s for s in final_slides if isinstance(s, dict) and s.get("slide_number", 0) > 1]
                
                # Ensure we have exactly num_slides user slides (slides 2 through num_slides+1)
                user_slides = [s for s in user_slides if s.get("slide_number", 0) <= num_slides + 1]
                existing_user_numbers = {s.get("slide_number") for s in user_slides}
                
                # Add any missing user slides (user's slide i → actual slide i+1)
                for i in range(1, num_slides + 1):
                    actual_slide_num = i + 1
                    if actual_slide_num not in existing_user_numbers:
                        print(f"⚠ Creating missing slide {actual_slide_num} (user's slide {i})")
                        user_slides.append({
                            "slide_number": actual_slide_num,
                            "slide_type": "content",
                            "title": f"Slide {actual_slide_num}",
                            "content": ["Content to be added"],
                            "speaker_notes": ""
                        })
                
                # Ensure base slide exists
                if not base_slides:
                    base_slides = [{
                        "slide_number": 1,
                        "slide_type": "title",
                        "title": topic,
                        "content": [subject or "Educational Presentation"] if subject else ["Generated by EduAssist"],
                        "speaker_notes": f"Introduction to the presentation on {topic}."
                    }]
                
                # Sort and combine
                user_slides.sort(key=lambda s: s.get("slide_number", 0))
                user_slides = user_slides[:num_slides]  # Take exactly num_slides user slides
                final_slides = base_slides + user_slides
                slide_data["slides"] = final_slides
                print(f"✓ Enforced exactly {len(final_slides)} slides (1 base slide 1 + {len(user_slides)} user slides 2-{num_slides+1})")
                print(f"🔍 DEBUG: Final slide numbers: {[s.get('slide_number') for s in final_slides]}")

            storage_dir = Path("storage/presentations")
            creator = PPTCreator(str(storage_dir))
            file_path = creator.create_presentation(slide_data)
            filename = os.path.basename(file_path)
            link = f"/api/download-ppt/{filename}"
            return AssistResponse(
                success=True,
                type="ppt",
                message=f"PPT generated for: {', '.join(topics) if topics else topic}",
                link=link,
                filename=filename,
                raw=raw
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PPT generation failed: {e}")

    # Question paper intent
    if intent == "question_paper":
        if content_analyzer is None or question_generator is None:
            raise HTTPException(
                status_code=503,
                detail="Question Paper Generator requires GEMINI_API_KEY. Please set it in backend/.env file."
            )
        if not isinstance(qp_cfg, dict):
            qp_cfg = {}
        qp_content = qp_cfg.get("content") or req.prompt
        requirements = {
            "num_mcq": _safe_int(qp_cfg.get("num_mcq"), 5),
            "num_short": _safe_int(qp_cfg.get("num_short"), 3),
            "num_long": _safe_int(qp_cfg.get("num_long"), 2),
            "marks_mcq": _safe_int(qp_cfg.get("marks_mcq"), 1),
            "marks_short": _safe_int(qp_cfg.get("marks_short"), 3),
            "marks_long": _safe_int(qp_cfg.get("marks_long"), 5),
            "difficulty": qp_cfg.get("difficulty") or "medium",
        }
        try:
            analysis = content_analyzer.analyze_content(qp_content, "text")
            questions = question_generator.generate_questions(analysis, requirements)
            total_marks = (
                len(questions.get("mcq_questions", [])) * requirements["marks_mcq"]
                + len(questions.get("short_answer_questions", [])) * requirements["marks_short"]
                + len(questions.get("long_answer_questions", [])) * requirements["marks_long"]
            )
            return AssistResponse(
                success=True,
                type="question_paper",
                message="Question paper generated",
                questions=questions,
                summary={
                    "total_marks": total_marks,
                    "total_mcqs": len(questions.get("mcq_questions", [])),
                    "total_short": len(questions.get("short_answer_questions", [])),
                    "total_long": len(questions.get("long_answer_questions", [])),
                },
                raw=raw
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Question paper generation failed: {e}")

    # General intent: behave like a helpful teacher assistant (chatbot)
    gen_prompt = f"""
You are EduAssist, a concise, helpful teaching assistant for educators.
Provide clear, actionable answers in under 180 words.
Use bullets when helpful. Include plain-text formulas if asked.
Do NOT mention being an AI. Focus on teacher-ready guidance.

User request:
{req.prompt}
"""
    try:
        answer = model_manager.generate_content(gen_prompt, model_type)
    except Exception:
        answer = raw.get("answer") if isinstance(raw, dict) else ""
    if not answer:
        answer = "Let me know if you want a PPT or a question paper, and include the topic/subject."
    return AssistResponse(
        success=True,
        type="general",
        message=answer,
        raw=raw
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
    if content_analyzer is None or question_generator is None:
        raise HTTPException(
            status_code=503,
            detail="Question Generator requires GEMINI_API_KEY. Please set it in backend/.env file. PPT Generator works with Groq."
        )
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
    if content_analyzer is None or question_generator is None:
        raise HTTPException(
            status_code=503,
            detail="Question Paper Generator requires GEMINI_API_KEY. Please set it in backend/.env file. PPT Generator works with Groq."
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