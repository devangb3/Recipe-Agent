from typing import Any, Dict, List, Optional

import requests

from recipe_agent.config import BASE_URL, DEFAULT_MODEL, TIMEOUT_SECONDS
from recipe_agent.logging_utils import get_logger

logger = get_logger(__name__)


class OpenRouterClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            # Let the model auto-select tools when provided
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        logger.info("Calling OpenRouter chat completions API")
        response = requests.post(
            BASE_URL, headers=headers, json=payload, timeout=TIMEOUT_SECONDS
        )
        if not response.ok:
            message = "Failed to parse error response"
            payload_data: Optional[Dict[str, Any]] = None
            try:
                payload_data = response.json()
                message = payload_data.get("error", {}).get("message", message)
            except ValueError:
                message = response.text or message
            raise RuntimeError(f"{response.status_code} {message}")

        data = response.json()
        # OpenAI / OpenRouter chat-completions style: choices[0].message
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("No choices returned from OpenRouter")
        message = choices[0].get("message") or {}
        # Normalise to at least have role/content keys
        return {
            "role": message.get("role", "assistant"),
            "content": message.get("content"),
            **({k: v for k, v in message.items() if k not in {"role", "content"}}),
        }
