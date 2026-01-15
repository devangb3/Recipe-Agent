import sys
from typing import Optional

from recipe_agent.agent import RecipeAgent
from recipe_agent.client import OpenRouterClient
from recipe_agent.config import DEFAULT_MODEL, SYSTEM_MESSAGES
from recipe_agent.utils import load_api_key
from recipe_agent.logging_utils import setup_logging


def run_agent(
    prompt: str,
    api_key: Optional[str],
) -> str:
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY. Add it to .env or your environment before running.")

    client = OpenRouterClient(api_key=api_key, model=DEFAULT_MODEL)
    agent = RecipeAgent(client)
    system_prompt = SYSTEM_MESSAGES[0]["content"]
    result = agent.run(prompt, system_prompt)

    reply = result["reply"]
    trace = result["trace"]

    output_lines = [reply]
    if trace:
        output_lines.append("\n--- tool trace ---")
        output_lines.extend(trace)
    return "\n".join(output_lines)

def main() -> None:
    setup_logging()
    api_key = load_api_key()
    prompt = "Give recipe for a coffee cake and the nutrtional breakdown for 200 grams of the cake"
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    print(run_agent(prompt, api_key))

if __name__ == "__main__":
    main()
