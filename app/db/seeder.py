from sqlalchemy import select
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
                set_ = {
                    "category": stmt.excluded.category,
                    "volume_30d": stmt.excluded.volume_30d,
                    "growth_pct": stmt.excluded.growth_pct,
                    "geo_focus": stmt.excluded.geo_focus,
                },
            )
            session.execute(stmt)
            print(f"upserted trend: {trend_data['ingredient_name']}")
        session.execute(stmt)
        print(f"upserted trend: {trend_data['ingredient_name']}")
    
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