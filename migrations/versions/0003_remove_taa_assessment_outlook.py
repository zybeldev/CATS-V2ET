"""Remove accidental TAA Assessment outlook column

Revision ID: 0003_remove_taa_outlook
Revises: 0002_taa_assessment_outlook
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_remove_taa_outlook"
down_revision = "0002_taa_assessment_outlook"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Restore the frozen Assessment persistence structure."""
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("TAA_Assessment")
    }

    if "outlook" in columns:
        op.drop_column("TAA_Assessment", "outlook")


def downgrade() -> None:
    """Restore the historical 0002 schema if explicitly downgraded."""
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("TAA_Assessment")
    }

    if "outlook" not in columns:
        op.add_column(
            "TAA_Assessment",
            sa.Column("outlook", sa.String(length=16), nullable=True),
        )
