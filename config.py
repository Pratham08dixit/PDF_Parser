# config.py
import os
from dotenv import load_dotenv
load_dotenv()
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Gemini / LLM config placeholder — fill with your own API key & call method
LLM_PROVIDER = "GEMINI"   # or "OPENAI" or "NONE"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
