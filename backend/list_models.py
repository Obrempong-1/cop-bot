from google import genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("📜 Available Gemini models:\n")

for model in client.models.list():
    print(f"- ID: {model.name}")
    print(f"  Display Name: {getattr(model, 'display_name', 'N/A')}")
    print(f"  Description: {getattr(model, 'description', 'N/A')}")
    print()
