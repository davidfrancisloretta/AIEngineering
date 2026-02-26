"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_name", sa.String(), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("conversions", sa.Integer(), nullable=True),
        sa.Column("ttr", sa.Float(), nullable=True),
        sa.Column("vtr", sa.Float(), nullable=True),
        sa.Column("cvr", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_campaign_metrics_id"), "campaign_metrics", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_campaign_metrics_campaign_name"),
        "campaign_metrics",
        ["campaign_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_campaign_metrics_campaign_name"), table_name="campaign_metrics"
    )
    op.drop_index(op.f("ix_campaign_metrics_id"), table_name="campaign_metrics")
    op.drop_table("campaign_metrics")
