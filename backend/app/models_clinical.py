"""
SQLAlchemy models for clinical trial data and RAG document chunks.
Shares the same declarative Base as models.py.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Date, Text, DateTime, ForeignKey, Boolean, SmallInteger
from sqlalchemy.orm import relationship

from models import Base


def _now():
    return datetime.now(timezone.utc)


class ClinicalStudy(Base):
    __tablename__ = "clinical_studies"

    id               = Column(Integer, primary_key=True, index=True)
    study_oid        = Column(String, unique=True, index=True, nullable=False)
    protocol_name    = Column(String, nullable=False)
    phase            = Column(String)
    sponsor          = Column(String)
    therapeutic_area = Column(String)
    objective        = Column(Text)
    status           = Column(String, default="Active")
    created_at       = Column(DateTime, default=_now)

    subjects = relationship("ClinicalSubject", back_populates="study",
                            cascade="all, delete-orphan")


class ClinicalSubject(Base):
    __tablename__ = "clinical_subjects"

    id              = Column(Integer, primary_key=True, index=True)
    study_id        = Column(Integer, ForeignKey("clinical_studies.id"), nullable=False)
    subject_key     = Column(String, index=True, nullable=False)
    site_id         = Column(String)
    site_name       = Column(String)
    age             = Column(Integer)
    sex             = Column(String)
    race            = Column(String)
    enrollment_date = Column(Date)
    status          = Column(String, default="Enrolled")
    created_at      = Column(DateTime, default=_now)

    study  = relationship("ClinicalStudy", back_populates="subjects")
    visits = relationship("ClinicalVisit", back_populates="subject",
                          cascade="all, delete-orphan")


class ClinicalVisit(Base):
    __tablename__ = "clinical_visits"

    id         = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("clinical_subjects.id"), nullable=False)
    visit_oid  = Column(String)
    visit_name = Column(String)
    visit_date = Column(Date)
    status     = Column(String, default="Completed")
    created_at = Column(DateTime, default=_now)

    subject = relationship("ClinicalSubject", back_populates="visits")
    forms   = relationship("ClinicalForm", back_populates="visit",
                           cascade="all, delete-orphan")


class ClinicalForm(Base):
    __tablename__ = "clinical_forms"

    id         = Column(Integer, primary_key=True, index=True)
    visit_id   = Column(Integer, ForeignKey("clinical_visits.id"), nullable=False)
    form_oid   = Column(String)
    form_name  = Column(String)
    data_json  = Column(Text)
    created_at = Column(DateTime, default=_now)

    visit = relationship("ClinicalVisit", back_populates="forms")


class QueryLog(Base):
    """
    Logs every RAG and SQL query for observability and user feedback collection.
    """
    __tablename__ = "query_logs"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=True)
    query_type       = Column(String(20), nullable=False)   # 'vector' | 'sql'
    question         = Column(Text, nullable=False)
    answer           = Column(Text)
    sql_generated    = Column(Text, nullable=True)
    heal_attempts    = Column(Integer, default=0)
    row_count        = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    feedback         = Column(SmallInteger, nullable=True)  # 1=thumbs up, -1=thumbs down
    created_at       = Column(DateTime, default=_now)


class DocumentChunk(Base):
    """
    Stores text chunks with pgvector embeddings for RAG retrieval.
    The 'embedding' column is a vector(768) type in PostgreSQL (set via raw DDL
    in migration 003). SQLAlchemy sees it as Text at the ORM level; all vector
    operations use raw SQL with db.execute(text(...)).
    """
    __tablename__ = "document_chunks"

    id            = Column(Integer, primary_key=True, index=True)
    source_type   = Column(String, index=True, nullable=False)
    source_id     = Column(Integer, index=True, nullable=False)
    chunk_text    = Column(Text, nullable=False)
    embedding     = Column(Text)        # real type: vector(768) — set via raw DDL
    metadata_json = Column(Text)
    created_at    = Column(DateTime, default=_now)


class PendingIngestion(Base):
    """
    Queue table for auto-vectorization. Postgres triggers on clinical tables
    insert rows here on INSERT/UPDATE. A background worker drains this queue,
    chunking and embedding each row into document_chunks.
    """
    __tablename__ = "pending_ingestion"

    id         = Column(Integer, primary_key=True, index=True)
    table_name = Column(String, nullable=False)    # e.g. 'clinical_subjects'
    row_id     = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_now)


class UserMemory(Base):
    """
    Postgres-native per-user memory for RAG context enrichment.
    Replaces the external Mem0 cloud service. Stores extracted facts from
    conversations with pgvector embeddings for semantic search.
    The 'embedding' column is vector(768) in PostgreSQL (set via raw DDL
    alongside document_chunks). SQLAlchemy sees it as Text.
    """
    __tablename__ = "user_memories"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    memory_text = Column(Text, nullable=False)
    embedding   = Column(Text)          # real type: vector(768) — set via raw DDL
    created_at  = Column(DateTime, default=_now)
    updated_at  = Column(DateTime, default=_now, onupdate=_now)
