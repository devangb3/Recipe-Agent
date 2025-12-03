import logging
import re
from typing import Any, Dict, List, Optional

import pymongo
from pymongo import MongoClient

from recipe_agent.utils import get_mongo_config

logger = logging.getLogger(__name__)

_CLIENT: Optional[MongoClient] = None


def get_db() -> Any:
    global _CLIENT
    uri, db_name = get_mongo_config()
    if _CLIENT is None:
        try:
            _CLIENT = MongoClient(uri, serverSelectionTimeoutMS=2000)
            _CLIENT.server_info()
        except Exception as e:
            logger.warning(f"Could not connect to MongoDB at {uri}: {e}")
            return None
    return _CLIENT[db_name]


def search_recipes_mongo(
    query: str,
    cuisine: Optional[str] = None,
    diet: Optional[str] = None,
) -> List[Dict[str, Any]]:
    db = get_db()
    if db is None:
        return []

    collection = db.recipes
    conditions = []

    # Text search on title, ingredients, and instructions
    if query:
        conditions.append({
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"ingredients": {"$regex": query, "$options": "i"}},  # Searches within array elements
                {"instructions": {"$regex": query, "$options": "i"}},
            ]
        })

    # For cuisine, search in ingredients/instructions since tags don't exist in Kaggle data
    if cuisine:
        conditions.append({
            "$or": [
                {"ingredients": {"$regex": cuisine, "$options": "i"}},
                {"instructions": {"$regex": cuisine, "$options": "i"}},
            ]
        })
    
    # For diet, search in ingredients/instructions
    if diet:
        conditions.append({
            "$or": [
                {"ingredients": {"$regex": diet, "$options": "i"}},
                {"instructions": {"$regex": diet, "$options": "i"}},
            ]
        })

    # Build final query
    mongo_query: Dict[str, Any] = {}
    if len(conditions) == 1:
        mongo_query = conditions[0]
    elif len(conditions) > 1:
        mongo_query = {"$and": conditions}

    cursor = collection.find(mongo_query, {"_id": 0}).limit(5)
    return list(cursor)