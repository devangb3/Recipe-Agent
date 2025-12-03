# Recipe Agent Plan

## Goal
Deliver a Python recipe agent that talks in natural language, uses OpenRouter for LLM reasoning, and always pulls in at least one internal tool call to ground its answers (pantry ideation, scaling, nutrition hints, etc.).

## Stack
- Python runtime with `requests` (HTTP) and stdlib only.
- OpenRouter chat completions API (`https://openrouter.ai/api/v1/chat/completions`), model default `openai/gpt-4o-mini`.
- Secrets: `.env` with `OPENROUTER_API_KEY=` (user supplied).

## System Prompt (shape)
- Role: culinary copilot that prefers concise, practical recipes with substitutions.
- Output: plain text for users; tool results are merged into prose (no JSON).
- Safety: avoid unsafe cooking steps; be clear about allergens if called out.
- Behavioral nudge: call at least one tool before final reply; summarize what tools uncovered.

## Tooling Plan
- Tool registry in code; JSON Schema compatible with OpenAI/OpenRouter tool calling.
- Core tools (initial set):
  - `pantry_ideation`: turn user hints (ingredients, cuisine, diet, meal type, time, servings, skill) into a structured recipe draft with steps and shopping notes.
  - `scale_and_swap`: scale ingredient amounts and suggest substitutions for dietary/allergy needs.
  - `nutrition_estimate`: rough calorie/macro estimate from ingredient list; flags heavy salt/sugar.
- All tools are pure Python; results are fed back into the LLM as `tool` messages.

## Orchestration Flow
1. Build initial messages: system prompt → short policy reminder → user message.
2. Call OpenRouter with tool schemas (`tool_choice=auto`, retry forcing a tool if none are called).
3. Execute each requested tool locally; append tool outputs to the chat log.
4. Call OpenRouter again to draft the final user-facing answer that cites tool findings.
5. Return the assistant’s natural-language text (strip metadata).

## UX Targets
- Answers stay under 10 steps unless asked otherwise; include timing, servings, and swaps.
- When unsure, ask 1–2 clarifying questions instead of guessing.
- Keep formatting light: short headings, bullet ingredients, numbered steps.

## Deliverables
- Python entrypoint to run one-off prompts (CLI) plus modular agent package (client, tools, orchestration, utils).
- Document how to set the API key and run an example query.

## Quick Usage (post-implementation)
- Add `OPENROUTER_API_KEY=...` to `.env`.
- Run `python run_agent.py "Make me a fast vegan dinner with chickpeas and spinach"` (tools will be called automatically).
- Optional: `--model openai/gpt-4o-mini` to override model; `--no-force-tool` if you want to let the model skip tools.
