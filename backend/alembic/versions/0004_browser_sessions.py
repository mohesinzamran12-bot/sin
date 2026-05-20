"""Add browser_sessions table

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-04 00:00:00.000000
"""
from typing import Union
import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "browser_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform", sqlmodel.AutoString(), nullable=False),
        sa.Column("cookies_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("user_agent", sqlmodel.AutoString(), nullable=False, server_default=""),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_browser_sessions_platform", "browser_sessions", ["platform"])
    op.create_index("ix_browser_sessions_is_valid", "browser_sessions", ["is_valid"])


def downgrade() -> None:
    op.drop_index("ix_browser_sessions_is_valid", table_name="browser_sessions")
    op.drop_index("ix_browser_sessions_platform", table_name="browser_sessions")
    op.drop_table("browser_sessions")
