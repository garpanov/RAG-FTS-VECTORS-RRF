"""Create the chunks table.

Revision ID: 20260921_0002
Revises: 20260920_0001
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "20260921_0002"
down_revision: str | Sequence[str] | None = "20260920_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chunks",
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.CheckConstraint(
            "chunk_number >= 0",
            name="ck_chunks_chunk_number_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("document_id", "chunk_number"),
    )


def downgrade() -> None:
    op.drop_table("chunks")
