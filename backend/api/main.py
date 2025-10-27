from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional

# Import agents
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from agents.content_analyzer_agent import ContentAnalyzer
from agents.question_generator_agent import QuestionGenerator

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