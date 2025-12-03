import os
import random
from pathlib import Path
from typing import Any, List, Optional


def load_env_vars() -> None:
    """Load all environment variables from .env without extra deps."""
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            key = name.strip()
            val = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


def load_api_key() -> Optional[str]:
    """Read OPENROUTER_API_KEY from environment or .env."""
    load_env_vars()
    return os.getenv("OPENROUTER_API_KEY")


def load_usda_key() -> Optional[str]:
    """Read USDA_API_KEY from environment."""
    load_env_vars()
    return os.getenv("USDA_API_KEY")


def get_mongo_config() -> tuple[str, str]:
    """Get MONGO_URI and MONGO_DB_NAME."""
    load_env_vars()
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    db_name = os.getenv("MONGO_DB_NAME", "recipe_agent")
    return uri, db_name


def as_number(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def normalize_ingredient_name(name: str) -> str:
    return name.strip().lower()


def short_round(value: float) -> float:
    if value.is_integer():
        return int(value)
    return round(value, 2)


def pick_label(options: List[str], fallback: str) -> str:
    clean = [o for o in options if o]
    if not clean:
        return fallback
    return random.choice(clean)
