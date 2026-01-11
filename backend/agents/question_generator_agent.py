import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini (optional - can use Groq via ModelManager)
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)
else:
    print("⚠ GEMINI_API_KEY not set - QuestionGenerator will need Groq API key")

class QuestionGenerator:
    """Question Generator Agent that creates various types of questions"""
    
    def __init__(self):
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY not set. Please set it in backend/.env file or use Groq for PPT generation.")
        self.model = genai.GenerativeModel('gemini-pro-latest')
    
    def generate_questions(self, content_analysis: dict, requirements: dict) -> dict:
        """Generate questions based on content analysis and requirements"""
        try:
            prompt = f"""
            Based on the following content analysis, generate questions according to the requirements.
            
            Content Analysis:
            - Key Concepts: {content_analysis.get('key_concepts', [])}
            - Difficulty Level: {content_analysis.get('difficulty_level', 'medium')}
            - Subject Areas: {content_analysis.get('subject_areas', [])}
            - Important Points: {content_analysis.get('important_points', [])}
            - Question-worthy Content: {content_analysis.get('question_worthy_content', [])}
            
            Requirements:
            - Number of MCQs: {requirements.get('num_mcq', 5)}
            - Number of Short Answer Questions: {requirements.get('num_short', 3)}
            - Number of Long Answer Questions: {requirements.get('num_long', 2)}
            - Marks per MCQ: {requirements.get('marks_mcq', 1)}
            - Marks per Short Answer: {requirements.get('marks_short', 3)}
            - Marks per Long Answer: {requirements.get('marks_long', 5)}
            - Difficulty: {requirements.get('difficulty', 'medium')}
            
            Please generate questions in JSON format with this structure:
            {{
                "mcq_questions": [
                    {{
                        "question": "question text",
                        "options": ["option1", "option2", "option3", "option4"],
                        "correct_answer": "correct option",
                        "marks": 1,
                        "difficulty": "easy/medium/hard"
                    }}
                ],
                "short_answer_questions": [
                    {{
                        "question": "question text",
                        "correct_answer": "brief answer",
                        "marks": 3,
                        "difficulty": "easy/medium/hard"
                    }}
                ],
                "long_answer_questions": [
                    {{
                        "question": "question text",
                        "correct_answer": "detailed answer",
                        "marks": 5,
                        "difficulty": "easy/medium/hard"
                    }}
                ]
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
                # If JSON parsing fails, return empty structure
                return {
                    "mcq_questions": [],
                    "short_answer_questions": [],
                    "long_answer_questions": []
                }
                
        except Exception as e:
            print(f"Error in question generation: {e}")
            return {
                "mcq_questions": [],
                "short_answer_questions": [],
                "long_answer_questions": [],
                "error": str(e)
            }
