"""Initial V2 persistence schema.

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("investigations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("title", sa.String(256), nullable=False), sa.Column("notes", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.create_table("documents", sa.Column("id", sa.String(36), primary_key=True), sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id", ondelete="RESTRICT"), nullable=False), sa.Column("filename", sa.String(512), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("content_type", sa.String(128), nullable=False), sa.Column("byte_size", sa.Integer(), nullable=False), sa.Column("extracted_text", sa.Text()))
    op.create_index("ix_documents_investigation_id", "documents", ["investigation_id"])
    op.create_table("entities", sa.Column("id", sa.String(36), primary_key=True), sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id", ondelete="RESTRICT"), nullable=False), sa.Column("name", sa.String(512), nullable=False), sa.Column("entity_type", sa.String(64), nullable=False))
    op.create_index("ix_entities_investigation_id", "entities", ["investigation_id"])
    op.create_table("relationships", sa.Column("id", sa.String(36), primary_key=True), sa.Column("investigation_id", sa.String(36), sa.ForeignKey("investigations.id", ondelete="RESTRICT"), nullable=False), sa.Column("source_entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False), sa.Column("target_entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False), sa.Column("label", sa.String(256), nullable=False))
    op.create_index("ix_relationships_investigation_id", "relationships", ["investigation_id"])
    op.create_table("evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("relationship_id", sa.String(36), sa.ForeignKey("relationships.id", ondelete="RESTRICT"), nullable=False), sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False), sa.Column("quote", sa.Text(), nullable=False), sa.Column("start_offset", sa.Integer()), sa.Column("end_offset", sa.Integer()))
    op.create_index("ix_evidence_relationship_id", "evidence", ["relationship_id"])
    op.create_index("ix_evidence_document_id", "evidence", ["document_id"])


def downgrade() -> None:
    # Only for disposable development databases; backup before any downgrade.
    op.drop_table("evidence")
    op.drop_table("relationships")
    op.drop_table("entities")
    op.drop_table("documents")
    op.drop_table("investigations")
