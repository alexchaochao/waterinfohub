"""init schema

Revision ID: 20260413_0001
Revises:
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision = "20260413_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "raw_documents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("raw_html_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="new"),
    )
    op.create_index("idx_raw_documents_domain", "raw_documents", ["domain"])
    op.create_index("idx_raw_documents_published_at", "raw_documents", ["published_at"])

    op.create_table(
        "normalized_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("entity_name", sa.Text(), nullable=True),
        sa.Column("event_title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("technologies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("signal_strength", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False, unique=True),
        sa.Column("embedding", Vector(1536), nullable=True),
    )
    op.create_index("idx_normalized_events_domain", "normalized_events", ["domain"])
    op.create_index("idx_normalized_events_published_at", "normalized_events", ["published_at"])

    op.create_table(
        "event_sources",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("normalized_events.id", ondelete="CASCADE")),
        sa.Column("raw_document_id", sa.BigInteger(), sa.ForeignKey("raw_documents.id", ondelete="CASCADE")),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("quote_text", sa.Text(), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("idx_event_sources_event_id", "event_sources", ["event_id"])

    op.create_table(
        "standard_events",
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("standard_no", sa.Text(), nullable=True),
        sa.Column("standard_name", sa.Text(), nullable=True),
        sa.Column("standard_scope", sa.Text(), nullable=True),
        sa.Column("action_type", sa.Text(), nullable=True),
        sa.Column("organization", sa.Text(), nullable=True),
    )

    op.create_table(
        "competitor_events",
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("market", sa.Text(), nullable=True),
        sa.Column("strategic_intent", sa.Text(), nullable=True),
        sa.Column("impact_analysis", sa.Text(), nullable=True),
    )

    op.create_table(
        "tender_events",
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("project_name", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True),
        sa.Column("procurement_org", sa.Text(), nullable=True),
        sa.Column("award_company", sa.Text(), nullable=True),
        sa.Column("amount", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
    )

    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("report_week", sa.Text(), nullable=False, unique=True),
        sa.Column("report_title", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("report_markdown", sa.Text(), nullable=False),
        sa.Column("report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="generated"),
    )

    op.create_table(
        "weekly_report_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("weekly_report_id", sa.BigInteger(), sa.ForeignKey("weekly_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("normalized_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("section_name", sa.Text(), nullable=False),
        sa.UniqueConstraint("weekly_report_id", "event_id", name="uq_weekly_report_item_once"),
    )
    op.create_index("idx_weekly_report_items_report_id", "weekly_report_items", ["weekly_report_id"])


def downgrade() -> None:
    op.drop_index("idx_weekly_report_items_report_id", table_name="weekly_report_items")
    op.drop_table("weekly_report_items")
    op.drop_table("weekly_reports")
    op.drop_table("tender_events")
    op.drop_table("competitor_events")
    op.drop_table("standard_events")
    op.drop_index("idx_event_sources_event_id", table_name="event_sources")
    op.drop_table("event_sources")
    op.drop_index("idx_normalized_events_published_at", table_name="normalized_events")
    op.drop_index("idx_normalized_events_domain", table_name="normalized_events")
    op.drop_table("normalized_events")
    op.drop_index("idx_raw_documents_published_at", table_name="raw_documents")
    op.drop_index("idx_raw_documents_domain", table_name="raw_documents")
    op.drop_table("raw_documents")
