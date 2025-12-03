import sys
from typing import Optional

from recipe_agent.agent import RecipeAgent
from recipe_agent.client import OpenRouterClient
from recipe_agent.config import DEFAULT_MODEL
from recipe_agent.utils import load_api_key


def run_agent(
    prompt: str,
    api_key: Optional[str],
) -> str:
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY. Add it to .env or your environment before running.")

    client = OpenRouterClient(api_key=api_key, model=DEFAULT_MODEL)
    agent = RecipeAgent(client)
    result = agent.run(prompt)

    reply = result["reply"]
    trace = result["trace"]

    output_lines = [reply]
    if trace:
        output_lines.append("\n--- tool trace ---")
        output_lines.extend(trace)
    return "\n".join(output_lines)


def main() -> None:
    api_key = load_api_key()
    prompt = "Chicken Sandwich recipe under 30 minutes"
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    try:
        output = run_agent(
            prompt=prompt,
            api_key=api_key,
        )
    except RuntimeError as err:
        sys.exit(str(err))

    print(output)

if __name__ == "__main__":
    main()
