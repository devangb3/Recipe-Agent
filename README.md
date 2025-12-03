# Recipe Agent Setup

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
OPENROUTER_API_KEY=your_openrouter_key
USDA_API_KEY=your_usda_api_key
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=recipe_agent
```

## Dependencies

Ensure you have the necessary Python packages installed:
- `pymongo`
- `requests`

## Database Setup

For  use, populate the database:

### Import from Kaggle Dataset (Recommended - 2M+ recipes)

```bash
# Import first 1000 recipes from Kaggle dataset
python scripts/import_kaggle.py --count 1000

# Import more recipes (e.g., 10000)
python scripts/import_kaggle.py --count 10000 --batch-size 1000
```

**Note:** First run will download ~635MB dataset from Kaggle (one-time download).

## Run as an API service

1) Install deps: `pip install -r requirements.txt`

2) Export environment:
```
OPENROUTER_API_KEY=...
# optional
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=recipe_agent
USDA_API_KEY=...
PORT=4581
```

3) Start the server:
```
python -m recipe_agent.server
# or
uvicorn recipe_agent.server:app --host 0.0.0.0 --port 4581
```

4) Test:

### Example request body (system + user message)

`server.py` exposes a `/responses` endpoint that expects an OpenRouter **Responses-style** payload.  
Here is a minimal example including both a system and a user message:

```json
{
  "model": "openai/gpt-4o-mini",
  "input": [
    {
      "type": "message",
      "role": "system",
      "content": [
        {
          "type": "input_text",
          "text": "You are a helpful culinary assistant. Answer concisely."
        }
      ]
    },
    {
      "type": "message",
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": "Suggest a 20-minute vegetarian pasta recipe."
        }
      ]
    }
  ]
}
```

### Example curl call to `server.py`

```bash
curl -X POST http://localhost:4581/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-4o-mini",
    "input": [
      {
        "type": "message",
        "role": "system",
        "content": [
          {
            "type": "input_text",
            "text": "You are a helpful culinary assistant. Answer concisely."
          }
        ]
      },
      {
        "type": "message",
        "role": "user",
        "content": [
          {
            "type": "input_text",
            "text": "Suggest a 20-minute vegetarian pasta recipe."
          }
        ]
      }
    ]
  }'
```

`/health` returns `{"status":"ok"}` for readiness checks. The API accepts an optional `model` field to override the default model per-request.

## Logging
- Logs are written to `logs/recipe_agent.log` and also printed to stdout.
- Logging is initialized in the server and CLI entrypoints; adjust `setup_logging` in `recipe_agent/logging_utils.py` if you need different paths or levels.
