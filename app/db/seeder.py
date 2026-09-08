from sqlalchemy import Select
from sqlalchemy.dialects.postgresql import insert
from app.db.session import engine, SessionLocal, init_db_extensions
from app.db.models import Base, Trend, KnowledgeDocument
from app.agent.embeddings import embedding_engine

MOCK_TRENDS = [
    {
        "ingredient_name": "Matcha",
        "category": "Tea & Adaptogens",
        "volume_30d": 145000,
        "growth_pct": 34.5,
        "geo_focus": "North America",
    },
    {
        "ingredient_name": "Pistachio Paste",
        "category": "Nuts & Confectionery",
        "volume_30d": 89000,
        "growth_pct": 78.2,
        "geo_focus": "Europe",
    },
    {
        "ingredient_name": "Ube Extract",
        "category": "Roots & Natural Flavor",
        "volume_30d": 52000,
        "growth_pct": 41.0,
        "geo_focus": "Global",
    },
    {
        "ingredient_name": "Yuzu",
        "category": "Citrus",
        "volume_30d": 38000,
        "growth_pct": 19.8,
        "geo_focus": "East Asia",
    },
]

MOCK_DOCUMENTS = [
    {
        "slug": "matcha-health-benefits",
        "content": (
            "Ceremonial grade matcha is seeing elevated demand in functional beverage formulations. "
            "Consumers associate it with steady energy and focus due to the synergistic interaction between caffeine "
            "and L-theanine, avoiding the crash common with standard coffee."
        ),
        "metadata": {"topic": "Matcha", "type": "market_research", "year": 2026},
    },
    {
        "slug": "pistachio-viral-cpg",
        "content": (
            "Pistachio paste and cream applications surged following viral social media exposure across Dubai "
            "and European dessert trends. Premium confectioners are experiencing localized raw ingredient shortages, "
            "prompting interest in Turkish and Sicilian supply alternatives."
        ),
        "metadata": {"topic": "Pistachio", "type": "trend_analysis", "year": 2026},
    },
    {
        "slug": "ube-color-and-flavor",
        "content": (
            "Ube (purple yam) continues to dominate bakery and frozen dessert innovation due to its vibrant purple color "
            "and mellow, vanilla-nutty profile. Clean-label food developers use it as a natural coloring and flavoring alternative."
        ),
        "metadata": {"topic": "Ube", "type": "formulation_note", "year": 2026},
    },
]