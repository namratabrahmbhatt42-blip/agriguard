import json
import re
from datetime import datetime
from pathlib import Path

SECURITY_LOG = Path(__file__).parent.parent / "security_log.json"

# Prompt injection patterns
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "you are now",
    "forget everything",
    "new instructions",
    "system prompt",
    "jailbreak",
    "pretend you are",
    "act as if",
    "override",
    "bypass",
    "disregard"
]

# Off-topic keywords — things not related to farming
OFF_TOPIC_PATTERNS = [
    "write my essay", "do my homework", "write code for",
    "hack ", "crack password", "illegal",
    "politics", "election", "movie", "cricket score",
    "stock market", "bitcoin", "crypto",
    "tell me a joke", "sing a song", "write a poem",
    "relationship advice", "dating"
]

# Farming related keywords — always allow these
FARMING_KEYWORDS = [
    "crop", "farm", "farmer", "field", "soil", "seed", "harvest",
    "irrigation", "fertilizer", "pesticide", "weather", "rain",
    "mandi", "price", "market", "disease", "pest", "plant",
    "wheat", "rice", "tomato", "cotton", "onion", "potato",
    "खेती", "किसान", "फसल", "मंडी", "बारिश", "मौसम", "कीड़े"
]

def log_security_event(message: str, reason: str, blocked: bool):
    """Log security events to file"""
    logs = []
    if SECURITY_LOG.exists():
        with open(SECURITY_LOG, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except:
                logs = []

    logs.append({
        "timestamp": datetime.now().isoformat(),
        "message": message[:100],
        "reason": reason,
        "blocked": blocked
    })

    with open(SECURITY_LOG, "w", encoding="utf-8") as f:
        json.dump(logs[-100:], f, ensure_ascii=False, indent=2)

def check_message(message: str) -> dict:
    """
    Check if message is safe and farming-related.
    Returns: {"allowed": bool, "reason": str, "response": str}
    """
    msg_lower = message.lower()

    # Check for prompt injection
    for pattern in INJECTION_PATTERNS:
        if pattern in msg_lower:
            log_security_event(message, f"Prompt injection: {pattern}", True)
            return {
                "allowed": False,
                "reason": "prompt_injection",
                "response": "I'm AgriGuard, an assistant for farmers. I can only help with farming questions about crops, weather, and market prices."
            }

    # If it contains farming keywords — always allow
    for keyword in FARMING_KEYWORDS:
        if keyword.lower() in msg_lower:
            log_security_event(message, "Allowed - farming keyword found", False)
            return {"allowed": True, "reason": "farming_content", "response": ""}

    # Check for off-topic content
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern in msg_lower:
            log_security_event(message, f"Off-topic: {pattern}", True)
            return {
                "allowed": False,
                "reason": "off_topic",
                "response": "I'm AgriGuard, your farming assistant! I can help you with crop diseases, weather forecasts, and mandi prices. What farming question can I answer for you?"
            }

    # Allow by default — better to be helpful than over-restrict
    log_security_event(message, "Allowed - default", False)
    return {"allowed": True, "reason": "default_allow", "response": ""}