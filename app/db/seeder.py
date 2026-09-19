from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.db.session import engine, SessionLocal, init_db_extensions
from app.db.models import Base, Trend, KnowledgeDocument, RegulatoryRecord
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


    # ~~~~~~ Substitution Profiles ~~~~~~~
    {
        "slug": "sub-pumpkin-seed-paste",
        "content": "Ingredient: Pumpkin Seed Paste (Pepita Butter). Function: Fat source, binder, filling base. Flavor Profile: Earthy, nutty, slightly savory. Texture: Creamy, oily. Allergen: Seed (Low risk). Ideal substitution for Pistachio Paste in fillings where tree-nut allergies or costs are a concern.",
        "metadata": {"topic": "Substitution", "type": "functional_ingredient", "target": "Pistachio Paste"}
    },
    {
        "slug": "sub-sunflower-seed-butter",
        "content": "Ingredient: Sunflower Seed Butter. Function: Emulsifier, binder, spread. Flavor Profile: Roasted, neutral nutty, mildly sweet. Texture: Highly spreadable, smooth. Allergen: Seed (Low risk). Often used to replace peanut or pistachio butter in clean-label baked goods.",
        "metadata": {"topic": "Substitution", "type": "functional_ingredient", "target": "Nut Pastes"}
    },
    {
        "slug": "sub-sweet-potato-color",
        "content": "Ingredient: Purple Sweet Potato Extract. Function: Natural colorant (Red/Purple), anthocyanin source. Flavor Profile: Neutral, faintly sweet. Texture: Liquid or fine powder. Allergen: None. Excellent clean-label substitute for artificial Red Dye 40 or Titanium Dioxide in beverages.",
        "metadata": {"topic": "Substitution", "type": "functional_ingredient", "target": "Colorant"}
    }

]


MOCK_REGULATORY = [
    {"ingredient_name": "Matcha", "agency": "FDA", "status": "GRAS", "limitations": "None for general food use."},
    {"ingredient_name": "Pistachio Paste", "agency": "FDA", "status": "GRAS", "limitations": "Must declare tree nut allergen."},
    {"ingredient_name": "Titanium Dioxide", "agency": "EFSA/FDA", "status": "Restricted/Banned", "limitations": "Banned in EU as food additive (E171). FDA restricts to 1% by weight."},
    {"ingredient_name": "Brominated Vegetable Oil", "agency": "FDA", "status": "Banned", "limitations": "FDA revoked GRAS status; no longer permitted in beverages."}
]



def seed_database():
    print("initializing pgvector extension...")
    init_db_extensions()

    print("checking database tables exist...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        # upsert quantitative trends
        print("seeding/upserting quantitative trends...")
        for trend_data in MOCK_TRENDS:
            stmt = insert(Trend).values(**trend_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Trend.ingredient_name],

                # e.g. one pair is "category": stmt.excluded.category
                set_ = {k: v for k, v in trend_data.items() if k != "ingredient_name"},
            )
            session.execute(stmt)
            print(f"upserted trend: {trend_data['ingredient_name']}")
        

        print("\n Seeding / Upserting Regulatory Records...")
        for reg_data in MOCK_REGULATORY:
            stmt = insert(RegulatoryRecord).values(**reg_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=[RegulatoryRecord.ingredient_name],
                set_={k: v for k, v in reg_data.items() if k != "ingredient_name"}
            )
            session.execute(stmt)
            print(f"  ✓ Upserted regulation: {reg_data['ingredient_name']}")
    
    session.commit()

    # upsert RAG knowledge documents
    print("generating embeddings and upserting knowledge documents...")
    doc_texts = [d["content"] for d in MOCK_DOCUMENTS]
    doc_vectors = embedding_engine.embed_documents(doc_texts)

    for doc_data, vector in zip(MOCK_DOCUMENTS, doc_vectors):
        slug = doc_data["slug"]
        full_meta = {**doc_data['metadata'], "slug": slug}

        #check if document already exists from JSONB metadata match
        existing_doc = session.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.metadata_["slug"].astext == slug
            )
        ).first()

        if existing_doc:
            existing_doc.content = doc_data["content"]
            existing_doc.metadata_ = full_meta
            existing_doc.embedding = vector
            print(f"update doc: {slug}")
        else:
            new_doc = KnowledgeDocument(
                content=doc_data["content"],
                metadata_=full_meta,
                embedding=vector,
            )
            session.add(new_doc)
            print(f"inserted new doc: {slug}")
    
    session.commit()
    print("seeding completed successfully!")

if __name__ == "__main__":
    seed_database()