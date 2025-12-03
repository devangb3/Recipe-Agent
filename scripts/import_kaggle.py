import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import kagglehub
from kagglehub import KaggleDatasetAdapter
import pandas as pd

from recipe_agent.db import get_db
from recipe_agent.utils import load_env_vars

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_json_string(s: str) -> List[str]:
    if not s or pd.isna(s):
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return parsed
        return [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        return []


def normalize_recipe(row: Dict[str, Any]) -> Dict[str, Any]:
    title = str(row.get("title", "")).strip()
    if not title:
        return None
    
    # Parse ingredients (JSON string array)
    ingredients_raw = row.get("ingredients", "")
    ingredients = parse_json_string(ingredients_raw) if isinstance(ingredients_raw, str) else []
    
    # Parse directions (JSON string array) and join into instructions
    directions_raw = row.get("directions", "")
    directions = parse_json_string(directions_raw) if isinstance(directions_raw, str) else []
    instructions = "\n".join(directions) if directions else ""
    
    return {
        "title": title,
        "ingredients": ingredients,
        "instructions": instructions
    }


def import_from_kaggle(count: int = 1000, batch_size: int = 1000) -> int:
    load_env_vars()
    
    db = get_db()
    if db is None:
        logger.error("Cannot connect to MongoDB. Check MONGO_URI in .env")
        return 0

    collection = db.recipes
    logger.info(f"Starting import of {count} recipes from Kaggle dataset...")
    
    try:
        handle = "wilmerarltstrmberg/recipe-dataset-over-2m"
        file_path = "recipes_data.csv"
        
        logger.info("Loading dataset from Kaggle")
        df = kagglehub.dataset_load(
            KaggleDatasetAdapter.PANDAS,
            handle,
            file_path,
            pandas_kwargs={"nrows": count}
        )
        
        logger.info(f"Loaded {len(df)} rows from dataset")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        
        recipes_to_insert = []
        imported = 0
        
        for _, row in df.iterrows():
            recipe = normalize_recipe(row.to_dict())
            if recipe and recipe["title"]:
                recipes_to_insert.append(recipe)
                
                if len(recipes_to_insert) >= batch_size:
                    try:
                        collection.insert_many(recipes_to_insert)
                        imported += len(recipes_to_insert)
                        logger.info(f"Imported batch: {imported} recipes so far...")
                        recipes_to_insert = []
                    except Exception as e:
                        logger.error(f"Error inserting batch: {e}")
                        recipes_to_insert = []
        
        if recipes_to_insert:
            try:
                collection.insert_many(recipes_to_insert)
                imported += len(recipes_to_insert)
            except Exception as e:
                logger.error(f"Error inserting final batch: {e}")
        
        logger.info(f"\nSuccessfully imported {imported} recipes!")
        return imported
        
    except Exception as e:
        logger.error(f"Error importing from Kaggle: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    parser = argparse.ArgumentParser(description="Import recipes from Kaggle dataset")
    parser.add_argument("--count", type=int, default=1000, 
                       help="Number of recipes to import (default: 1000)")
    parser.add_argument("--batch-size", type=int, default=1000,
                       help="Batch size for MongoDB inserts (default: 1000)")
    
    args = parser.parse_args()
    
    imported = import_from_kaggle(count=args.count, batch_size=args.batch_size)
    
    if imported > 0:
        db = get_db()
        
        total = db.recipes.count_documents({})
        logger.info(f"\nTotal recipes in database: {total}")
    
    sys.exit(0 if imported > 0 else 1)


if __name__ == "__main__":
    main()

