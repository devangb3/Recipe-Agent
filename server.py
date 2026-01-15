import uuid
from typing import Any, Dict, Optional, Sequence

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from recipe_agent.agent import RecipeAgent
from recipe_agent.client import OpenRouterClient
from recipe_agent.config import DEFAULT_MODEL, SYSTEM_MESSAGES
from recipe_agent.logging_utils import get_logger, setup_logging
from recipe_agent.tools import build_tools
from recipe_agent.utils import load_api_key

setup_logging()
logger = get_logger(__name__)
app = FastAPI(title="Recipe Agent", version="0.1.0")
TOOLS = build_tools()


class ChatRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    trace: list[str]
    model: str


class ToolExecutionRequest(BaseModel):
    tool_call_id: Optional[str] = None
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


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

@app.get("/tools/health")
def tools_health() -> Dict[str, str]:
    return {"status": "ok"}

@app.get("/tools")
def list_tools() -> Dict[str, Any]:
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            }
            for tool in TOOLS.values()
        ]
    }

@app.post("/tools")
def execute_tool(payload: ToolExecutionRequest) -> Dict[str, Any]:
    tool = TOOLS.get(payload.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {payload.tool_name}")

    try:
        result = tool.handler(payload.arguments or {})
    except Exception as exc:
        logger.exception("Tool execution failed: %s", payload.tool_name)
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed for {payload.tool_name}: {exc}",
        ) from exc

    return {
        "tool_call_id": payload.tool_call_id,
        "tool_name": payload.tool_name,
        "result": result,
    }


@app.post("/responses")
def responses(payload: Dict[str, Any]) -> Dict[str, Any]:

    logger.info("Received request")
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

    if result.get("trace"):
        logger.info("Trace: %s", result["trace"])

    reply = result.get("reply", "[no reply]")
    return _format_responses_reply(reply, model)


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    port = 4581 # default port
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
