"""query optimization fields and indexes

Revision ID: 20260413_0002
Revises: 20260413_0001
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0002"
down_revision = "20260413_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("raw_documents", sa.Column("source_host", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE raw_documents
        SET source_host = split_part(replace(replace(source_url, 'https://', ''), 'http://', ''), '/', 1)
        WHERE source_host IS NULL
        """
    )
    op.create_index(
        "idx_raw_documents_domain_source_time",
        "raw_documents",
        ["domain", "source_id", "fetched_at"],
    )
    op.create_index(
        "idx_raw_documents_status_time",
        "raw_documents",
        ["status", "fetched_at"],
    )

    op.add_column("normalized_events", sa.Column("search_text", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE normalized_events
        SET search_text = trim(
            concat_ws(
                ' ',
                coalesce(event_title, ''),
                coalesce(summary, ''),
                coalesce(entity_name, ''),
                coalesce(region, ''),
                coalesce(country, '')
            )
        )
        WHERE search_text IS NULL
        """
    )
    op.create_index(
        "idx_normalized_events_domain_priority_time",
        "normalized_events",
        ["domain", "importance_score", "published_at"],
    )
    op.create_index(
        "idx_normalized_events_entity_time",
        "normalized_events",
        ["entity_name", "published_at"],
    )
    op.create_index(
        "idx_normalized_events_technologies_gin",
        "normalized_events",
        ["technologies"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_normalized_events_tags_gin",
        "normalized_events",
        ["tags"],
        postgresql_using="gin",
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_normalized_events_search_text_tsv
        ON normalized_events
        USING GIN (to_tsvector('simple', coalesce(search_text, '')))
        """
    )
    # op.execute(
    #     """
    #     CREATE INDEX IF NOT EXISTS idx_normalized_events_embedding_hnsw
    #     ON normalized_events
    #     USING hnsw (embedding vector_cosine_ops)
    #     """
    # )

    op.create_index(
        "idx_event_sources_raw_document_id",
        "event_sources",
        ["raw_document_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_event_sources_raw_document_id", table_name="event_sources")

    op.execute("DROP INDEX IF EXISTS idx_normalized_events_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_normalized_events_search_text_tsv")
    op.drop_index("idx_normalized_events_tags_gin", table_name="normalized_events")
    op.drop_index("idx_normalized_events_technologies_gin", table_name="normalized_events")
    op.drop_index("idx_normalized_events_entity_time", table_name="normalized_events")
    op.drop_index("idx_normalized_events_domain_priority_time", table_name="normalized_events")
    op.drop_column("normalized_events", "search_text")

    op.drop_index("idx_raw_documents_status_time", table_name="raw_documents")
    op.drop_index("idx_raw_documents_domain_source_time", table_name="raw_documents")
    op.drop_column("raw_documents", "source_host")
