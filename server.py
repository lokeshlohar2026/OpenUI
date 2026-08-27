from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from google import genai
from openui_library import OPENUI_PROMPT, BASE_SYSTEM_PROMPT

load_dotenv()
client = genai.Client()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SYSTEM_PROMPT = f"{BASE_SYSTEM_PROMPT}\n\n{OPENUI_PROMPT}"

@app.post("/demo")
async def stream(req: Request):
    body = await req.json()
    query = body.get("message","")
    def gen():
        stream = client.models.generate_content_stream(
            model="gemini-flash-latest",
            contents=query,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.2))