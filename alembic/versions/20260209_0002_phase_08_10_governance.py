"""phase 08-10 governance schema

Revision ID: 20260209_0002
Revises: 20260209_0001
Create Date: 2026-02-09 14:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260209_0002"
down_revision = "20260209_0001"
branch_labels = None
depends_on = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    cols = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in cols)


def _has_table(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "documents"):
        with op.batch_alter_table("documents") as batch:
            if not _has_column(bind, "documents", "tenant_id"):
                batch.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"))
            if not _has_column(bind, "documents", "ingestion_status"):
                batch.add_column(
                    sa.Column("ingestion_status", sa.String(length=32), nullable=False, server_default="ACCEPTED")
                )
            if not _has_column(bind, "documents", "quality_tier"):
                batch.add_column(sa.Column("quality_tier", sa.String(length=16), nullable=True))
            if not _has_column(bind, "documents", "quality_score"):
                batch.add_column(sa.Column("quality_score", sa.Float(), nullable=True))
        if not _has_index(bind, "documents", "ix_documents_tenant_id"):
            op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])

    if _has_table(bind, "runs"):
        with op.batch_alter_table("runs") as batch:
            if not _has_column(bind, "runs", "tenant_id"):
                batch.add_column(sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"))
            if not _has_column(bind, "runs", "review_decision"):
                batch.add_column(sa.Column("review_decision", sa.String(length=32), nullable=True))
            if not _has_column(bind, "runs", "review_reason_codes_json"):
                batch.add_column(sa.Column("review_reason_codes_json", sa.Text(), nullable=True))
            if not _has_column(bind, "runs", "decision_log_json"):
                batch.add_column(sa.Column("decision_log_json", sa.Text(), nullable=True))
        if not _has_index(bind, "runs", "ix_runs_tenant_id"):
            op.create_index("ix_runs_tenant_id", "runs", ["tenant_id"])

    if not _has_table(bind, "quarantine_items"):
        op.create_table(
            "quarantine_items",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("stage", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("reason_codes_json", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=True),
            sa.Column("storage_path", sa.String(length=500), nullable=False),
            sa.Column("reprocess_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_reprocessed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _has_index(bind, "quarantine_items", "ix_quarantine_items_document_id"):
        op.create_index("ix_quarantine_items_document_id", "quarantine_items", ["document_id"])
    if not _has_index(bind, "quarantine_items", "ix_quarantine_items_tenant_id"):
        op.create_index("ix_quarantine_items_tenant_id", "quarantine_items", ["tenant_id"])


def downgrade() -> None:
    # Downgrade is intentionally conservative for SQLite compatibility in local environments.
    pass
