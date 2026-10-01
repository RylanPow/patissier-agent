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

def parse_openfda_record(query_term: str, data: dict | None) -> dict:
    """Transform raw OpenFDA payload into our RegulatoryRecord schema."""
    agency = "FDA"
    
    if not data:
        # default fallback for traditional botanical/food ingredients not registered as synthetic additives
        return {
            "ingredient_name": query_term.capitalize(),
            "agency": agency,
            "status": "GRAS (Traditional/Pending Notice)",
            "limitations": "Common food substance; verify specific supplier GRN or cGMP usage limits.",
            "effective_date": datetime.utcnow()
        }

    # extract official substance name or fall back to query term
    substance_name = data.get("substance_name", query_term).capitalize()
    
    # extract regulatory status details
    classes = data.get("substance_classification", [])
    status = "GRAS / Regulated Additive" if classes else "Registered Food Substance"
    if any("BANNED" in c.upper() or "REVOKED" in c.upper() for c in classes):
        status = "Banned"

    #assemble limitations and technical usages
    technical_effects = data.get("technical_effects", [])
    effects_str = ", ".join(technical_effects) if technical_effects else "General food use"
    
    citations = []
    for reg in data.get("regulations", []):
        cfr = reg.get("citation")
        if cfr:
            citations.append(cfr)
            
    citation_str = f" (CFR: {', '.join(citations)})" if citations else ""
    limitations = f"Approved technical uses: {effects_str}{citation_str}"

    return {
        "ingredient_name": substance_name,
        "agency": agency,
        "status": status,
        "limitations": limitations,
        "effective_date": datetime.utcnow()
    }