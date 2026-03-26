"""Add multi-output fields to conversions

Revision ID: 002
Revises: 001
Create Date: 2026-03-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversions", sa.Column("output_dir_path", sa.String(500), nullable=True))
    op.add_column("conversions", sa.Column("output_bmp_path", sa.String(500), nullable=True))
    op.add_column("conversions", sa.Column("output_png_path", sa.String(500), nullable=True))
    op.add_column("conversions", sa.Column("output_layers_json", sa.String(500), nullable=True))
    op.add_column("conversions", sa.Column("output_viewer_path", sa.String(500), nullable=True))
    op.add_column("conversions", sa.Column("layers_info", sa.JSON(), nullable=True))
    op.add_column("conversions", sa.Column("engine_used", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("conversions", "engine_used")
    op.drop_column("conversions", "layers_info")
    op.drop_column("conversions", "output_viewer_path")
    op.drop_column("conversions", "output_layers_json")
    op.drop_column("conversions", "output_png_path")
    op.drop_column("conversions", "output_bmp_path")
    op.drop_column("conversions", "output_dir_path")
