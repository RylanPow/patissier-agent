from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models import Trend, KnowledgeDocument
from app.agent.embeddings import embedding_engine

def run_verification():
    print("Starting DB verification...\n")

    with SessionLocal() as session:
        print("TEST1: querying relational data (trends)")
        target_ingredient = "Matcha"

        trend = session.scalar(
            select(Trend).where(Trend.ingredient_name == target_ingredient)
        )

        if trend:
            print(f"found {trend.ingredient_name}:")
            print(f"  -Category: {trend.category}")
            print(f"  -30-Day Volume: {trend.volume_30d:,}")
            print(f"  -Growth: {trend.growth_pct}%")
        else:
            print(f"could not find {target_ingredient}")
        
        print("\n" + "="*40 + "\n")

        print("TEST 2: Querying Semantic Vector Data (RAG)")
        query_text = "Why do consumers drink matcha instead of coffee?"
        print(f"  Question: '{query_text}'")

        query_vector = embedding_engine.embed_query(query_text)

        best_doc = session.scalar(
            select(KnowledgeDocument)
            .order_by(KnowledgeDocument.embedding.cosine_distance(query_vector))
            .limit(1)
        )

        if best_doc:
            print(f"Top Match Found (Slug: {best_doc.metadata_.get('slug')}):")
            print(f"  -Content: {best_doc.content}")
        else:
            print("No documents found in the database.")

if __name__ == "__main__":
    run_verification()