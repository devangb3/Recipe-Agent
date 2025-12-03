from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from recipe_agent.db import search_recipes_mongo
from recipe_agent.usda import fetch_nutrition_for_ingredient
from recipe_agent.utils import as_number, short_round
from recipe_agent.logging_utils import get_logger
ToolHandler = Callable[[Dict[str, Any]], Any]

logger = get_logger(__name__)

@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: ToolHandler

    def as_openai_tool(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

def build_tools() -> Dict[str, Tool]:
    
    return {
        "search_local_recipes": Tool(
            name="search_local_recipes",
            description="Search for recipes in the local database.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords for recipe title.",
                    },
                    "cuisine": {
                        "type": "string",
                        "description": "Filter by cuisine (e.g. Italian, Mexican).",
                    },
                    "diet": {
                        "type": "string",
                        "description": "Filter by diet (e.g. vegetarian, vegan).",
                    },
                },
            },
            handler=_tool_search_local_recipes,
        ),
        
        "calculate_recipe_nutrition": Tool(
            name="calculate_recipe_nutrition",
            description="Calculate total nutrition for a recipe using USDA data.",
            parameters={
                "type": "object",
                "properties": {
                    "ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                            },
                            "required": ["name", "quantity"],
                        },
                    },
                    "servings": {
                        "type": "integer",
                        "description": "Number of servings.",
                    },
                },
                "required": ["ingredients"],
            },
            handler=_tool_calculate_recipe_nutrition,
        ),
        "scale_recipe": Tool(
            name="scale_recipe",
            description="Scale ingredient quantities mathematically.",
            parameters={
                "type": "object",
                "properties": {
                    "ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"},
                                "notes": {"type": "string"},
                            },
                        },
                    },
                    "base_servings": {"type": "integer"},
                    "target_servings": {"type": "integer"},
                },
                "required": ["ingredients", "base_servings", "target_servings"],
            },
            handler=_tool_scale_recipe,
        ),
    }

def _tool_search_local_recipes(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    logger.info("Searching local recipes")
    query = args.get("query") or ""
    cuisine = args.get("cuisine")
    diet = args.get("diet")
    return search_recipes_mongo(query, cuisine, diet)

def _tool_calculate_recipe_nutrition(args: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Calculating recipe nutrition")
    ingredients = args.get("ingredients") or []
    servings = args.get("servings") or 1
    
    total_stats = {"calories": 0.0, "protein": 0.0, "fat": 0.0, "carbs": 0.0}
    
    for item in ingredients:
        name = item.get("name") or ""
        qty = as_number(item.get("quantity")) or 0.0
        unit = item.get("unit") or ""
        
        # Use USDA lookup
        stats = fetch_nutrition_for_ingredient(name, qty, unit)
        for k in total_stats:
            total_stats[k] += stats.get(k, 0.0)
            
    # Round totals
    for k in total_stats:
        total_stats[k] = round(total_stats[k], 1)
        
    per_serving = {k: round(v / servings, 1) for k, v in total_stats.items()} if servings else total_stats
    
    return {
        "total_nutrition": total_stats,
        "per_serving_nutrition": per_serving,
        "servings": servings
    }

def _tool_scale_recipe(args: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Scaling recipe")
    base_servings = args.get("base_servings") or 2
    target_servings = args.get("target_servings") or base_servings
    ingredients = args.get("ingredients") or []
    
    scale_factor = target_servings / base_servings if base_servings else 1
    scaled_ingredients = []
    
    for item in ingredients:
        name = item.get("name") or ""
        qty = as_number(item.get("quantity"))
        unit = item.get("unit") or ""
        notes = item.get("notes") or ""
        
        new_qty = short_round(qty * scale_factor) if qty is not None else None
        
        scaled_ingredients.append({
            "name": name,
            "quantity": new_qty if new_qty is not None else item.get("quantity"),
            "unit": unit,
            "notes": notes
        })
        
    return {
        "base_servings": base_servings,
        "target_servings": target_servings,
        "scale_factor": round(scale_factor, 2),
        "ingredients": scaled_ingredients
    }

