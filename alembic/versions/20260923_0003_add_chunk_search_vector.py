"""Add a full-text search vector to chunks.

Revision ID: 20260923_0003
Revises: 20260921_0002
Create Date: 2026-09-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260923_0003"
down_revision: str | Sequence[str] | None = "20260921_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('simple'::regconfig, content)",
                persisted=True,
            ),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chunks_search_vector",
        "chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chunks_search_vector",
        table_name="chunks",
        postgresql_using="gin",
    )
    op.drop_column("chunks", "search_vector")
