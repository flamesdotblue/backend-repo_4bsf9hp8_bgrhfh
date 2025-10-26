import os
import requests
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: The API key is provided by the user for this sandbox.
# It is kept server-side and never exposed to the frontend.
GEMINI_API_KEY = "AIzaSyATgoWoZ_FKK4U_Y2E_y3BYaiPTLyIu698"
GEMINI_MODEL = "gemini-1.5-flash-latest"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

class TalkRequest(BaseModel):
    character: Literal["Togepi", "Pikachu"]
    message: str

class TalkResponse(BaseModel):
    reply: str


def build_system_prompt(character: str) -> str:
    if character == "Togepi":
        persona = (
            "You are Togepi from Pokémon. You speak in a cute, baby-like voice, "
            "often saying 'Toge! Toge!' sprinkled between short friendly phrases. "
            "Keep sentences short and joyful for young kids. Never say anything scary or complex."
        )
    else:
        persona = (
            "You are Pikachu from Pokémon. You speak playfully with cheerful energy, "
            "peppering in 'Pika! Pika!' and 'Pikachu!' between short phrases. "
            "Keep replies friendly, encouraging, and simple for kids."
        )
    guidelines = (
        "Always keep answers under 2 short sentences. Avoid web links. "
        "No violence, no sensitive topics. Encourage kindness and curiosity."
    )
    return f"{persona} {guidelines}"


def call_gemini(character: str, user_message: str) -> str:
    system_prompt = build_system_prompt(character)
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": system_prompt},
                    {"text": f"User said: {user_message}\nCharacter: {character}\nReply in-character."},
                ],
            }
        ]
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=20)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Gemini error: {resp.text[:200]}")
        data = resp.json()
        # Extract text safely
        reply = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if not reply:
            reply = "Pika! Let's try again!"
        return reply
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.post("/api/talk", response_model=TalkResponse)
def talk(req: TalkRequest):
    reply = call_gemini(req.character, req.message)
    return {"reply": reply}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
