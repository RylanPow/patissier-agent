from typing import List
from fastembed import TextEmbedding

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
    
class EmbeddingEngine:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self._model = TextEmbedding(model_name=model_name)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.embed(texts)
        # fastembed returns numpy arrays -> convert to float lists for SQLalchemy and pgvector
        return [e.tolist() for e in embeddings]
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

embedding_engine = EmbeddingEngine()