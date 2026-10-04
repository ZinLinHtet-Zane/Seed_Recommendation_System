import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Add GEMINI_API_KEY to backend/.env")

client = genai.Client(api_key=api_key)

response = client.interactions.create(
    model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    input=(
        "Reply with one short sentence confirming that "
        "you can help explain seed recommendations in simple words."
    )
)

print(response.output_text)