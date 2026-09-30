import httpx
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from app.db.session import SessionLocal, init_db_extensions
from app.db.models import Base, RegulatoryRecord
from app.db.session import engine

TARGET_SUBSTANCES = [
    "caffeine",
    "theanine",
    "vanillin",
    "xanthan gum",
    "citric acid",
    "aspartame",
    "sucralose",
    "potassium sorbate",
    "sodium benzoate",
    "erythritol",
    "matcha",
    "curcumin",
]

OPENFDA_SUBSTANCE_URL = "https://api.fda.gov/food/substance.json"

def fetch_substance_data(substance_name: str) -> dict | None:
    """Fetch substance classification and regulation details from the OpenFDA API."""
    params = {
        "search": f'substance_name:"{substance_name}"',
        "limit": 1
    }
    try:
        response = httpx.get(OPENFDA_SUBSTANCE_URL, params=params, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                return results[0]
        elif response.status_code != 404:
            print(f"  Warning: Received HTTP {response.status_code} for '{substance_name}'")
    except Exception as e:
        print(f" Error fetching OpenFDA data for '{substance_name}': {e}")
    return None