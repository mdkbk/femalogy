"""period gap_confirmed

Revision ID: 7c1e2d9a4b10
Revises: 465fdda44b76
Create Date: 2026-11-04 22:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c1e2d9a4b10"
down_revision: Union[str, Sequence[str], None] = "465fdda44b76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("periods") as batch:
        batch.add_column(sa.Column("gap_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("periods") as batch:
        batch.drop_column("gap_confirmed")
