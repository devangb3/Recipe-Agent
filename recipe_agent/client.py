from typing import Any, Dict, List, Optional

import requests

from recipe_agent.config import BASE_URL, DEFAULT_MODEL, TIMEOUT_SECONDS


class OpenRouterClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = "auto",
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
        if tools and tool_choice is not None:
            payload["tool_choice"] = tool_choice

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Recipe Agent",
        }
        response = requests.post(
            BASE_URL, headers=headers, json=payload, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        data = response.json()
        if "choices" not in data or not data["choices"]:
            raise RuntimeError("OpenRouter response missing choices")
        return data["choices"][0]["message"]
