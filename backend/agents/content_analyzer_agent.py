import os
import json
from dotenv import load_dotenv

load_dotenv()

from google import genai

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")

class ContentAnalyzer:
    """Simple content analyzer using Gemini AI"""
    
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        # IMPORTANT: gemini-pro-latest can map to gemini-2.5-pro (free tier quota may be 0).
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    def analyze_content(self, content: str, document_type: str = "text") -> dict:
        """Analyze content and extract key information"""
        try:
            prompt = f"""
            Analyze the following {document_type} content and provide a structured analysis.
            
            Content:
            {content[:3000]}
            
            Please provide a JSON response with the following structure:
            {{
                "key_concepts": ["concept1", "concept2", ...],
                "difficulty_level": "easy/medium/hard",
                "subject_areas": ["area1", "area2", ...],
                "important_points": ["point1", "point2", ...],
                "question_worthy_content": ["content1", "content2", ...]
            }}
            
            Return ONLY valid JSON.
            """
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            result_text = getattr(response, "text", "") or ""
            
            # Try to extract JSON from the response
            try:
                # Remove markdown code blocks if present
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                return json.loads(result_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, return a structured response
                return {
                    "key_concepts": [],
                    "difficulty_level": "medium",
                    "subject_areas": [],
                    "important_points": [],
                    "question_worthy_content": [result_text]
                }
                
        except Exception as e:
            print(f"Error in content analysis: {e}")
            return {
                "key_concepts": [],
                "difficulty_level": "medium",
                "subject_areas": [],
                "important_points": [],
                "question_worthy_content": [],
                "error": str(e)
            }