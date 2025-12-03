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
            # Trigger connection to fail fast if invalid
            _CLIENT.server_info()
        except Exception as e:
            logger.warning(f"Could not connect to MongoDB at {uri}: {e}")
            # Return a mock or handle gracefully if needed, but for now let it raise or return None
            # Depending on requirements, we might want to suppress if local DB is optional.
            # But plan implies we should use it.
            return None
    return _CLIENT[db_name]


def seed_db_if_empty() -> None:
    db = get_db()
    if db is None:
        return

    collection = db.recipes
    if collection.count_documents({}) > 0:
        return

    logger.info("Seeding MongoDB with sample recipes...")
    sample_recipes = [
        {
            "title": "Classic Chicken Sandwich",
            "ingredients": [
                "2 chicken breast cutlets",
                "2 brioche buns",
                "2 tbsp mayonnaise",
                "1 tsp lemon juice",
                "lettuce",
                "tomato",
            ],
            "instructions": "Season chicken. Cook in skillet 3-4 mins per side. Toast buns. Assemble with mayo and veggies.",
            "tags": ["chicken", "sandwich", "lunch", "quick"],
            "time_minutes": 20,
        },
        {
            "title": "Spaghetti Aglio e Olio",
            "ingredients": [
                "1 lb spaghetti",
                "6 cloves garlic, sliced",
                "1/2 cup olive oil",
                "1 tsp red pepper flakes",
                "parsley",
            ],
            "instructions": "Boil pasta. Sauté garlic in oil until golden. Add pepper flakes. Toss pasta with oil and pasta water.",
            "tags": ["pasta", "italian", "vegetarian", "dinner"],
            "time_minutes": 15,
        },
        {
            "title": "Simple Garden Salad",
            "ingredients": [
                "mixed greens",
                "cucumber",
                "cherry tomatoes",
                "olive oil",
                "balsamic vinegar",
            ],
            "instructions": "Chop veggies. Toss with greens. Dress with oil and vinegar.",
            "tags": ["salad", "vegetarian", "vegan", "healthy", "side"],
            "time_minutes": 10,
        },
        {
            "title": "Beef Tacos",
            "ingredients": [
                "1 lb ground beef",
                "1 packet taco seasoning",
                "8 corn tortillas",
                "lettuce",
                "cheese",
                "salsa",
            ],
            "instructions": "Brown beef. Add seasoning and water. Simmer. Warm tortillas. Fill with beef and toppings.",
            "tags": ["mexican", "beef", "dinner", "tacos"],
            "time_minutes": 25,
        },
        {
            "title": "Vegetable Stir Fry",
            "ingredients": [
                "broccoli",
                "carrots",
                "bell peppers",
                "soy sauce",
                "ginger",
                "garlic",
                "tofu (optional)",
            ],
            "instructions": "Stir fry veggies in hot oil. Add aromatics. Sauce with soy, ginger, garlic. Serve over rice.",
            "tags": ["asian", "stir fry", "vegetarian", "vegan", "dinner"],
            "time_minutes": 20,
        },
    ]
    collection.insert_many(sample_recipes)
    # Create text index for searching
    collection.create_index([("title", pymongo.TEXT), ("tags", pymongo.TEXT)])


def search_recipes_mongo(
    query: str,
    cuisine: Optional[str] = None,
    diet: Optional[str] = None,
    time_limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    db = get_db()
    if db is None:
        return []

    collection = db.recipes
    mongo_query: Dict[str, Any] = {}

    # Text search on title/tags
    if query:
        # Simple regex for partial match if text index doesn't catch everything or for flexibility
        # Using regex for simplicity in this demo context
        mongo_query["$or"] = [
            {"title": {"$regex": query, "$options": "i"}},
            {"tags": {"$regex": query, "$options": "i"}},
        ]

    if cuisine:
        mongo_query["tags"] = {"$regex": cuisine, "$options": "i"}

    if time_limit:
        mongo_query["time_minutes"] = {"$lte": time_limit}
    
    # Note: 'diet' is often subjective or requires checking ingredients/tags. 
    # For this simple schema, we check tags.
    if diet:
        mongo_query["tags"] = {"$regex": diet, "$options": "i"}

    cursor = collection.find(mongo_query, {"_id": 0}).limit(5)
    return list(cursor)

