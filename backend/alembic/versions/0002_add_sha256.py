"""add sha256 to file_versions

Revision ID: 0002_add_sha256
Revises: 0001_initial_schema
Create Date: 2026-11-17 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_sha256"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_versions",
        sa.Column("sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("file_versions", "sha256")
