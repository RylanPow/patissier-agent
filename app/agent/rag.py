from langchain_core.tools import tool
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import KnowledgeDocument
from app.agent.embeddings import embedding_engine

@tool
def search_food_knowledge(query: str) -> str:
    # note that triple quote strings are just strings, except you can use quotes " " inside
    # without escaping, and they can be multiline

    # ~~~~~~~~~~~~~~~~IMPORTANT~~~~~~~~~~~~~~~~~~~~~~
    # for the @tool decorator this is docstring actually necessary!  
    # it will be fed to the LLM to provide context
    """
    # this tool can search the internal knowledge base for qualitative information,
    # health benefits, culinary uses, formulation notes, and indstury reports about ingredients
    # input should be a specific question or topic e.g. "why do people drink matcha"?
    """


    try:
        # convert search query into a 384 dimensional vector
        query_vector = embedding_engine.embed_query(query)
        with SessionLocal() as session:
            # perform vector similarity search using pgevector cosine distance
            # fetch top 2 most relevant document chunks
            results = session.scalars(
                select(KnowledgeDocument)
                .order_by(KnowledgeDocument.embedding.cosine_distance(query_vector))
                .limit(2)
            ).all()

            if not results:
                return "No relevant knowlwedge documents found"
            
            # format the extracted documents into a clean string for the LLM to read
            formatted_results = []
            for i, doc in enumerate(results, 1):
                topic = doc.metadata_.get("topic", 'Unknown Topic')
                doc_type = doc.metadata_.get("Type", "Document")
                formatted_results.append(f"--- Document {i} ({topic} - {doc_type}) ---\n{doc.content}")
            
            return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error executing knowledge search: {str(e)}"