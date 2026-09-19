from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import engine, SessionLocal, init_db_extensions
from app.db.models import Base, Trend, KnowledgeDocument, RegulatoryRecord
from app.agent.embeddings import embedding_engine

# mock quantitative trend data
MOCK_TRENDS = [
    {"ingredient_name": "Matcha", "category": "Tea & Adaptogens", "volume_30d": 145000, "growth_pct": 34.5, "geo_focus": "North America"},
    {"ingredient_name": "Pistachio Paste", "category": "Nuts & Confectionery", "volume_30d": 89000, "growth_pct": 78.2, "geo_focus": "Europe"},
    {"ingredient_name": "Ube Extract", "category": "Roots & Natural Flavor", "volume_30d": 52000, "growth_pct": 41.0, "geo_focus": "Global"},
    {"ingredient_name": "Yuzu", "category": "Citrus", "volume_30d": 38000, "growth_pct": 19.8, "geo_focus": "East Asia"},
]

# mock regulatory data
MOCK_REGULATORY = [
    {"ingredient_name": "Matcha", "agency": "FDA", "status": "GRAS", "limitations": "None for general food use."},
    {"ingredient_name": "Pistachio Paste", "agency": "FDA", "status": "GRAS", "limitations": "Must declare tree nut allergen."},
    # split EFSA and FDA into two clean records
    {"ingredient_name": "Titanium Dioxide", "agency": "EFSA", "status": "Banned", "limitations": "Banned in EU as food additive (E171)."},
    {"ingredient_name": "Titanium Dioxide", "agency": "FDA", "status": "Restricted", "limitations": "Restricts to 1% by weight."},
    {"ingredient_name": "Brominated Vegetable Oil", "agency": "FDA", "status": "Banned", "limitations": "FDA revoked GRAS status; no longer permitted in beverages."}
]


MOCK_DOCUMENTS = [
    # mock qualitative ingredient data
    {
        "slug": "matcha-health-benefits",
        "content": "Ceremonial grade matcha is seeing elevated demand in functional beverage formulations. Consumers associate it with steady energy and focus due to the synergistic interaction between caffeine and L-theanine, avoiding the crash common with standard coffee.",
        "metadata": {"topic": "Matcha", "type": "market_research", "year": 2026},
    },
    {
        "slug": "pistachio-viral-cpg",
        "content": "Pistachio paste and cream applications surged following viral social media exposure across Dubai and European dessert trends. Premium confectioners are experiencing localized raw ingredient shortages, prompting interest in Turkish and Sicilian supply alternatives.",
        "metadata": {"topic": "Pistachio", "type": "trend_analysis", "year": 2026},
    },

    # functional profiles for Substitution Modeler
    {
        "slug": "sub-pumpkin-seed-paste",
        "content": "Ingredient: Pumpkin Seed Paste (Pepita Butter). Function: Fat source, binder, filling base. Flavor Profile: Earthy, nutty, slightly savory. Texture: Creamy, oily. Allergen: Seed (Low risk). Ideal substitution for Pistachio Paste in fillings where tree-nut allergies or costs are a concern.",
        "metadata": {"topic": "Substitution", "type": "substitute_profile", "target": "Pistachio Paste"}
    },
    {
        "slug": "sub-sunflower-seed-butter",
        "content": "Ingredient: Sunflower Seed Butter. Function: Emulsifier, binder, spread. Flavor Profile: Roasted, neutral nutty, mildly sweet. Texture: Highly spreadable, smooth. Allergen: Seed (Low risk). Often used to replace peanut or pistachio butter in clean-label baked goods.",
        "metadata": {"topic": "Substitution", "type": "substitute_profile", "target": "Nut Pastes"}
    },
    {
        "slug": "sub-sweet-potato-color",
        "content": "Ingredient: Purple Sweet Potato Extract. Function: Natural colorant (Red/Purple), anthocyanin source. Flavor Profile: Neutral, faintly sweet. Texture: Liquid or fine powder. Allergen: None. Excellent clean-label substitute for artificial Red Dye 40 or Titanium Dioxide in beverages.",
        "metadata": {"topic": "Substitution", "type": "substitute_profile", "target": "Colorant"}
    }
]

def seed_database():
    print(" Ensuring pgvector extension is ready...")
    init_db_extensions()
    
    print(" Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        # 1. upsert quantitative trends
        print("\n Seeding / Upserting Quantitative Trends...")
        for trend_data in MOCK_TRENDS:
            stmt = insert(Trend).values(**trend_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Trend.ingredient_name],
                set_={k: v for k, v in trend_data.items() if k != "ingredient_name"}
            )
            session.execute(stmt)
            print(f" Upserted trend: {trend_data['ingredient_name']}")
            
        # 2. upsert regulatory records
        print("\n Seeding / Upserting Regulatory Records...")
        for reg_data in MOCK_REGULATORY:
            stmt = insert(RegulatoryRecord).values(**reg_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ingredient_name", "agency"],
                set_={k: v for k, v in reg_data.items() if k not in ["ingredient_name", "agency"]}            
            )
            session.execute(stmt)
            print(f" Upserted regulation: {reg_data['ingredient_name']}")

        session.commit()

        # 3. upsert RAG knowledge documents (qualitative + substitution)
        print("\n Generating embeddings and upserting Knowledge Documents...")
        doc_texts = [d["content"] for d in MOCK_DOCUMENTS]
        doc_vectors = embedding_engine.embed_documents(doc_texts)

        for doc_data, vector in zip(MOCK_DOCUMENTS, doc_vectors):
            slug = doc_data["slug"]
            full_meta = {**doc_data["metadata"], "slug": slug}

            existing_doc = session.scalar(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.metadata_["slug"].astext == slug
                )
            )

            if existing_doc:
                existing_doc.content = doc_data["content"]
                existing_doc.metadata_ = full_meta
                existing_doc.embedding = vector
                print(f" Updated doc: {slug}")
            else:
                new_doc = KnowledgeDocument(
                    content=doc_data["content"],
                    metadata_=full_meta,
                    embedding=vector,
                )
                session.add(new_doc)
                print(f" Inserted new doc: {slug}")

        session.commit()
        print("\n Seeding completed successfully!")

if __name__ == "__main__":
    seed_database()