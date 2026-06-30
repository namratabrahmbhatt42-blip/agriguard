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

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from google.adk.events.event import Event
from google.genai import types

from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_chat_endpoint_success() -> None:
    """
    Test the FastAPI /chat endpoint by mocking the ADK runner execution.
    """
    mock_event = Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="This is a mock response from the agent.")]
        )
    )
    
    async def mock_run_async(*args, **kwargs):
        yield mock_event

    with patch("app.main.runner.run_async", side_effect=mock_run_async) as mock_run:
        response = client.post("/chat", json={"message": "What is the price of wheat in India?"})
        
        assert response.status_code == 200
        assert response.json() == {"response": "This is a mock response from the agent."}
        mock_run.assert_called_once()


def test_chat_endpoint_empty_message() -> None:
    """
    Test the FastAPI /chat endpoint validation for empty messages.
    """
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 400
    assert "Message cannot be empty" in response.json()["detail"]


def test_get_root_html() -> None:
    """
    Test that the root endpoint returns the HTML chat UI successfully.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AgriGuard" in response.text
