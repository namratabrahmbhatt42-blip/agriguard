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
from app.agent import root_agent, weather_agent, crop_doctor_agent, market_agent

def test_orchestrator_agent_structure() -> None:
    """
    Unit test to verify the structure and routing setup of the Orchestrator Agent.
    """
    assert root_agent is not None
    assert root_agent.name == "orchestrator_agent"
    assert "routes" in root_agent.description.lower() or "orchestrator" in root_agent.description.lower()
    
    # Check that orchestrator has the 3 specified specialized sub-agents
    assert len(root_agent.sub_agents) == 3
    sub_agent_names = [agent.name for agent in root_agent.sub_agents]
    assert "weather_agent" in sub_agent_names
    assert "crop_doctor_agent" in sub_agent_names
    assert "market_agent" in sub_agent_names


def test_specialized_agents_configuration() -> None:
    """
    Unit test to verify the configuration of individual specialized agents.
    """
    # Weather Agent
    assert weather_agent.name == "weather_agent"
    assert "weather" in weather_agent.description.lower() or "irrigation" in weather_agent.description.lower()
    
    # Crop Doctor Agent
    assert crop_doctor_agent.name == "crop_doctor_agent"
    assert "diagnoses" in crop_doctor_agent.description.lower() or "crop disease" in crop_doctor_agent.description.lower()
    
    # Market Agent
    assert market_agent.name == "market_agent"
    assert "india" in market_agent.description.lower()
    assert "market" in market_agent.description.lower() or "price" in market_agent.description.lower()
