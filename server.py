import os
import uuid
from typing import Any, Dict, Optional, Sequence

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from recipe_agent.agent import RecipeAgent
from recipe_agent.client import OpenRouterClient
from recipe_agent.config import DEFAULT_MODEL, SYSTEM_MESSAGES
from recipe_agent.logging_utils import get_logger, setup_logging
from recipe_agent.utils import load_api_key

setup_logging()
logger = get_logger(__name__)
app = FastAPI(title="Recipe Agent", version="0.1.0")


class ChatRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    trace: list[str]
    model: str


def _build_agent(model: Optional[str]) -> RecipeAgent:
    api_key = load_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="Missing OPENROUTER_API_KEY")
    client = OpenRouterClient(api_key=api_key, model=model or DEFAULT_MODEL)
    return RecipeAgent(client)


def _extract_text_from_content(content: Sequence[Dict[str, Any]]) -> str:
    parts: list[str] = []
    for entry in content or []:
        text = entry.get("text")
        if text:
            parts.append(str(text))
    return "\n".join(parts)


def _extract_messages(messages: Sequence[Dict[str, Any]]) -> tuple[str, str]:
    system_text = ""
    user_text = ""
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content") or []
        text = _extract_text_from_content(content)
        if role == "system" and not system_text:
            system_text = text
        elif role == "user" and not user_text:
            user_text = text
    return system_text, user_text


def _format_responses_reply(reply: str, model: str) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "object": "response",
        "model": model,
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": reply}],
            }
        ],
        "usage": {
            "input_tokens": 0,
            "output_tokens": len(reply.split()),
            "total_tokens": len(reply.split()),
        },
        "status": "completed",
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/responses")
def responses(payload: Dict[str, Any]) -> Dict[str, Any]:

    logger.info("Received /responses request")
    model = payload.get("model") or DEFAULT_MODEL
    messages = payload.get("input") or []
    system_prompt, user_prompt = _extract_messages(messages)
    if not system_prompt:
        system_prompt = SYSTEM_MESSAGES[0]["content"]

    agent = _build_agent(model)
    try:
        result = agent.run(user_prompt, system_prompt)
    except Exception as exc:
        logger.exception("Agent error")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    reply = result.get("reply", "[no reply]")
    return _format_responses_reply(reply, model)


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    port = 4581 # default port
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
