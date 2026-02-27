"""
Pydantic schemas for clinical trial data and RAG endpoints.
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


# ── Clinical Study ─────────────────────────────────────────────────────────────

class StudyResponse(BaseModel):
    id:               int
    study_oid:        str
    protocol_name:    str
    phase:            Optional[str] = None
    sponsor:          Optional[str] = None
    therapeutic_area: Optional[str] = None
    objective:        Optional[str] = None
    status:           Optional[str] = None
    created_at:       Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Clinical Subject ───────────────────────────────────────────────────────────

class SubjectResponse(BaseModel):
    id:              int
    study_id:        int
    subject_key:     str
    site_id:         Optional[str] = None
    site_name:       Optional[str] = None
    age:             Optional[int] = None
    sex:             Optional[str] = None
    race:            Optional[str] = None
    enrollment_date: Optional[date] = None
    status:          Optional[str] = None

    class Config:
        from_attributes = True


# ── Clinical Visit ─────────────────────────────────────────────────────────────

class VisitResponse(BaseModel):
    id:         int
    subject_id: int
    visit_oid:  Optional[str] = None
    visit_name: Optional[str] = None
    visit_date: Optional[date] = None
    status:     Optional[str] = None

    class Config:
        from_attributes = True


# ── Clinical Form ──────────────────────────────────────────────────────────────

class FormResponse(BaseModel):
    id:        int
    visit_id:  int
    form_oid:  Optional[str] = None
    form_name: Optional[str] = None
    data_json: Optional[str] = None

    class Config:
        from_attributes = True


# ── Seed Response ──────────────────────────────────────────────────────────────

class ClinicalSeedResponse(BaseModel):
    study:    str
    subjects: int
    visits:   int
    forms:    int


# ── RAG ────────────────────────────────────────────────────────────────────────

class RAGChatRequest(BaseModel):
    question: str
    top_k:    int = 5


class RAGSourceChunk(BaseModel):
    chunk_text:  str
    source_type: str
    source_id:   int
    similarity:  float


class RAGChatResponse(BaseModel):
    answer:  str
    sources: list[RAGSourceChunk]
    model:   str


class RAGIngestResponse(BaseModel):
    chunks_created: int
    message:        str


class RAGStatusResponse(BaseModel):
    ollama_ready: bool
    chunk_count:  int
    embed_model:  str
    llm_model:    str


# ── ODM Upload ──────────────────────────────────────────────────────────────

class ODMUploadResponse(BaseModel):
    study:    str
    subjects: int
    visits:   int
    forms:    int
    warnings: list[str] = []
    message:  str
