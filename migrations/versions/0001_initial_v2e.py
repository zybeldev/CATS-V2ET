"""Initial CATS V2E schema

Revision ID: 0001_initial_v2e
Revises:
"""

from alembic import op

from cats.database.base import Base
import cats.database.models  # noqa: F401

revision = "0001_initial_v2e"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
