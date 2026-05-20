"""Add approval_queue table

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-03 00:00:00.000000
"""
from typing import Union
import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_queue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("action", sqlmodel.AutoString(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sqlmodel.AutoString(), nullable=False, server_default="pending"),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_queue_application_id", "approval_queue", ["application_id"])
    op.create_index("ix_approval_queue_status", "approval_queue", ["status"])


def downgrade() -> None:
    op.drop_index("ix_approval_queue_status", table_name="approval_queue")
    op.drop_index("ix_approval_queue_application_id", table_name="approval_queue")
    op.drop_table("approval_queue")
