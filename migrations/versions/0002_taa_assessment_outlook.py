"""Add structured TAA financial outlook

Revision ID: 0002_taa_assessment_outlook
Revises: 0001_initial_v2e
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_taa_assessment_outlook"
down_revision = "0001_initial_v2e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0001 creates from current metadata, so a brand-new database may already
    # contain the column. Existing V2ET databases at 0001 do not.
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("TAA_Assessment")}
    if "outlook" not in columns:
        # Historical rows remain NULL rather than inventing a financial conclusion
        # after the fact.
        op.add_column(
            "TAA_Assessment",
            sa.Column("outlook", sa.String(length=16), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("TAA_Assessment")}
    if "outlook" in columns:
        op.drop_column("TAA_Assessment", "outlook")
