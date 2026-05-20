"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # candidates table
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.AutoString(), nullable=False),
        sa.Column("email", sqlmodel.AutoString(), nullable=False),
        sa.Column("phone", sqlmodel.AutoString(), nullable=True),
        sa.Column("cv_raw_text", sa.Text(), nullable=True),
        sa.Column("cv_file_path", sqlmodel.AutoString(), nullable=True),
        sa.Column("cv_parsed_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_candidates_email"), "candidates", ["email"], unique=True)

    # job_preferences table
    op.create_table(
        "job_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("target_titles", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("target_cities", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("min_salary", sa.Integer(), nullable=True),
        sa.Column("max_salary", sa.Integer(), nullable=True),
        sa.Column("excluded_companies", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("preferred_industries", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("remote_ok", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("full_time_only", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # jobs table
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sqlmodel.AutoString(), nullable=True),
        sa.Column("source", sqlmodel.AutoString(), nullable=False, server_default="manual"),
        sa.Column("title", sqlmodel.AutoString(), nullable=False),
        sa.Column("company_name", sqlmodel.AutoString(), nullable=False),
        sa.Column("city", sqlmodel.AutoString(), nullable=True),
        sa.Column("salary_range", sqlmodel.AutoString(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("url", sqlmodel.AutoString(), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_jobs_external_id"), "jobs", ["external_id"], unique=True)

    # system_events table
    op.create_table(
        "system_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("level", sqlmodel.AutoString(), nullable=False),
        sa.Column("source", sqlmodel.AutoString(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("system_events")
    op.drop_index(op.f("ix_jobs_external_id"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("job_preferences")
    op.drop_index(op.f("ix_candidates_email"), table_name="candidates")
    op.drop_table("candidates")
