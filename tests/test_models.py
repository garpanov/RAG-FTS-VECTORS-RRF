from typing import cast

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Table

from app.models import Chunk


def test_chunk_table_has_expected_columns() -> None:
    table = cast(Table, Chunk.__table__)

    assert tuple(table.columns.keys()) == (
        "document_id",
        "chunk_number",
        "content",
        "embedding",
    )
    assert all(not column.nullable for column in table.columns)
    assert isinstance(table.c.embedding.type, Vector)
    assert table.c.embedding.type.dim == 1024


def test_chunk_primary_key_scopes_number_to_document() -> None:
    table = cast(Table, Chunk.__table__)
    primary_key_columns = tuple(column.name for column in table.primary_key.columns)

    assert primary_key_columns == ("document_id", "chunk_number")


def test_chunk_document_foreign_key_cascades_on_delete() -> None:
    table = cast(Table, Chunk.__table__)
    foreign_key = next(iter(table.c.document_id.foreign_keys))

    assert foreign_key.target_fullname == "documents.id"
    assert foreign_key.ondelete == "CASCADE"


def test_chunk_number_must_be_nonnegative() -> None:
    table = cast(Table, Chunk.__table__)
    constraints = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert str(constraints["ck_chunks_chunk_number_nonnegative"].sqltext) == "chunk_number >= 0"
