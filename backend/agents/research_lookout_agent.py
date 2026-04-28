import os
import json
import time
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


def _call_groq_research(prompt: str) -> str:
    """Fallback to Groq LLaMA when Gemini is overloaded."""
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
                    "You are an expert academic Research Assistant. "
                    "Always respond with valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": 2048,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


class ResearchLookoutAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment variables.")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def conduct_research(self, title: str, description: str) -> Dict[str, Any]:
        prompt = f"""
        You are an expert academic Research Assistant. A professor is conducting research with the following details:
        Title: {title}
        Description: {description}

        Your task is to use Google Search to find completely grounded, up-to-date, and trending information related to this research.
        
        Please provide your findings in valid JSON format ONLY with exactly this structure:
        {{
            "trending_topics": [
                "Topic 1 - brief description of why it's trending",
                "Topic 2 - ...",
                "Topic 3 - ..."
            ],
            "recent_papers": [
                {{
                    "title": "Title of paper or article",
                    "url": "http://link-to-source...",
                    "snippet": "1 sentence explaining relevance"
                }}
            ]
        }}
        Provide up to 5 recent papers/articles. Return ONLY valid JSON. Focus on high-quality academic or tech references.
        """

        last_error = None

        # Attempt 1: Gemini with Google Search grounding
        # Attempt 2: Gemini without grounding (different model)
        # Attempt 3: Groq LLaMA fallback
        gemini_attempts = [
            (self.model, types.GenerateContentConfig(tools=[{"google_search": {}}])),
            ("gemini-2.0-flash", types.GenerateContentConfig()),
        ]

        for attempt, (model_name, config) in enumerate(gemini_attempts):
            try:
                print(
                    f"🔍 Research Lookout attempt {attempt + 1} "
                    f"with model={model_name}, "
                    f"grounding={'yes' if attempt == 0 else 'no'}"
                )
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                result_text = getattr(response, "text", "") or ""
                return self._parse_json(result_text)

            except Exception as e:
                err_str = str(e)
                print(f"⚠️ Research Lookout attempt {attempt + 1} failed: {err_str}")
                last_error = e

                # Detect transient overload — skip to Groq immediately
                is_transient = any(
                    code in err_str
                    for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "quota")
                )
                if is_transient and GROQ_API_KEY:
                    print("⚡ Research Lookout: Gemini overloaded – switching to Groq LLaMA fallback...")
                    break  # Don't retry remaining Gemini attempts; go to Groq

        # Groq fallback
        if GROQ_API_KEY:
            try:
                print("🔄 Research Lookout: Trying Groq LLaMA...")
                text = _call_groq_research(prompt)
                result = self._parse_json(text)
                print("✅ Research Lookout: Groq fallback succeeded.")
                return result
            except Exception as groq_err:
                print(f"❌ Research Lookout: Groq fallback failed: {groq_err}")
                last_error = groq_err

        print(f"❌ All Research Lookout attempts failed: {last_error}")
        return {
            "trending_topics": [],
            "recent_papers": [],
            "error": str(last_error),
        }

    @staticmethod
    def _parse_json(result_text: str) -> dict:
        """Strip markdown fences and parse JSON."""
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        return json.loads(result_text)


# Instance for API
research_lookout_agent = ResearchLookoutAgent()
