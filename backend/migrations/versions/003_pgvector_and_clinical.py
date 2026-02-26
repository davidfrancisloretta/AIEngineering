"""Enable pgvector extension and create clinical trial + RAG tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. clinical_studies
    op.create_table(
        "clinical_studies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("study_oid", sa.String, nullable=False),
        sa.Column("protocol_name", sa.String, nullable=False),
        sa.Column("phase", sa.String),
        sa.Column("sponsor", sa.String),
        sa.Column("therapeutic_area", sa.String),
        sa.Column("objective", sa.Text),
        sa.Column("status", sa.String, server_default="Active"),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_clinical_studies_id", "clinical_studies", ["id"])
    op.create_index("ix_clinical_studies_study_oid", "clinical_studies", ["study_oid"], unique=True)

    # 3. clinical_subjects
    op.create_table(
        "clinical_subjects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("study_id", sa.Integer, sa.ForeignKey("clinical_studies.id"), nullable=False),
        sa.Column("subject_key", sa.String, nullable=False),
        sa.Column("site_id", sa.String),
        sa.Column("site_name", sa.String),
        sa.Column("age", sa.Integer),
        sa.Column("sex", sa.String),
        sa.Column("race", sa.String),
        sa.Column("enrollment_date", sa.Date),
        sa.Column("status", sa.String, server_default="Enrolled"),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_clinical_subjects_id", "clinical_subjects", ["id"])
    op.create_index("ix_clinical_subjects_subject_key", "clinical_subjects", ["subject_key"])

    # 4. clinical_visits
    op.create_table(
        "clinical_visits",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("subject_id", sa.Integer, sa.ForeignKey("clinical_subjects.id"), nullable=False),
        sa.Column("visit_oid", sa.String),
        sa.Column("visit_name", sa.String),
        sa.Column("visit_date", sa.Date),
        sa.Column("status", sa.String, server_default="Completed"),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_clinical_visits_id", "clinical_visits", ["id"])

    # 5. clinical_forms
    op.create_table(
        "clinical_forms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("visit_id", sa.Integer, sa.ForeignKey("clinical_visits.id"), nullable=False),
        sa.Column("form_oid", sa.String),
        sa.Column("form_name", sa.String),
        sa.Column("data_json", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_clinical_forms_id", "clinical_forms", ["id"])

    # 6. document_chunks — raw DDL for vector(768) column
    op.execute("""
        CREATE TABLE document_chunks (
            id            SERIAL PRIMARY KEY,
            source_type   VARCHAR NOT NULL,
            source_id     INTEGER NOT NULL,
            chunk_text    TEXT NOT NULL,
            embedding     vector(768),
            metadata_json TEXT,
            created_at    TIMESTAMP DEFAULT NOW()
        )
    """)
    op.create_index("ix_document_chunks_source_type", "document_chunks", ["source_type"])
    op.create_index("ix_document_chunks_source_id", "document_chunks", ["source_id"])

    # 7. HNSW index for cosine similarity (works on empty table, unlike IVFFlat)
    op.execute("""
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.drop_table("clinical_forms")
    op.drop_table("clinical_visits")
    op.drop_table("clinical_subjects")
    op.drop_table("clinical_studies")
    op.execute("DROP EXTENSION IF EXISTS vector")
