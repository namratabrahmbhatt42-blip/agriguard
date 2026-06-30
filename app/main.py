import os
import asyncio
import uuid
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
from typing import Optional

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
api_key = os.getenv("GROQ_API_KEY")
print(f"[AgriGuard] API Key loaded: {'YES' if api_key else 'NO'}")
if not api_key:
    raise ValueError("GROQ_API_KEY not found!")

client = Groq(api_key=api_key)
app = FastAPI(title="AgriGuard")

AGENTS = {
    "weather": "You are a weather and irrigation expert for Indian farmers. You will be given REAL weather data. Summarize it clearly and give farming advice.",
    "crop_doctor": "You are a crop disease expert for Indian farmers. Diagnose crop diseases and give affordable remedy advice in max 4 sentences.",
    "market": "You will be given REAL mandi price data. Summarize it clearly and give selling advice to the farmer.",
    "orchestrator": "You are AgriGuard, a friendly AI assistant for Indian farmers. Answer farming questions helpfully and briefly."
}

def extract_city(message: str) -> str:
    indian_cities = [
        "ahmedabad", "surat", "vadodara", "rajkot", "mumbai", "pune", "delhi",
        "bangalore", "hyderabad", "chennai", "kolkata", "jaipur", "lucknow",
        "nagpur", "indore", "bhopal", "patna", "ludhiana", "amritsar"
    ]
    msg_lower = message.lower()
    for city in indian_cities:
        if city in msg_lower:
            return city.title()
    return "Ahmedabad"

def extract_crop(message: str) -> str:
    crop_map = {
        "tomato": "tomato", "टमाटर": "tomato",
        "wheat": "wheat", "गेहूं": "wheat", "गेहु": "wheat",
        "rice": "rice", "चावल": "rice", "धान": "rice",
        "onion": "onion", "प्याज": "onion", "प्याज़": "onion",
        "cotton": "cotton", "कपास": "cotton",
        "potato": "potato", "आलू": "potato"
    }
    for keyword, crop in crop_map.items():
        if keyword.lower() in message.lower():
            return crop
    return "tomato"

def extract_state(message: str) -> str:
    state_map = {
        "gujarat": "gujarat", "gujrat": "gujarat", "गुजरात": "gujarat",
        "maharashtra": "maharashtra", "महाराष्ट्र": "maharashtra",
        "punjab": "punjab", "पंजाब": "punjab",
        "haryana": "haryana", "हरियाणा": "haryana",
        "rajasthan": "rajasthan", "राजस्थान": "rajasthan",
        "uttar pradesh": "uttar pradesh", "उत्तर प्रदेश": "uttar pradesh",
        "up": "uttar pradesh",
        "west bengal": "west bengal", "पश्चिम बंगाल": "west bengal",
        "karnataka": "karnataka", "कर्नाटक": "karnataka",
        "tamil nadu": "tamil nadu", "tamilnadu": "tamil nadu"
    }
    for keyword, state in state_map.items():
        if keyword.lower() in message.lower():
            return state
    return "default"

def detect_language(message: str) -> str:
    """Detect if message is Hindi (Devanagari script) or English"""
    hindi_chars = sum(1 for ch in message if '\u0900' <= ch <= '\u097F')
    if hindi_chars > 0:
        return "Hindi"
    return "English"

def route_query(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ["rain","weather","temperature","irrigation","water","forecast","monsoon","humid","बारिश","मौसम","सिंचाई","तापमान"]):
        return "weather"
    elif any(w in msg for w in ["disease","pest","yellow","spots","leaves","dying","insects","fungus","spray","wilt","rot","कीड़े","बीमारी","पत्ते","कीट","फफूंद"]):
        return "crop_doctor"
    elif any(w in msg for w in ["price","mandi","sell","market","rate","rupee","profit","cost","भाव","मंडी","बेचना","कीमत","मुनाफा"]):
        return "market"
    else:
        return "orchestrator"

def correct_spelling(message: str) -> str:
    """Use Groq to fix spelling mistakes before processing"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a spelling correction tool. Fix only spelling mistakes in the user's message. Keep the same language (English or Hindi). Do not change the meaning, do not answer the question, do not add anything extra. Return ONLY the corrected text, nothing else. If there are no mistakes, return the original text unchanged."
                },
                {"role": "user", "content": message}
            ],
            max_tokens=150,
            temperature=0
        )
        corrected = response.choices[0].message.content.strip()
        # Remove quotes if model wrapped the response
        corrected = corrected.strip('"').strip("'")
        return corrected if corrected else message
    except Exception as e:
        print(f"[AgriGuard] Spell correction failed: {e}")
        return message

def get_mcp_data(agent_name: str, message: str) -> str:
    if agent_name == "weather":
        city = extract_city(message)
        return get_farming_weather_advice(city)
    elif agent_name == "market":
        crop = extract_crop(message)
        state = extract_state(message)
        price_data = get_mandi_price(crop, state)
        if "error" in price_data:
            return get_all_prices(state)
        return f"""
REAL MANDI DATA:
Crop: {price_data['crop']}
State: {price_data['state']}
Price: ₹{price_data['price']} {price_data['unit']}
Trend: {price_data['trend'].title()}
Best Market: {price_data['best_market']}
Advice: {price_data['advice']}
"""
    return ""

from typing import Optional

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

    # Auto-correct spelling mistakes
    original_message = request.message
    corrected_message = await asyncio.wait_for(
        asyncio.get_event_loop().run_in_executor(None, lambda: correct_spelling(request.message)),
        timeout=10.0
    )
    if corrected_message.lower() != original_message.lower():
        print(f"[AgriGuard] Spell corrected: '{original_message}' → '{corrected_message}'")
        request.message = corrected_message

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

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    profile = get_or_create_profile(session_id)

    # Extract and save any profile info from message
    updates = extract_profile_info(request.message, profile)
    if updates:
        update_profile(session_id, updates)
        profile.update(updates)

    # Route to correct agent
    agent_name = route_query(request.message)
    system_prompt = AGENTS[agent_name]
    print(f"[AgriGuard] Session: {session_id[:8]} | Routing to: {agent_name}")

    # Build farmer context from memory
    farmer_context = build_context(profile)

    # Get real MCP data
    mcp_data = get_mcp_data(agent_name, request.message)

    # Detect language strictly from the message
    language = detect_language(request.message)

    # Build full message with context + real data
    user_message = request.message
    if farmer_context:
        user_message = f"FARMER PROFILE (use to personalize response):\n{farmer_context}\n\nFarmer's question: {request.message}"
    if mcp_data:
        user_message += f"\n\nREAL DATA FROM MCP SERVER:\n{mcp_data}\n\nPlease use this real data to answer clearly."

    user_message += f"\n\nIMPORTANT: Reply ONLY in {language}. Do not mix languages. Do not use any other script."

    try:
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt + f" Always reply in {language} only, matching the language of the farmer's question exactly."},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=400
                )
            ),
            timeout=20.0
        )
        reply = response.choices[0].message.content

        # Save to memory
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
    print("[AgriGuard] Starting at http://localhost:8080")
    uvicorn.run("app.main:app", host="localhost", port=8080, reload=True)