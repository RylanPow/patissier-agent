
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import String, Integer, Float, DateTime, func
from pgvector.sqlalchemy import Vector
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Trend(Base):
    # stores quantitative business metrics about food trends
    __tablename__ = "trends"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ingredient name is unique so can implement upsert logic later
    ingredient_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50))
    volume_30d: Mapped[int] = mapped_column(Integer, default=0)
    growth_pct: Mapped[float] = mapped_column(Float, default=0.0)
    geo_focus: Mapped[str] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class KnowledgeDocument(Base):
    # stores text chunks and embeddings for RAG
    __tablename__ = "knowledge_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str]
    metadata_: Mapped[dict] = mapped_column(JSONB, default=dict)
    
    # fastembed with BAAI/bge-small-en-v1.5 --> exactly 384 dimensions
    # note: pgvector MUST know this dimension size to index 
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
