from crewai import Agent, Task, Crew
from crewai_tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import PyPDF2
import python_pptx
from docx import Document
import os
from dotenv import load_dotenv

load_dotenv()

class DocumentProcessorTool(BaseTool):
    name: str = "Document Processor Tool"
    description: str = "Extracts text content from various document formats (PDF, PPT, DOCX)"
    
    def _run(self, file_path: str, file_type: str) -> str:
        """Extract text from document based on file type"""
        try:
            if file_type.lower() == 'pdf':
                return self._extract_from_pdf(file_path)
            elif file_type.lower() in ['ppt', 'pptx']:
                return self._extract_from_ppt(file_path)
            elif file_type.lower() in ['doc', 'docx']:
                return self._extract_from_docx(file_path)
            else:
                return f"Unsupported file type: {file_type}"
        except Exception as e:
            return f"Error processing document: {str(e)}"
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def _extract_from_ppt(self, file_path: str) -> str:
        """Extract text from PowerPoint file"""
        text = ""
        prs = python_pptx.Presentation(file_path)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

# Create the Document Processor Agent
from crewai import LLM 

document_processor_agent = Agent(
    role="Document Processor",
    goal="Extract and clean text content from uploaded documents (PDFs, PPTs, DOCX files)",
    backstory="""You are an expert document processor with years of experience in 
    extracting text from various document formats. You ensure that the extracted 
    content is clean, readable, and properly formatted for further processing.""",
    tools=[DocumentProcessorTool()],
    llm=LLM(model="gemini-pro", api_key=os.getenv("GEMINI_API_KEY")),
    verbose=True,
    allow_delegation=False
)

# Create the Document Processing Task
def create_document_processing_task(file_path: str, file_type: str) -> Task:
    return Task(
        description=f"""
        Process the uploaded document at {file_path} of type {file_type}.
        
        Your tasks:
        1. Extract all text content from the document
        2. Clean and format the text for readability
        3. Remove any formatting artifacts or unnecessary characters
        4. Ensure the text is properly structured
        
        Return the cleaned text content.
        """,
        expected_output="Clean, formatted text content extracted from the document",
        agent=document_processor_agent
    )