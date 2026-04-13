from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, Index, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from waterinfohub.db.session import Base


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (
        Index("idx_raw_documents_domain_source_time", "domain", "source_id", "fetched_at"),
        Index("idx_raw_documents_status_time", "status", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_host: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_html_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="new")


class NormalizedEvent(Base):
    __tablename__ = "normalized_events"
    __table_args__ = (
        Index(
            "idx_normalized_events_domain_priority_time",
            "domain",
            "importance_score",
            "published_at",
        ),
        Index("idx_normalized_events_entity_time", "entity_name", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)


class EventSource(Base):
    __tablename__ = "event_sources"
    __table_args__ = (Index("idx_event_sources_raw_document_id", "raw_document_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("normalized_events.id", ondelete="CASCADE"))
    raw_document_id: Mapped[int] = mapped_column(ForeignKey("raw_documents.id", ondelete="CASCADE"))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    quote_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)


class StandardEvent(Base):
    __tablename__ = "standard_events"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True
    )
    standard_no: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization: Mapped[str | None] = mapped_column(Text, nullable=True)


class CompetitorEvent(Base):
    __tablename__ = "competitor_events"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True
    )
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    market: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategic_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)


class TenderEvent(Base):
    __tablename__ = "tender_events"

    event_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True
    )
    project_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    procurement_org: Mapped[str | None] = mapped_column(Text, nullable=True)
    award_company: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str | None] = mapped_column(Text, nullable=True)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_week: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    report_title: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    report_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="generated")


class WeeklyReportItem(Base):
    __tablename__ = "weekly_report_items"
    __table_args__ = (
        UniqueConstraint("weekly_report_id", "event_id", name="uq_weekly_report_item_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    weekly_report_id: Mapped[int] = mapped_column(
        ForeignKey("weekly_reports.id", ondelete="CASCADE"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("normalized_events.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(nullable=False)
    section_name: Mapped[str] = mapped_column(Text, nullable=False)
