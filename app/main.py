import os
import asyncio
import uuid
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq
from app.weather_mcp import get_farming_weather_advice
from app.market_mcp import get_mandi_price, get_all_prices
from app.farmer_memory import (
    get_or_create_profile, update_profile,
    add_to_history, extract_profile_info, build_context
)
from app.security import check_message

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
api_key = os.getenv("GROQ_API_KEY")
print(f"[AgriGuard] API Key loaded: {'YES' if api_key else 'NO'}")
if not api_key:
    raise ValueError("GROQ_API_KEY not found!")

client = Groq(api_key=api_key)
app = FastAPI(title="AgriGuard")

AGENTS = {
    "weather": "You are a weather and irrigation expert for Indian farmers. You will be given REAL weather data. Summarize it clearly and give practical farming advice.",
    "crop_doctor": "You are a crop disease and pest expert for Indian farmers. Diagnose problems and give affordable remedy advice in simple language.",
    "market": "You will be given REAL mandi price data. Summarize it clearly and give practical selling advice to the farmer.",
    "orchestrator": "You are AgriGuard, a friendly AI assistant for Indian farmers. Answer farming questions helpfully and briefly."
}

def ai_understand(message: str) -> dict:
    """Use Groq to understand message — handles any language, spelling, dialect"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """You are a message analyzer for an Indian farming assistant.
Analyze the farmer's message and return ONLY a JSON object with these fields:
{
  "intent": "weather" or "crop_doctor" or "market" or "general",
  "city": "city name in English or null",
  "crop": "crop name in English or null",
  "state": "state name in English or null",
  "language": "Hindi" or "English"
}

Intent rules:
- weather: anything about rain, temperature, irrigation, forecast, monsoon, बारिश, मौसम, पानी, barish, mausam
- crop_doctor: anything about pests, disease, insects, dying crops, spots, कीड़े, बीमारी, कीट, kide, keeda, bimari, fasal me samasya
- market: anything about price, mandi, selling, rate, भाव, मंडी, कीमत, tamatar price, gehu bhav
- general: anything else

Always correct spelling mistakes. Understand Hindi, Hinglish, broken English, and local dialects.
Examples:
- "meri fasal me kide lag gae he" → crop_doctor
- "tamatar ki price ahmedabad me kya he" → market, crop=tomato, city=Ahmedabad
- "kya kal barish hogi ahmedabad me" → weather, city=Ahmedabad
- "gehu me pila rang aa raha he" → crop_doctor, crop=wheat
- "pyaj ka bhav kya he gujarat me" → market, crop=onion, state=gujarat
- "will it rain in mumbai tomorrow" → weather, city=Mumbai

Return ONLY the JSON object, no explanation, no markdown."""
                },
                {"role": "user", "content": message}
            ],
            max_tokens=150,
            temperature=0
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        print(f"[AgriGuard] AI understood: {result}")
        return result

    except Exception as e:
        print(f"[AgriGuard] AI understanding failed: {e}, using fallback")
        msg = message.lower()
        intent = "general"
        if any(w in msg for w in ["rain","weather","barish","mausam","baarish","irrigation","forecast","monsoon"]):
            intent = "weather"
        elif any(w in msg for w in ["disease","pest","kide","keeda","bimari","spots","dying","insect","fungus","spray"]):
            intent = "crop_doctor"
        elif any(w in msg for w in ["price","mandi","bhav","keemat","sell","rate","tamatar","gehu","pyaj"]):
            intent = "market"
        return {"intent": intent, "city": None, "crop": None, "state": None, "language": "English"}

def correct_spelling(message: str) -> str:
    """Use Groq to fix spelling mistakes"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a spelling correction tool. Fix only spelling mistakes in the user's message. Keep the same language. Do not answer the question. Return ONLY the corrected text, nothing else."
                },
                {"role": "user", "content": message}
            ],
            max_tokens=150,
            temperature=0
        )
        corrected = response.choices[0].message.content.strip().strip('"').strip("'")
        return corrected if corrected else message
    except Exception as e:
        print(f"[AgriGuard] Spell correction failed: {e}")
        return message

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    agent_used: str
    session_id: str
    farmer_name: str = ""

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/health")
async def health():
    return {"status": "ok", "api_key_loaded": bool(api_key)}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Security check first
    security = check_message(request.message)
    if not security["allowed"]:
        print(f"[AgriGuard] BLOCKED: {security['reason']} — {request.message[:50]}")
        return ChatResponse(
            response=security["response"],
            agent_used="security",
            session_id=request.session_id or str(uuid.uuid4()),
            farmer_name=""
        )

    # Auto-correct spelling
    original_message = request.message
    corrected_message = await asyncio.wait_for(
        asyncio.get_event_loop().run_in_executor(None, lambda: correct_spelling(request.message)),
        timeout=10.0
    )
    if corrected_message.lower() != original_message.lower():
        print(f"[AgriGuard] Spell corrected: '{original_message}' → '{corrected_message}'")
        request.message = corrected_message

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    profile = get_or_create_profile(session_id)

    # Extract and save profile info
    updates = extract_profile_info(request.message, profile)
    if updates:
        update_profile(session_id, updates)
        profile.update(updates)

    # AI-powered understanding
    understanding = await asyncio.wait_for(
        asyncio.get_event_loop().run_in_executor(None, lambda: ai_understand(request.message)),
        timeout=10.0
    )

    agent_name = understanding.get("intent", "general")
    if agent_name == "general":
        agent_name = "orchestrator"
    language = understanding.get("language", "English")

    system_prompt = AGENTS[agent_name]
    print(f"[AgriGuard] Session: {session_id[:8]} | Agent: {agent_name} | Language: {language}")

    # Build farmer context from memory
    farmer_context = build_context(profile)

    # Get real MCP data using AI-extracted entities
    mcp_data = ""
    if agent_name == "weather":
        city = understanding.get("city") or profile.get("location") or "Ahmedabad"
        mcp_data = get_farming_weather_advice(city)
    elif agent_name == "market":
        crop = understanding.get("crop") or "tomato"
        state = understanding.get("state") or "default"
        price_data = get_mandi_price(crop, state)
        if "error" in price_data:
            mcp_data = get_all_prices(state)
        else:
            mcp_data = f"""
REAL MANDI DATA:
Crop: {price_data['crop']}
State: {price_data['state']}
Price: ₹{price_data['price']} {price_data['unit']}
Trend: {price_data['trend'].title()}
Best Market: {price_data['best_market']}
Advice: {price_data['advice']}
"""

    # Build full message
    user_message = request.message
    if farmer_context:
        user_message = f"FARMER PROFILE:\n{farmer_context}\n\nFarmer's question: {request.message}"
    if mcp_data:
        user_message += f"\n\nREAL DATA FROM MCP SERVER:\n{mcp_data}\n\nUse this real data to answer."

    user_message += f"\n\nIMPORTANT: Reply ONLY in {language}. Do not mix languages."

    try:
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt + f" Always reply in {language} only."},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=400
                )
            ),
            timeout=20.0
        )
        reply = response.choices[0].message.content
        add_to_history(session_id, request.message, reply, agent_name)
        print(f"[AgriGuard] {agent_name} replied OK")

        return ChatResponse(
            response=reply,
            agent_used=agent_name,
            session_id=session_id,
            farmer_name=profile.get("name") or ""
        )

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Response timed out. Please try again.")
    except Exception as e:
        print(f"[AgriGuard] ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    print(f"[AgriGuard] Starting at http://localhost:{port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)