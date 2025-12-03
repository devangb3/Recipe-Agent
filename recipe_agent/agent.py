import json
from typing import Any, Dict, List, Optional

from recipe_agent.client import OpenRouterClient
from recipe_agent.config import DEFAULT_MODEL
from recipe_agent.tools import build_tools
from recipe_agent.logging_utils import get_logger


class RecipeAgent:
    def __init__(
        self,
        client: OpenRouterClient,
    ):
        self.client = client
        self.model = DEFAULT_MODEL
        self.tools = build_tools()
        self.logger = get_logger(__name__)

    def _tool_defs(self) -> List[Dict[str, Any]]:
        return [tool.as_openai_tool() for tool in self.tools.values()]

    def run(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        messages: List[Dict[str, Any]] = []

        sys_prompt = system_prompt or ""
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_prompt})

        tool_defs = self._tool_defs()
        trace: List[str] = []

        message = self.client.chat(messages, tools=tool_defs)
        messages.append(message)

        max_iterations = 5
        iterations = 0

        while message.get("tool_calls") and iterations < max_iterations:
            iterations += 1
            
            for call in message["tool_calls"]:
                tool_name = call["function"]["name"]
                raw_args = call["function"].get("arguments") or "{}"
                
                try:
                    parsed_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    parsed_args = {}

                handler = self.tools.get(tool_name)
                if not handler:
                    tool_content = f"Tool {tool_name} not implemented."
                    trace.append(f"Error: {tool_content}")
                else:
                    try:
                        tool_result = handler.handler(parsed_args)
                        tool_content = json.dumps(tool_result, ensure_ascii=False)
                        trace.append(f"{tool_name} -> {tool_content}")
                    except Exception as exc:
                        tool_content = f"Error executing {tool_name}: {exc}"
                        trace.append(tool_content)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": tool_name,
                        "content": tool_content,
                    }
                )

            message = self.client.chat(messages, tools=tool_defs)
            messages.append(message)

        final_content = message.get("content") or "[No content returned]"
        return {"reply": final_content, "trace": trace, "messages": messages}
