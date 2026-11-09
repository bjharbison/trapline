"""First persistent schema. No API routes until Host/Origin security review."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    documents: Mapped[list["Document"]] = relationship(back_populates="investigation")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id", ondelete="RESTRICT"), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    investigation: Mapped[Investigation] = relationship(back_populates="documents")
    __table_args__ = (Index("ix_documents_investigation_id", "investigation_id"),)


class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (Index("ix_entities_investigation_id", "investigation_id"),)


class Relationship(Base):
    __tablename__ = "relationships"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    investigation_id: Mapped[str] = mapped_column(ForeignKey("investigations.id", ondelete="RESTRICT"), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    __table_args__ = (Index("ix_relationships_investigation_id", "investigation_id"),)


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    relationship_id: Mapped[str] = mapped_column(ForeignKey("relationships.id", ondelete="RESTRICT"), nullable=False)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    __table_args__ = (Index("ix_evidence_relationship_id", "relationship_id"), Index("ix_evidence_document_id", "document_id"))
