"""
Helper script to verify Gemini API key and model access.

This repo uses the current Gemini SDK: `google-genai` (import path: `from google import genai`).
"""

import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file")
    print("Please add GEMINI_API_KEY=your_key_here to your .env file")
    exit(1)

print(f"✅ API Key found: {API_KEY[:10]}...{API_KEY[-4:] if len(API_KEY) > 14 else ''}")

try:
    from google import genai

    client = genai.Client(api_key=API_KEY)
    # Default to flash to avoid free-tier quota=0 for pro models.
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    print(f"\n🧪 Testing model: {model_name} ...")
    response = client.models.generate_content(
        model=model_name,
        contents="Say hello in one short sentence.",
    )
    print("✅ Model works!")
    print(f"   Response: {(response.text or '')[:120]}...")

except Exception as e:
    print(f"❌ Error: {e}")
    if "API_KEY" in str(e) or "key" in str(e).lower():
        print("\n💡 Make sure your API key is valid and has proper permissions")
    elif "quota" in str(e).lower() or "429" in str(e):
        print("\n💡 You've hit a quota limit. Wait a bit and try again, or upgrade your plan")
    else:
        print(f"\n💡 Unexpected error: {type(e).__name__}")
