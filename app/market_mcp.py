# Market MCP Server — realistic Indian mandi price data

MANDI_PRICES = {
    "tomato": {
        "gujarat": {"price": 1200, "unit": "per quintal", "trend": "rising", "best_market": "Ahmedabad APMC"},
        "maharashtra": {"price": 1100, "unit": "per quintal", "trend": "stable", "best_market": "Pune Market"},
        "punjab": {"price": 950, "unit": "per quintal", "trend": "falling", "best_market": "Jalandhar Mandi"},
        "default": {"price": 1050, "unit": "per quintal", "trend": "stable", "best_market": "Local APMC"}
    },
    "wheat": {
        "punjab": {"price": 2275, "unit": "per quintal", "trend": "stable", "best_market": "Ludhiana Mandi"},
        "haryana": {"price": 2250, "unit": "per quintal", "trend": "stable", "best_market": "Karnal Mandi"},
        "gujarat": {"price": 2200, "unit": "per quintal", "trend": "rising", "best_market": "Rajkot APMC"},
        "default": {"price": 2250, "unit": "per quintal", "trend": "stable", "best_market": "Local Mandi"}
    },
    "rice": {
        "west bengal": {"price": 2100, "unit": "per quintal", "trend": "stable", "best_market": "Kolkata Market"},
        "punjab": {"price": 2183, "unit": "per quintal", "trend": "rising", "best_market": "Amritsar Mandi"},
        "gujarat": {"price": 2050, "unit": "per quintal", "trend": "stable", "best_market": "Surat APMC"},
        "default": {"price": 2100, "unit": "per quintal", "trend": "stable", "best_market": "Local Mandi"}
    },
    "onion": {
        "maharashtra": {"price": 1800, "unit": "per quintal", "trend": "rising", "best_market": "Lasalgaon Mandi"},
        "gujarat": {"price": 1650, "unit": "per quintal", "trend": "rising", "best_market": "Mahuva APMC"},
        "rajasthan": {"price": 1500, "unit": "per quintal", "trend": "stable", "best_market": "Alwar Mandi"},
        "default": {"price": 1600, "unit": "per quintal", "trend": "stable", "best_market": "Local Mandi"}
    },
    "cotton": {
        "gujarat": {"price": 6500, "unit": "per quintal", "trend": "rising", "best_market": "Rajkot APMC"},
        "maharashtra": {"price": 6300, "unit": "per quintal", "trend": "stable", "best_market": "Akola Mandi"},
        "punjab": {"price": 6200, "unit": "per quintal", "trend": "stable", "best_market": "Sirsa Mandi"},
        "default": {"price": 6400, "unit": "per quintal", "trend": "stable", "best_market": "Local Mandi"}
    },
    "potato": {
        "uttar pradesh": {"price": 1200, "unit": "per quintal", "trend": "falling", "best_market": "Agra Mandi"},
        "gujarat": {"price": 1350, "unit": "per quintal", "trend": "stable", "best_market": "Deesa APMC"},
        "punjab": {"price": 1100, "unit": "per quintal", "trend": "falling", "best_market": "Jalandhar Mandi"},
        "default": {"price": 1200, "unit": "per quintal", "trend": "stable", "best_market": "Local Mandi"}
    }
}

def get_mandi_price(crop: str, state: str = "default") -> dict:
    """Get current mandi price for a crop in a state"""
    crop = crop.lower().strip()
    state = state.lower().strip()

    if crop not in MANDI_PRICES:
        available = ", ".join(MANDI_PRICES.keys())
        return {"error": f"Crop '{crop}' not found. Available: {available}"}

    crop_data = MANDI_PRICES[crop]
    price_info = crop_data.get(state, crop_data.get("default"))

    return {
        "crop": crop.title(),
        "state": state.title(),
        "price": price_info["price"],
        "unit": price_info["unit"],
        "trend": price_info["trend"],
        "best_market": price_info["best_market"],
        "advice": get_selling_advice(price_info["trend"])
    }

def get_selling_advice(trend: str) -> str:
    if trend == "rising":
        return "Price is rising — consider holding stock for 3-5 more days for better returns."
    elif trend == "falling":
        return "Price is falling — sell immediately to avoid further losses."
    else:
        return "Price is stable — good time to sell at current rates."

def get_all_prices(state: str = "default") -> str:
    """Get all crop prices for a state"""
    state = state.lower().strip()
    result = f"MANDI PRICES — {state.title() if state != 'default' else 'India Average'}\n\n"
    for crop in MANDI_PRICES:
        crop_data = MANDI_PRICES[crop]
        price_info = crop_data.get(state, crop_data.get("default"))
        trend_emoji = "📈" if price_info["trend"] == "rising" else "📉" if price_info["trend"] == "falling" else "➡️"
        result += f"{trend_emoji} {crop.title()}: ₹{price_info['price']} {price_info['unit']}\n"
    return result