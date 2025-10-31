from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
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
    allow_origins=["http://localhost:3000"],  # Next.js default port
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