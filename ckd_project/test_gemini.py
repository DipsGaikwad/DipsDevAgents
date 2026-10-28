
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise SystemExit("ERROR: GEMINI_API_KEY was not found in .env")

try:
    client = genai.Client(api_key=api_key)

    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input="Explain how AI works in a few words."
    )

    print("SUCCESS: Gemini API is working!")
    print(interaction.output_text)

except Exception as exc:
    print("Gemini API request failed.")
    print(type(exc).__name__ + ":", str(exc))
