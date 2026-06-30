# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# We will define a model instance that uses the GEMINI_API_KEY from environment variables
model = Gemini(
    model="gemini-2.5-flash",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# 1. weather_agent - handles weather and irrigation questions
weather_agent = Agent(
    name="weather_agent",
    description="Handles weather forecasts, seasonal climate conditions, and irrigation/watering questions.",
    model=model,
    instruction=(
        "You are the AgriGuard Weather and Irrigation Specialist. "
        "Answer questions about weather forecasts, seasonal climate, and irrigation advice (e.g., watering schedules, quantity) for crops. "
        "Provide helpful, practical information. "
        "If the user asks about crop diseases or market prices, or something else outside your domain, "
        "transfer back to orchestrator_agent."
    ),
)

# 2. crop_doctor_agent - diagnoses crop diseases from text descriptions
crop_doctor_agent = Agent(
    name="crop_doctor_agent",
    description="Diagnoses crop diseases from symptom descriptions and suggests treatments or preventions.",
    model=model,
    instruction=(
        "You are the AgriGuard Crop Doctor. "
        "Analyze text descriptions of crop symptoms (e.g., spots, wilting, mold, pests) to diagnose diseases. "
        "Suggest possible diagnoses, management tips, organic or chemical treatment recommendations, and preventive measures. "
        "If the user asks about weather, irrigation, or market prices, transfer back to orchestrator_agent."
    ),
)

# 3. market_agent - answers questions about crop market prices for India
market_agent = Agent(
    name="market_agent",
    description="Answers questions about crop market prices, market trends, and pricing information specifically in India.",
    model=model,
    instruction=(
        "You are the AgriGuard Crop Market Specialist specializing in the Indian agricultural market. "
        "Provide crop market prices in Indian Rupees (INR) for different states, districts, and mandis in India. "
        "Analyze market price trends in India and give appropriate buying/selling recommendations for Indian farmers. "
        "If the user asks about weather, irrigation, or crop diseases, transfer back to orchestrator_agent."
    ),
)

# 4. orchestrator_agent (root agent) - routes farmer queries to specialized sub-agents
orchestrator_agent = Agent(
    name="orchestrator_agent",
    description="Main entry point that routes farmer queries to specialized sub-agents.",
    model=model,
    instruction=(
        "You are the AgriGuard Orchestrator. Your role is to understand the farmer's query "
        "and delegate it to the appropriate specialized sub-agent: "
        "- Use `weather_agent` for weather forecasts, climate, or irrigation/watering questions. "
        "- Use `crop_doctor_agent` for diagnosing crop pests, diseases, or symptom analysis. "
        "- Use `market_agent` for crop prices, market trends, and sales questions. "
        "If the query is a general greeting or does not fit any specialized domain, answer it directly. "
        "Always transfer to the correct sub-agent if the request fits their domain."
    ),
    sub_agents=[weather_agent, crop_doctor_agent, market_agent],
)

# Keep root_agent pointing to orchestrator_agent to match import requirements in tests and runtime
root_agent = orchestrator_agent

app = App(
    root_agent=root_agent,
    name="app",
)
