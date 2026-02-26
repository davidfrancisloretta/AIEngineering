"""Add users, api_configs, and rave_transactions tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "api_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rave_public_key", sa.String(), nullable=True),
        sa.Column("rave_secret_key", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_api_configs_id"), "api_configs", ["id"], unique=False)

    op.create_table(
        "rave_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rave_id", sa.Integer(), nullable=True),
        sa.Column("transaction_ref", sa.String(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("payment_type", sa.String(), nullable=True),
        sa.Column("customer_email", sa.String(), nullable=True),
        sa.Column("customer_name", sa.String(), nullable=True),
        sa.Column("data_yaml", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rave_transactions_id"), "rave_transactions", ["id"], unique=False)
    op.create_index(op.f("ix_rave_transactions_rave_id"), "rave_transactions", ["rave_id"], unique=True)
    op.create_index(op.f("ix_rave_transactions_transaction_ref"), "rave_transactions", ["transaction_ref"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_rave_transactions_transaction_ref"), table_name="rave_transactions")
    op.drop_index(op.f("ix_rave_transactions_rave_id"), table_name="rave_transactions")
    op.drop_index(op.f("ix_rave_transactions_id"), table_name="rave_transactions")
    op.drop_table("rave_transactions")
    op.drop_index(op.f("ix_api_configs_id"), table_name="api_configs")
    op.drop_table("api_configs")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
