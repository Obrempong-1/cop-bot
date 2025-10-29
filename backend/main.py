# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import faiss
import fitz  
import numpy as np
import requests
import asyncio
import datetime
import os
import re
from google import genai  
from urllib.parse import urlparse


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not found in .env file")
else:
    print("✅ GEMINI_API_KEY loaded successfully")


client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "models/gemini-2.5-pro-preview-03-25"  


app = FastAPI(
    title="PIWC Asokwa Chatbot API",
    description="Chatbot backend for PIWC Asokwa powered by Gemini, Facebook live data, and local documents.",
    version="2.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


BASE_DIR = Path(__file__).resolve().parent
DOCS_PATH = BASE_DIR / "documents"
CHUNK_SIZE = 300
pdf_chunks = []

if DOCS_PATH.exists():
    for file_name in os.listdir(DOCS_PATH):
        if file_name.endswith(".pdf"):
            path = DOCS_PATH / file_name
            try:
                with fitz.open(path) as doc:
                    text = "".join(page.get_text() for page in doc)
                words = text.split()
                for i in range(0, len(words), CHUNK_SIZE):
                    pdf_chunks.append(" ".join(words[i:i + CHUNK_SIZE]))
            except Exception as e:
                print(f"⚠️ Error reading {file_name}: {e}")
else:
    print(f"⚠️ '{DOCS_PATH}' folder not found")

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

if pdf_chunks:
    embeddings = embed_model.encode(pdf_chunks, convert_to_numpy=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    print(f"✅ Loaded {len(pdf_chunks)} document chunks into FAISS index")
else:
    index = None
    print("⚠️ No documents indexed — chatbot will rely on Gemini + Facebook + web context")

def search_pdf(query: str, top_k=2):
    if not index:
        return ""
    query_vector = embed_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_vector, top_k)
    return "\n\n".join([pdf_chunks[i] for i in indices[0]])


BIBLE_API_URL = "https://bible-api.com/"

def fetch_bible_verse(reference: str):
    try:
        ref = reference.replace(" ", "%20")
        response = requests.get(BIBLE_API_URL + ref, timeout=5)
        if response.status_code == 200:
            data = response.json()
            verses = [v["text"] for v in data.get("verses", [])]
            return " ".join(verses)
        return "❌ Verse not found."
    except Exception as e:
        print("Bible API error:", e)
        return "⚠️ Error fetching Bible verse."


FB_PAGES = {
    "PIWC": "https://m.facebook.com/piwcasokwa",
    "COP": "https://m.facebook.com/thecophq"
}

FB_CACHE = {"data": {}, "timestamp": None}

def fetch_facebook_latest_posts():
    """
    Fetch the latest visible posts from Facebook mobile pages.
    Caches results for 10 minutes.
    """
    global FB_CACHE
    now = datetime.datetime.utcnow()

    
    if FB_CACHE["timestamp"] and (now - FB_CACHE["timestamp"]).total_seconds() < 600:
        return FB_CACHE["data"]

    results = {}
    headers = {"User-Agent": "Mozilla/5.0"}

    for name, url in FB_PAGES.items():
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            posts = []
            for p in soup.find_all(["p", "div"]):
                text = p.get_text(strip=True)
                if 50 < len(text) < 400:
                    posts.append(text)

            results[name] = "\n".join(posts[:5]) if posts else "No recent posts found."
        except Exception as e:
            print(f"⚠️ Facebook fetch error ({name}): {e}")
            results[name] = ""

    FB_CACHE = {"data": results, "timestamp": now}
    return results


CACHE = {}
executor = ThreadPoolExecutor(max_workers=3)

async def async_query_gemini(prompt: str):
    if not prompt or len(prompt.strip()) < 2:
        return (
            "👋 Hello! Could you please provide a little more detail? "
            "You can ask about church policies, leadership, upcoming events, or biblical topics."
        )

    if prompt in CACHE:
        return CACHE[prompt]

  
    pdf_context = search_pdf(prompt)
    fb_data = fetch_facebook_latest_posts()
    piwc_fb = fb_data.get("PIWC", "")
    cop_fb = fb_data.get("COP", "")

    
    if any(word in prompt.lower() for word in ["event", "theme", "announcement", "news", "activity", "update"]):
        context_source = (
            f"Recent Facebook Updates:\n\n"
            f"PIWC Asokwa:\n{piwc_fb}\n\n"
            f"The Church of Pentecost HQ:\n{cop_fb}"
        )
    elif any(word in prompt.lower() for word in ["policy", "doctrine", "manual", "handbook"]):
        context_source = f"Official church documents:\n{pdf_context}"
    else:
        context_source = (
            f"Reference Materials:\n{pdf_context}\n\n"
            f"Facebook Insights:\n{piwc_fb}\n\n{cop_fb}"
        )

    def call_gemini():
        smart_prompt = f"""
You are a smart, friendly assistant for The Church of Pentecost (PIWC Asokwa). 
Your goal is to always answer intelligently, even when the question is vague.

Rules:
1. Reformulate unclear user input to make sense of it.
2. Combine church documents, Facebook data, and biblical insights.
3. Always give structured, factual, and referenced answers.
4. Include a short "📘 References" section that points to your sources.
5. If something is uncertain, clarify politely — do not fabricate info.

Context Sources:
{context_source}

User Input:
{prompt}

Now provide a clear, structured, and referenced answer.
"""
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=smart_prompt
            )
            answer = response.text if hasattr(response, "text") else "⚠️ No response text found."
            if "📘 Reference" not in answer and "📘 References" not in answer:
                answer += "\n\n📘 References:\n- Church Manuals, Facebook Pages, or available local sources."
            return answer
        except Exception as e:
            print("Gemini error:", e)
            return f"⚠️ Error contacting Gemini: {str(e)}"

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(executor, call_gemini)
    CACHE[prompt] = answer
    return answer


@app.on_event("startup")
async def startup_event():
    print("🚀 PIWC Asokwa Chatbot API started successfully using model:", MODEL_NAME)

@app.get("/")
async def root():
    return {
        "message": "Welcome to the PIWC Asokwa Chatbot API 🚀",
        "model": MODEL_NAME,
        "docs_url": "/docs",
        "status": "running"
    }

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message.strip()

    bible_match = re.match(r"^what does the bible say about (.*)$", user_message.lower())
    if bible_match:
        reference = bible_match.group(1).strip()
        verse = fetch_bible_verse(reference)
        return {"reply": verse}

    gemini_resp = await async_query_gemini(user_message)
    return {"reply": gemini_resp}


@app.get("/models")
async def list_gemini_models():
    try:
        models = client.models.list()
        model_list = []
        for model in models:
            model_list.append({
                "name": model.name,
                "display_name": getattr(model, "display_name", None),
                "description": getattr(model, "description", None),
                "type": getattr(model, "type_", None),
            })
        return {"models": model_list}
    except Exception as e:
        print("⚠️ Error fetching models:", e)
        return {"error": f"Failed to list models: {str(e)}"}
