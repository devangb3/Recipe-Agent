import requests
from typing import Any, Dict, Optional
from recipe_agent.utils import load_usda_key, as_number

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

def get_api_key() -> Optional[str]:
    return load_usda_key()

def search_food(query: str) -> Optional[int]:
    """Search for a food item and return its FDC ID."""
    api_key = get_api_key()
    if not api_key:
        return None
    
    params = {
        "api_key": api_key,
        "query": query,
        "pageSize": 1,
        "dataType": ["Foundation", "Survey (FNDDS)"] 
    }
    try:
        resp = requests.get(f"{USDA_BASE_URL}/foods/search", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        foods = data.get("foods", [])
        if foods:
            return foods[0]["fdcId"]
    except Exception:
        return None
    return None

def get_food_nutrients(fdc_id: int) -> Dict[str, float]:
    """Get calories, protein, fat, carbs for a given FDC ID (per 100g usually)."""
    api_key = get_api_key()
    if not api_key:
        return {}

    try:
        resp = requests.get(f"{USDA_BASE_URL}/food/{fdc_id}", params={"api_key": api_key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    nutrients = {}
    # Standard USDA nutrient IDs
    # 208/1008 = Energy (kcal)
    # 203/1003 = Protein (g)
    # 204/1004 = Total Lipid (fat) (g)
    # 205/1005 = Carbohydrate (g)
    
    # Map USDA nutrient names/ids to our simple keys
    target_nutrients = {
        "Energy": "calories",
        "Protein": "protein",
        "Total lipid (fat)": "fat",
        "Carbohydrate, by difference": "carbs",
    }

    for nutrient in data.get("foodNutrients", []):
        name = nutrient.get("nutrient", {}).get("name") or nutrient.get("nutrientName")
        amount = nutrient.get("amount")
        
        if name in target_nutrients:
            nutrients[target_nutrients[name]] = amount
        
        # Fallback by checking IDs if names vary
        n_id = nutrient.get("nutrient", {}).get("id") or nutrient.get("nutrientId")
        if n_id in [1008, 208]: # Energy
             nutrients["calories"] = amount
        elif n_id in [1003, 203]: # Protein
             nutrients["protein"] = amount
        elif n_id in [1004, 204]: # Fat
             nutrients["fat"] = amount
        elif n_id in [1005, 205]: # Carbs
             nutrients["carbs"] = amount

    return nutrients

def fetch_nutrition_for_ingredient(name: str, quantity: float, unit: str) -> Dict[str, float]:
    """
    Fetch nutrition for an ingredient.
    USDA return values are typically per 100g.
    We need to convert user unit to grams.
    This is a simplified converter.
    """
    fdc_id = search_food(name)
    if not fdc_id:
        return {}

    # Get per 100g values
    per_100g = get_food_nutrients(fdc_id)
    if not per_100g:
        return {}

    # Simple unit conversion to grams
    # This is VERY rough. Real apps need a robust density/unit DB.
    grams = 0.0
    unit = unit.lower().strip()
    
    if unit in ["g", "gram", "grams"]:
        grams = quantity
    elif unit in ["kg", "kilogram"]:
        grams = quantity * 1000
    elif unit in ["oz", "ounce", "ounces"]:
        grams = quantity * 28.35
    elif unit in ["lb", "pound", "pounds"]:
        grams = quantity * 453.59
    elif unit in ["cup", "cups"]:
        grams = quantity * 200 # Rough average for many solids/liquids
    elif unit in ["tbsp", "tablespoon"]:
        grams = quantity * 15
    elif unit in ["tsp", "teaspoon"]:
        grams = quantity * 5
    else:
        # Default assumption: if unit unknown/missing, assume ~100g portion or 'each' ~100g
        grams = quantity * 100 

    ratio = grams / 100.0
    
    return {
        "calories": round(per_100g.get("calories", 0) * ratio, 1),
        "protein": round(per_100g.get("protein", 0) * ratio, 1),
        "fat": round(per_100g.get("fat", 0) * ratio, 1),
        "carbs": round(per_100g.get("carbs", 0) * ratio, 1),
    }

