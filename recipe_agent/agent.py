import json
from typing import Any, Dict, List

from recipe_agent.client import OpenRouterClient
from recipe_agent.config import DEFAULT_MODEL, SYSTEM_MESSAGES
from recipe_agent.tools import build_tools


class RecipeAgent:
    def __init__(
        self,
        client: OpenRouterClient,
    ):
        self.client = client
        self.model = DEFAULT_MODEL
        self.tools = build_tools()
        self.system_messages = SYSTEM_MESSAGES

    def _tool_defs(self) -> List[Dict[str, Any]]:
        return [tool.as_openai_tool() for tool in self.tools.values()]

    def run(
        self,
        user_prompt: str,
    ) -> Dict[str, Any]:
        # Reset messages for single turn statelessness
        messages: List[Dict[str, Any]] = list(self.system_messages)
        messages.append({"role": "user", "content": user_prompt})

        tool_defs = self._tool_defs()
        trace: List[str] = []

        message = self.client.chat(messages, tools=tool_defs, tool_choice="auto")
        messages.append(message)

        # Tool execution loop (ReAct)
        # Limit iterations to avoid infinite loops
        max_iterations = 5
        iterations = 0

        while message.get("tool_calls") and iterations < max_iterations:
            iterations += 1
            
            # Process all tool calls in parallel
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

            # Call LLM again with tool outputs
            message = self.client.chat(messages, tools=tool_defs, tool_choice="auto")
            messages.append(message)

        final_content = message.get("content") or "[No content returned]"
        return {"reply": final_content, "trace": trace, "messages": messages}
