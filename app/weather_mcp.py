import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5"

def get_current_weather(city: str) -> dict:
    """Get current weather for any Indian city"""
    try:
        url = f"{BASE_URL}/weather"
        params = {
            "q": f"{city},IN",
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return {"error": f"City not found: {city}"}

        return {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
            "visibility": data.get("visibility", 0) / 1000
        }
    except Exception as e:
        return {"error": str(e)}


def get_3day_forecast(city: str) -> dict:
    """Get 3-day weather forecast for any Indian city"""
    try:
        url = f"{BASE_URL}/forecast"
        params = {
            "q": f"{city},IN",
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "cnt": 24
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return {"error": f"City not found: {city}"}

        # Group by day
        days = {}
        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]
            if date not in days:
                days[date] = {
                    "date": date,
                    "min_temp": item["main"]["temp_min"],
                    "max_temp": item["main"]["temp_max"],
                    "condition": item["weather"][0]["description"],
                    "humidity": item["main"]["humidity"],
                    "rain_chance": item.get("pop", 0) * 100
                }
            else:
                days[date]["min_temp"] = min(days[date]["min_temp"], item["main"]["temp_min"])
                days[date]["max_temp"] = max(days[date]["max_temp"], item["main"]["temp_max"])
                days[date]["rain_chance"] = max(days[date]["rain_chance"], item.get("pop", 0) * 100)

        forecast_list = list(days.values())[:3]
        return {"city": city, "forecast": forecast_list}

    except Exception as e:
        return {"error": str(e)}


def get_farming_weather_advice(city: str) -> str:
    """Get weather + farming advice combined"""
    current = get_current_weather(city)
    forecast = get_3day_forecast(city)

    if "error" in current:
        return f"Could not fetch weather for {city}. Please check city name."

    advice = []

    # Temperature advice
    temp = current["temperature"]
    if temp > 40:
        advice.append("Very high temperature — irrigate crops early morning or evening only.")
    elif temp > 35:
        advice.append("High temperature — increase irrigation frequency.")
    elif temp < 10:
        advice.append("Low temperature — protect sensitive crops from frost.")

    # Humidity advice
    humidity = current["humidity"]
    if humidity > 80:
        advice.append("High humidity — watch for fungal diseases on crops.")
    elif humidity < 30:
        advice.append("Low humidity — crops may need extra watering.")

    # Rain forecast advice
    if "forecast" in forecast:
        for day in forecast["forecast"]:
            if day["rain_chance"] > 70:
                advice.append(f"High chance of rain on {day['date']} ({day['rain_chance']:.0f}%) — delay fertilizer application.")
                break
            elif day["rain_chance"] > 40:
                advice.append(f"Moderate rain expected on {day['date']} — plan irrigation accordingly.")
                break

    advice_text = " ".join(advice) if advice else "Weather conditions are suitable for farming."

    result = f"""
CURRENT WEATHER — {current['city']}
Temperature: {current['temperature']}°C (feels like {current['feels_like']}°C)
Condition: {current['condition'].title()}
Humidity: {current['humidity']}%
Wind: {current['wind_speed']} m/s

3-DAY FORECAST:
"""
    if "forecast" in forecast:
        for day in forecast["forecast"]:
            result += f"• {day['date']}: {day['min_temp']:.0f}°C - {day['max_temp']:.0f}°C, {day['condition'].title()}, Rain chance: {day['rain_chance']:.0f}%\n"

    result += f"\nFARMING ADVICE:\n{advice_text}"
    return result