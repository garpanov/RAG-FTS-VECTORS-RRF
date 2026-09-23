from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("document_number", name="uq_documents_document_number"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_number: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint("chunk_number >= 0", name="ck_chunks_chunk_number_nonnegative"),
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )

    document_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chunk_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple'::regconfig, content)", persisted=True),
        nullable=False,
    )
