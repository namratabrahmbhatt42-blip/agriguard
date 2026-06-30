import json
import os
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).parent.parent / "farmer_profiles.json"

def load_profiles() -> dict:
    """Load all farmer profiles from disk"""
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_profiles(profiles: dict):
    """Save all profiles to disk"""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def get_or_create_profile(session_id: str) -> dict:
    """Get existing farmer profile or create new one"""
    profiles = load_profiles()
    if session_id not in profiles:
        profiles[session_id] = {
            "session_id": session_id,
            "name": None,
            "location": None,
            "crops": [],
            "conversation_history": [],
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        save_profiles(profiles)
    return profiles[session_id]

def update_profile(session_id: str, updates: dict):
    """Update farmer profile with new information"""
    profiles = load_profiles()
    if session_id in profiles:
        profiles[session_id].update(updates)
        profiles[session_id]["last_active"] = datetime.now().isoformat()
        save_profiles(profiles)

def add_to_history(session_id: str, user_message: str, agent_response: str, agent_used: str):
    """Add conversation turn to history — keep last 5"""
    profiles = load_profiles()
    if session_id in profiles:
        history = profiles[session_id].get("conversation_history", [])
        history.append({
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "agent": agent_used,
            "response": agent_response[:200]
        })
        # Keep only last 5 conversations
        profiles[session_id]["conversation_history"] = history[-5:]
        profiles[session_id]["last_active"] = datetime.now().isoformat()
        save_profiles(profiles)

def extract_profile_info(message: str, profile: dict) -> dict:
    """Extract name, location, crops from message and update profile"""
    updates = {}
    msg_lower = message.lower()

    # Extract name
    name_patterns = ["my name is", "i am ", "mera naam", "मेरा नाम"]
    for pattern in name_patterns:
        if pattern in msg_lower:
            idx = msg_lower.index(pattern) + len(pattern)
            name = message[idx:].split()[0].strip(".,!")
            if len(name) > 1:
                updates["name"] = name.title()
                break

    # Extract location
    cities = ["ahmedabad", "surat", "vadodara", "rajkot", "mumbai", "pune",
              "delhi", "bangalore", "hyderabad", "chennai", "kolkata", "jaipur",
              "lucknow", "nagpur", "indore", "bhopal", "patna", "ludhiana"]
    for city in cities:
        if city in msg_lower:
            updates["location"] = city.title()
            break

    # Extract crops
    crop_keywords = ["tomato", "wheat", "rice", "onion", "cotton", "potato",
                     "टमाटर", "गेहूं", "चावल", "प्याज", "कपास", "आलू"]
    found_crops = [c for c in crop_keywords if c in msg_lower]
    if found_crops:
        existing = profile.get("crops", [])
        all_crops = list(set(existing + found_crops))
        updates["crops"] = all_crops

    return updates

def build_context(profile: dict) -> str:
    """Build context string from farmer profile for the AI"""
    context_parts = []

    if profile.get("name"):
        context_parts.append(f"Farmer's name: {profile['name']}")
    if profile.get("location"):
        context_parts.append(f"Farmer's location: {profile['location']}")
    if profile.get("crops"):
        context_parts.append(f"Farmer grows: {', '.join(profile['crops'])}")

    history = profile.get("conversation_history", [])
    if history:
        context_parts.append("Recent conversation history:")
        for h in history[-3:]:
            context_parts.append(f"  - Farmer asked about {h['agent']}: {h['user'][:80]}")

    return "\n".join(context_parts) if context_parts else ""