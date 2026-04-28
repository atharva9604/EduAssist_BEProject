import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

from google import genai

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set")


def _call_groq(prompt: str) -> str:
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
                    "You are an expert academic content analyzer. "
                    "Always respond with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 2048,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


class ContentAnalyzer:
    """Simple content analyzer using Gemini AI with Groq fallback."""

    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        # IMPORTANT: gemini-pro-latest can map to gemini-2.5-pro (free tier quota may be 0).
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def analyze_content(self, content: str, document_type: str = "text") -> dict:
        """Analyze content and extract key information"""
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

        result_text = self._generate_with_fallback(prompt)
        return self._parse_json(result_text)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_with_fallback(self, prompt: str, max_retries: int = 2) -> str:
        """Try Gemini first; on 503/429/quota errors fall back to Groq."""
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                result_text = getattr(response, "text", "") or ""

                if not result_text.strip():
                    raise RuntimeError(
                        f"Content analyzer: Gemini returned an empty response. "
                        f"Model: {self.model_name}. "
                        "This usually means the API key has no quota or the model is unavailable."
                    )

                print(
                    f"[ContentAnalyzer] Gemini response OK "
                    f"(attempt {attempt + 1}, length: {len(result_text)})"
                )
                return result_text

            except Exception as e:
                err_str = str(e)
                print(f"[ContentAnalyzer] Gemini error (attempt {attempt + 1}): {err_str}")
                last_error = e

                # Detect transient / quota errors that warrant a fallback
                is_transient = any(
                    code in err_str
                    for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "quota")
                )

                if is_transient:
                    # Try Groq fallback immediately if Gemini is unavailable
                    if GROQ_API_KEY:
                        print(
                            "[ContentAnalyzer] ⚡ Gemini unavailable – switching to Groq LLaMA fallback..."
                        )
                        try:
                            text = _call_groq(prompt)
                            print(
                                f"[ContentAnalyzer] Groq fallback succeeded "
                                f"(length: {len(text)})"
                            )
                            return text
                        except Exception as groq_err:
                            print(f"[ContentAnalyzer] Groq fallback also failed: {groq_err}")
                            raise RuntimeError(
                                f"Both Gemini and Groq failed. "
                                f"Gemini: {err_str} | Groq: {groq_err}"
                            )
                    else:
                        # No Groq key – retry after a short wait
                        if attempt < max_retries - 1:
                            wait = 3 * (2 ** attempt)
                            print(f"[ContentAnalyzer] Retrying Gemini in {wait}s...")
                            time.sleep(wait)
                else:
                    # Non-transient error – raise immediately
                    raise

        raise last_error or RuntimeError("Content analyzer: all attempts failed")

    @staticmethod
    def _parse_json(result_text: str) -> dict:
        """Extract and parse JSON from the model response."""
        try:
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(result_text)
            print(
                f"[ContentAnalyzer] Successfully parsed content analysis with "
                f"{len(parsed.get('key_concepts', []))} key concepts"
            )
            return parsed
        except json.JSONDecodeError as je:
            print(
                f"[ContentAnalyzer] JSON parse failed, using raw text as fallback. Error: {je}"
            )
            return {
                "key_concepts": [],
                "difficulty_level": "medium",
                "subject_areas": [],
                "important_points": [],
                "question_worthy_content": [result_text],
            }