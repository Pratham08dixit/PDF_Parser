# llm_client.py
import os
import json
from config import GEMINI_API_KEY, LLM_PROVIDER

# Option 1: OpenAI client
# Option 2: Gemini client
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except ImportError:
    pass


def call_llm_for_json(system_prompt: str, reasoning_prompt: str, content: str) -> dict:
    """
    Calls the configured LLM (Gemini or OpenAI) to convert raw PDF content into structured JSON.
    """
    if LLM_PROVIDER.upper() == "GEMINI" and GEMINI_API_KEY:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content([
            {"role": "system", "parts": [system_prompt]},
            {"role": "developer", "parts": [reasoning_prompt]},
            {"role": "user", "parts": [content]}
        ])
        output = response.text

    else:
        raise RuntimeError("No valid LLM provider or API key configured")

    try:
        return json.loads(output)
    except Exception:
        raise ValueError("LLM did not return valid JSON: " + str(output)[:500])
