"""initial: campaigns, offers

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geo", sa.String(2), nullable=False),
        sa.Column("keitaro_campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("keitaro_domain_id", sa.BigInteger(), nullable=False),
        sa.Column("keitaro_group_id", sa.BigInteger(), nullable=False),
        sa.Column("keitaro_source_id", sa.BigInteger(), nullable=False),
        sa.Column("offer_stream_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_campaigns_keitaro_campaign_id",
        "campaigns",
        ["keitaro_campaign_id"],
        unique=True,
    )
    op.create_table(
        "offers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "campaign_id",
            sa.Integer(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("keitaro_offer_id", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("campaign_id", "keitaro_offer_id", name="uq_offer_per_campaign"),
    )


def downgrade() -> None:
    op.drop_table("offers")
    op.drop_index("ix_campaigns_keitaro_campaign_id", table_name="campaigns")
    op.drop_table("campaigns")
