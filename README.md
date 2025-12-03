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
