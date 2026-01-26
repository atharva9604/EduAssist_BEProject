# import os
# import json
# from dotenv import load_dotenv

# load_dotenv()

# from google import genai

# API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
# if not API_KEY:
#     raise RuntimeError("GEMINI_API_KEY not set")

# class QuestionGenerator:
#     """Question Generator Agent that creates various types of questions"""
    
#     def __init__(self):
#         self.client = genai.Client(api_key=API_KEY)
#         # IMPORTANT: gemini-pro-latest can map to gemini-2.5-pro (free tier quota may be 0).
#         self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
#     def generate_questions(self, content_analysis: dict, requirements: dict) -> dict:
#         """Generate questions based on content analysis and requirements"""
#         try:
#             prompt = f"""
#             Based on the following content analysis, generate questions according to the requirements.
            
#             Content Analysis:
#             - Key Concepts: {content_analysis.get('key_concepts', [])}
#             - Difficulty Level: {content_analysis.get('difficulty_level', 'medium')}
#             - Subject Areas: {content_analysis.get('subject_areas', [])}
#             - Important Points: {content_analysis.get('important_points', [])}
#             - Question-worthy Content: {content_analysis.get('question_worthy_content', [])}
            
#             Requirements:
#             - Number of MCQs: {requirements.get('num_mcq', 5)}
#             - Number of Short Answer Questions: {requirements.get('num_short', 3)}
#             - Number of Long Answer Questions: {requirements.get('num_long', 2)}
#             - Marks per MCQ: {requirements.get('marks_mcq', 1)}
#             - Marks per Short Answer: {requirements.get('marks_short', 3)}
#             - Marks per Long Answer: {requirements.get('marks_long', 5)}
#             - Difficulty: {requirements.get('difficulty', 'medium')}
            
#             Please generate questions in JSON format with this structure:
#             {{
#                 "mcq_questions": [
#                     {{
#                         "question": "question text",
#                         "options": ["option1", "option2", "option3", "option4"],
#                         "correct_answer": "correct option",
#                         "marks": 1,
#                         "difficulty": "easy/medium/hard"
#                     }}
#                 ],
#                 "short_answer_questions": [
#                     {{
#                         "question": "question text",
#                         "correct_answer": "brief answer",
#                         "marks": 3,
#                         "difficulty": "easy/medium/hard"
#                     }}
#                 ],
#                 "long_answer_questions": [
#                     {{
#                         "question": "question text",
#                         "correct_answer": "detailed answer",
#                         "marks": 5,
#                         "difficulty": "easy/medium/hard"
#                     }}
#                 ]
#             }}
            
#             Return ONLY valid JSON.
#             """
            
#             response = self.client.models.generate_content(
#                 model=self.model_name,
#                 contents=prompt,
#             )
#             result_text = getattr(response, "text", "") or ""
            
#             # Try to extract JSON from the response
#             try:
#                 # Remove markdown code blocks if present
#                 if "```json" in result_text:
#                     result_text = result_text.split("```json")[1].split("```")[0].strip()
#                 elif "```" in result_text:
#                     result_text = result_text.split("```")[1].split("```")[0].strip()
                
#                 return json.loads(result_text)
#             except json.JSONDecodeError:
#                 # If JSON parsing fails, return empty structure
#                 return {
#                     "mcq_questions": [],
#                     "short_answer_questions": [],
#                     "long_answer_questions": []
#                 }
                
#         except Exception as e:
#             print(f"Error in question generation: {e}")
#             return {
#                 "mcq_questions": [],
#                 "short_answer_questions": [],
#                 "long_answer_questions": [],
#                 "error": str(e)
#             }


import os
import json
import random
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
genai_client = genai.Client(api_key=API_KEY)

class QuestionGenerator:
    """Question Generator Agent that creates various types of questions"""
    
    def __init__(self):
        # Use gemini-2.5-flash for free tier (has quota, unlike gemini-2.5-pro which has limit 0)
        # gemini-pro-latest maps to gemini-2.5-pro which has quota limit 0 on free tier
        # gemini-2.5-flash is free tier compatible and works well
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    def _calculate_difficulty_distribution(
        self, 
        total_questions: int, 
        difficulty: str, 
        difficulty_distribution: Optional[Dict[str, int]] = None
    ) -> Dict[str, int]:
        """Calculate how many questions of each difficulty level to generate"""
        if difficulty_distribution:
            return difficulty_distribution
        
        if difficulty == "mixed":
            # Distribute evenly across all difficulty levels
            per_level = total_questions // 3
            remainder = total_questions % 3
            return {
                "easy": per_level + (1 if remainder > 0 else 0),
                "medium": per_level + (1 if remainder > 1 else 0),
                "hard": per_level
            }
        elif difficulty == "easy":
            return {"easy": total_questions, "medium": 0, "hard": 0}
        elif difficulty == "hard":
            return {"easy": 0, "medium": 0, "hard": total_questions}
        else:  # medium
            return {"easy": 0, "medium": total_questions, "hard": 0}
    
    def generate_questions(
        self, 
        content_analysis: dict, 
        requirements: dict,
        difficulty_distribution: Optional[Dict[str, int]] = None
    ) -> dict:
        """Generate questions based on content analysis and requirements"""
        try:
            difficulty = requirements.get('difficulty', 'medium')
            num_mcq = requirements.get('num_mcq', 5)
            num_short = requirements.get('num_short', 3)
            num_long = requirements.get('num_long', 2)
            
            # Calculate difficulty distribution for each question type
            mcq_dist = self._calculate_difficulty_distribution(num_mcq, difficulty, difficulty_distribution)
            short_dist = self._calculate_difficulty_distribution(num_short, difficulty, difficulty_distribution)
            long_dist = self._calculate_difficulty_distribution(num_long, difficulty, difficulty_distribution)
            
            # Build prompt with set variation note if present
            set_variation_note = requirements.get('set_variation_note', '')
            
            prompt = f"""
            Based on the following content analysis, generate questions according to the requirements.
            
            Content Analysis:
            - Key Concepts: {content_analysis.get('key_concepts', [])}
            - Difficulty Level: {content_analysis.get('difficulty_level', 'medium')}
            - Subject Areas: {content_analysis.get('subject_areas', [])}
            - Important Points: {content_analysis.get('important_points', [])}
            - Question-worthy Content: {content_analysis.get('question_worthy_content', [])}
            
            Requirements:
            - Number of MCQs: {num_mcq} (Easy: {mcq_dist['easy']}, Medium: {mcq_dist['medium']}, Hard: {mcq_dist['hard']})
            - Number of Short Answer Questions: {num_short} (Easy: {short_dist['easy']}, Medium: {short_dist['medium']}, Hard: {short_dist['hard']})
            - Number of Long Answer Questions: {num_long} (Easy: {long_dist['easy']}, Medium: {long_dist['medium']}, Hard: {long_dist['hard']})
            - Marks per MCQ: {requirements.get('marks_mcq', 1)}
            - Marks per Short Answer: {requirements.get('marks_short', 3)}
            - Marks per Long Answer: {requirements.get('marks_long', 5)}
            - Overall Difficulty: {difficulty}
            {set_variation_note}
            
            IMPORTANT: Generate questions with the specified difficulty distribution. Make sure to create 
            questions that match the difficulty levels (easy questions should be straightforward, 
            medium questions should require moderate understanding, hard questions should require deep analysis).
            
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
            
            Return ONLY valid JSON. Ensure the difficulty distribution matches the requirements.
            """
            
            response = genai_client.models.generate_content(
                model=self.model,
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
    
    def generate_multiple_sets(
        self,
        content_analysis: dict,
        requirements: dict,
        num_sets: int = 3,
        difficulty_distribution: Optional[Dict[str, int]] = None
    ) -> List[dict]:
        """Generate multiple sets of questions with variations"""
        sets = []
        
        for set_num in range(1, num_sets + 1):
            print(f"Generating question set {set_num}/{num_sets}...")
            
            # Add variation instruction for different sets
            set_requirements = requirements.copy()
            if num_sets > 1:
                # Add instruction to ensure uniqueness
                variation_note = f"""
                
IMPORTANT FOR SET VARIATION:
This is Set {set_num} of {num_sets} question papers. 
Ensure ALL questions in this set are completely different from the other sets.
Use different wording, different concepts, and different approaches.
Do NOT repeat any questions from previous sets.
"""
                set_requirements['set_variation_note'] = variation_note
            
            questions = self.generate_questions(
                content_analysis,
                set_requirements,
                difficulty_distribution
            )
            
            # Add set identifier
            questions['set_number'] = set_num
            questions['set_name'] = f"Set {set_num}"
            
            sets.append(questions)
        
        return sets