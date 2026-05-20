"""Add conversations table

Revision ID: 0005
Revises: 0004
Create Date: 2025-01-05 00:00:00.000000
"""
from typing import Union
import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("direction", sqlmodel.AutoString(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sender_name", sqlmodel.AutoString(), nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reply_needed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reply_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("draft_reply", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_application_id", "conversations", ["application_id"])
    op.create_index("ix_conversations_reply_needed", "conversations", ["reply_needed"])


def downgrade() -> None:
    op.drop_index("ix_conversations_reply_needed", table_name="conversations")
    op.drop_index("ix_conversations_application_id", table_name="conversations")
    op.drop_table("conversations")
