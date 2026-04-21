import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

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
        # Try with google_search grounding first, fallback to plain generation
        for attempt, config in enumerate([
            types.GenerateContentConfig(tools=[{"google_search": {}}]),
            types.GenerateContentConfig(),  # fallback: no grounding
        ]):
            try:
                model_name = self.model if attempt == 0 else "gemini-2.0-flash"
                print(f"🔍 Research Lookout attempt {attempt+1} with model={model_name}, grounding={'yes' if attempt==0 else 'no'}")
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                result_text = getattr(response, "text", "") or ""
                
                # Clean JSON markdown blocks
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                    
                return json.loads(result_text)
            except Exception as e:
                print(f"⚠️ Research Lookout attempt {attempt+1} failed: {e}")
                last_error = e
                continue

        print(f"❌ All Research Lookout attempts failed: {last_error}")
        return {
            "trending_topics": [],
            "recent_papers": [],
            "error": str(last_error)
        }

# Instance for API
research_lookout_agent = ResearchLookoutAgent()
