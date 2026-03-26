"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-26
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
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    op.create_table(
        "conversions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("api_key_id", sa.String(36), sa.ForeignKey("api_keys.id"), nullable=True),
        sa.Column("batch_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("original_format", sa.String(10), nullable=False),
        sa.Column("original_size_bytes", sa.Integer(), nullable=False),
        sa.Column("input_path", sa.String(500), nullable=False),
        sa.Column("output_svg_path", sa.String(500), nullable=True),
        sa.Column("output_dxf_path", sa.String(500), nullable=True),
        sa.Column("share_token", sa.String(32), unique=True, nullable=True),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("is_billed", sa.Boolean(), default=False),
    )
    op.create_index("ix_conversions_share_token", "conversions", ["share_token"])
    op.create_index("ix_conversions_batch_id", "conversions", ["batch_id"])
    op.create_index("ix_conversions_user_created", "conversions", ["user_id", "created_at"])

    op.create_table(
        "webhooks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("events", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("webhooks")
    op.drop_table("conversions")
    op.drop_table("api_keys")
    op.drop_table("users")
