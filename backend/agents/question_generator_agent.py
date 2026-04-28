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
import time
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
genai_client = genai.Client(api_key=API_KEY)


def _call_groq_qgen(prompt: str) -> str:
    """Fallback: call Groq LLaMA when Gemini is unavailable."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set – cannot fall back to Groq.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert academic question paper generator. "
                    "Always respond with valid JSON only, no extra commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 4096,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

class QuestionGenerator:
    """Question Generator Agent that creates various types of questions"""
    
    def __init__(self):
        # Use gemini-2.5-flash for free tier (has quota, unlike gemini-2.5-pro which has limit 0)
        # gemini-pro-latest maps to gemini-2.5-pro which has quota limit 0 on free tier
        # gemini-2.5-flash is free tier compatible and works well
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def _generate_with_fallback(self, prompt: str, max_retries: int = 2) -> str:
        """Try Gemini first; on 503/429/quota errors fall back to Groq LLaMA."""
        last_error = None

        for attempt in range(max_retries):
            try:
                response = genai_client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                result_text = getattr(response, "text", "") or ""

                if not result_text.strip():
                    raise RuntimeError(
                        f"Gemini returned an empty response. Model: {self.model}. "
                        "This usually means the API key has no quota or the model is unavailable."
                    )

                print(
                    f"[QuestionGenerator] Gemini response OK "
                    f"(attempt {attempt + 1}, length: {len(result_text)})"
                )
                return result_text

            except Exception as e:
                err_str = str(e)
                print(f"[QuestionGenerator] Gemini error (attempt {attempt + 1}): {err_str}")
                last_error = e

                is_transient = any(
                    code in err_str
                    for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "quota")
                )

                if is_transient:
                    if GROQ_API_KEY:
                        print(
                            "[QuestionGenerator] ⚡ Gemini unavailable – switching to Groq LLaMA fallback..."
                        )
                        try:
                            text = _call_groq_qgen(prompt)
                            print(
                                f"[QuestionGenerator] Groq fallback succeeded "
                                f"(length: {len(text)})"
                            )
                            return text
                        except Exception as groq_err:
                            print(f"[QuestionGenerator] Groq fallback also failed: {groq_err}")
                            raise RuntimeError(
                                f"Both Gemini and Groq failed. "
                                f"Gemini: {err_str} | Groq: {groq_err}"
                            )
                    else:
                        if attempt < max_retries - 1:
                            wait = 3 * (2 ** attempt)
                            print(f"[QuestionGenerator] Retrying Gemini in {wait}s...")
                            time.sleep(wait)
                else:
                    raise

        raise last_error or RuntimeError("QuestionGenerator: all attempts failed")


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
            institution_standard = requirements.get('institution_standard', 'General')
            
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
            - Institution Standard/Format: {institution_standard}
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
            
            Additionally, ensure the structure, depth, and tone strictly align with the {institution_standard} examination guidelines.
            
            Please generate questions in JSON format with this structure:
            {{
                "mcq_questions": [
                    {{
                        "question": "question text",
                        "options": ["option1", "option2", "option3", "option4"],
                        "correct_answer": "correct option",
                        "marks": {requirements.get('marks_mcq', 1)},
                        "difficulty": "easy/medium/hard"
                    }}
                ],
                "short_answer_questions": [
                    {{
                        "question": "question text",
                        "correct_answer": "brief answer",
                        "marks": {requirements.get('marks_short', 3)},
                        "difficulty": "easy/medium/hard"
                    }}
                ],
                "long_answer_questions": [
                    {{
                        "question": "question text",
                        "correct_answer": "detailed answer",
                        "marks": {requirements.get('marks_long', 5)},
                        "difficulty": "easy/medium/hard"
                    }}
                ]
            }}
            
            Return ONLY valid JSON. Ensure the difficulty distribution matches the requirements.
            """
            
            result_text = self._generate_with_fallback(prompt)
            
            # Try to extract JSON from the response
            try:
                # Remove markdown code blocks if present
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                parsed = json.loads(result_text)
            except json.JSONDecodeError as je:
                print(f"[QuestionGenerator] JSON parse failed. Raw text (first 500 chars): {result_text[:500]}")
                raise RuntimeError(
                    f"Gemini returned invalid JSON that could not be parsed. "
                    f"Parse error: {je}. First 200 chars of response: {result_text[:200]}"
                )
            
            # Validate that questions were actually generated
            total_generated = (
                len(parsed.get("mcq_questions", [])) +
                len(parsed.get("short_answer_questions", [])) +
                len(parsed.get("long_answer_questions", []))
            )
            if total_generated == 0:
                print(f"[QuestionGenerator] WARNING: Gemini returned 0 questions. Parsed data: {parsed}")
                raise RuntimeError(
                    "Gemini returned a valid JSON response but with 0 questions. "
                    "This may indicate the content was too short or unclear for question generation."
                )
            
            print(f"[QuestionGenerator] Successfully generated {total_generated} questions")
            return parsed
                
        except Exception as e:
            print(f"Error in question generation: {e}")
            raise
    
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