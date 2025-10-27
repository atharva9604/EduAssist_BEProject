import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class ContentAnalyzer:
    """Simple content analyzer using Gemini AI"""
    
    def __init__(self):
        # Use gemini-pro-latest (it's working!)
        self.model = genai.GenerativeModel('gemini-pro-latest')
    
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
            
            response = self.model.generate_content(prompt)
            result_text = response.text
            
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