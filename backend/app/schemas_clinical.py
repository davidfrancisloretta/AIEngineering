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
    log_id:  Optional[int] = None


class RAGIngestResponse(BaseModel):
    chunks_created: int
    message:        str


class RAGStatusResponse(BaseModel):
    ollama_ready: bool
    chunk_count:  int
    embed_model:  str
    llm_model:    str
    embed_cache_hits: Optional[int] = None
    embed_cache_size: Optional[int] = None


# ── Text-to-SQL ────────────────────────────────────────────────────────────────

class ConversationMessage(BaseModel):
    role:    str        # "user" or "assistant"
    content: str
    sql:     str = ""   # the SQL that was executed for this turn (if any)


class SQLQueryRequest(BaseModel):
    question: str
    history:  list[ConversationMessage] = []


class SQLQueryResponse(BaseModel):
    answer:        str
    sql:           str
    columns:       list[str]
    rows:          list[list]
    row_count:     int
    model:         str
    heal_attempts: int = 0
    log_id:        Optional[int] = None


class FeedbackRequest(BaseModel):
    feedback: int   # 1 = thumbs up, -1 = thumbs down


# ── ODM Upload ──────────────────────────────────────────────────────────────

class ODMUploadResponse(BaseModel):
    study:    str
    subjects: int
    visits:   int
    forms:    int
    warnings: list[str] = []
    message:  str


# ── Ingestion Status ─────────────────────────────────────────────────────────

class RAGIngestStatusResponse(BaseModel):
    status:         str            # idle | running | done | error
    done:           int
    total:          int
    chunks_created: int
    error:          Optional[str] = None


# ── Analytics ────────────────────────────────────────────────────────────────

class RAGAnalyticsSummary(BaseModel):
    total_queries:   int
    vector_queries:  int
    sql_queries:     int
    avg_response_ms: float
    thumbs_up:       int
    thumbs_down:     int
    unrated:         int


class RAGDailyStats(BaseModel):
    day:        str
    query_type: str
    count:      int
    avg_ms:     float


class RAGTopQuestion(BaseModel):
    question:   str
    count:      int
    avg_ms:     float
    avg_s:      str  # formatted seconds (e.g., "1.23s")
    thumbs_up:  int
    thumbs_down: int
