"""
Ingestion service: builds text chunks from the clinical database,
embeds them via Ollama, and stores them in document_chunks for RAG retrieval.

Auto-vectorization: process_pending() drains the pending_ingestion queue
populated by Postgres triggers on clinical tables.
"""
import json
import logging

from sqlalchemy.orm import Session
from sqlalchemy import text
import opik

from models_clinical import (
    ClinicalStudy, ClinicalSubject, ClinicalVisit,
    ClinicalForm, DocumentChunk,
)
from services.llm import embed_text

log = logging.getLogger("ingestion")


def _vector_literal(embedding: list[float]) -> str:
    """Format a Python list as a pgvector string literal '[0.1,0.2,...]'."""
    return "[" + ",".join(str(v) for v in embedding) + "]"


def _upsert_chunk(
    db: Session,
    source_type: str,
    source_id: int,
    chunk_text: str,
    metadata: dict,
) -> None:
    """
    Delete any existing chunk for this source, embed the text, and insert a new row.
    Uses raw SQL for the vector INSERT because SQLAlchemy does not know the vector type.
    """
    db.execute(
        text(
            "DELETE FROM document_chunks "
            "WHERE source_type = :st AND source_id = :sid"
        ),
        {"st": source_type, "sid": source_id},
    )

    vector      = embed_text(chunk_text)
    vector_str  = _vector_literal(vector)
    meta_str    = json.dumps(metadata)

    db.execute(
        text(
            """
            INSERT INTO document_chunks
                (source_type, source_id, chunk_text, embedding, metadata_json, created_at)
            VALUES
                (:source_type, :source_id, :chunk_text,
                 CAST(:embedding AS vector), :metadata_json, NOW())
            """
        ),
        {
            "source_type":  source_type,
            "source_id":    source_id,
            "chunk_text":   chunk_text,
            "embedding":    vector_str,
            "metadata_json": meta_str,
        },
    )


def count_expected_chunks(db: Session) -> int:
    """Estimate the total number of chunks ingest_all() will create (lower bound)."""
    studies  = db.query(ClinicalStudy).count()
    subjects = db.query(ClinicalSubject).count()
    visits   = db.query(ClinicalVisit).count()
    return max(studies + subjects + int(visits * 2.5), 1)


@opik.track(name="ingestion")
def ingest_all(db: Session, on_progress=None) -> int:
    """
    Build all text chunks from clinical data and embed them.
    Returns the total number of chunks created.

    Chunk types:
      - study:         one per study
      - subject:       one per subject
      - visit:         one per visit (includes vital signs)
      - adverse_event: one per AE event
      - lab:           one per visit with abnormal lab values
    """
    count   = 0
    studies = db.query(ClinicalStudy).all()

    for study in studies:
        # ── Study chunk ──────────────────────────────────────────────────────
        text_study = (
            f"Clinical study {study.study_oid}. "
            f"Protocol: {study.protocol_name}. "
            f"Phase: {study.phase}. Sponsor: {study.sponsor}. "
            f"Therapeutic area: {study.therapeutic_area}. "
            f"Objective: {study.objective}. "
            f"Current status: {study.status}."
        )
        _upsert_chunk(db, "study", study.id, text_study,
                      {"study_oid": study.study_oid})
        count += 1
        if on_progress:
            on_progress(count)

        subjects = (
            db.query(ClinicalSubject)
            .filter(ClinicalSubject.study_id == study.id)
            .all()
        )

        for subj in subjects:
            # ── Subject chunk ─────────────────────────────────────────────────
            text_subj = (
                f"Subject {subj.subject_key} enrolled in study {study.study_oid}. "
                f"Site: {subj.site_name} ({subj.site_id}). "
                f"Age: {subj.age} years, Sex: {subj.sex}, Race: {subj.race}. "
                f"Enrollment date: {subj.enrollment_date}. "
                f"Subject status: {subj.status}."
            )
            _upsert_chunk(db, "subject", subj.id, text_subj,
                          {"study_oid": study.study_oid,
                           "subject_key": subj.subject_key,
                           "site": subj.site_name})
            count += 1
            if on_progress:
                on_progress(count)

            visits = (
                db.query(ClinicalVisit)
                .filter(ClinicalVisit.subject_id == subj.id)
                .all()
            )

            for visit in visits:
                forms     = (
                    db.query(ClinicalForm)
                    .filter(ClinicalForm.visit_id == visit.id)
                    .all()
                )
                form_data = {
                    f.form_oid: json.loads(f.data_json)
                    for f in forms if f.data_json
                }

                # ── Visit / Vitals chunk ──────────────────────────────────────
                vs = form_data.get("VS", {})
                text_visit = (
                    f"Subject {subj.subject_key} attended visit '{visit.visit_name}' "
                    f"on {visit.visit_date} at {subj.site_name}. "
                    f"Visit status: {visit.status}. "
                )
                if vs:
                    text_visit += (
                        f"Vital signs recorded: "
                        f"heart rate {vs.get('heart_rate')} bpm, "
                        f"blood pressure {vs.get('systolic_bp')}/{vs.get('diastolic_bp')} mmHg, "
                        f"temperature {vs.get('temperature')} C, "
                        f"weight {vs.get('weight')} kg, "
                        f"height {vs.get('height')} cm."
                    )
                _upsert_chunk(db, "visit", visit.id, text_visit,
                              {"study_oid": study.study_oid,
                               "subject_key": subj.subject_key,
                               "visit_name": visit.visit_name,
                               "visit_date": str(visit.visit_date)})
                count += 1
                if on_progress:
                    on_progress(count)

                # ── Adverse event chunks (one per event) ──────────────────────
                ae_events = form_data.get("AE", {}).get("events", [])
                for ae_idx, ae in enumerate(ae_events):
                    text_ae = (
                        f"Adverse event reported for subject {subj.subject_key} "
                        f"at visit '{visit.visit_name}' ({visit.visit_date}): "
                        f"{ae.get('term')}. "
                        f"Severity: {ae.get('severity')}. "
                        f"Relationship to study drug: {ae.get('relationship')}. "
                        f"Outcome: {ae.get('outcome')}."
                    )
                    # Use a unique source_id derived from visit + index
                    _upsert_chunk(
                        db, "adverse_event",
                        visit.id * 100 + ae_idx,
                        text_ae,
                        {"study_oid":    study.study_oid,
                         "subject_key":  subj.subject_key,
                         "visit_name":   visit.visit_name,
                         "ae_term":      ae.get("term"),
                         "ae_severity":  ae.get("severity")},
                    )
                    count += 1
                    if on_progress:
                        on_progress(count)

                # ── Abnormal lab chunk (one per visit if any abnormals) ────────
                lb_results = form_data.get("LB", {}).get("results", [])
                abnormal   = [r for r in lb_results if r.get("flag") not in ("N", None)]
                if abnormal:
                    lab_lines = ", ".join(
                        f"{r['name']} {r['value']} {r['unit']} (flag: {r['flag']})"
                        for r in abnormal
                    )
                    text_lab = (
                        f"Abnormal laboratory results for subject {subj.subject_key} "
                        f"at visit '{visit.visit_name}' ({visit.visit_date}): "
                        f"{lab_lines}."
                    )
                    _upsert_chunk(
                        db, "lab",
                        visit.id * 1000,
                        text_lab,
                        {"study_oid":   study.study_oid,
                         "subject_key": subj.subject_key,
                         "visit_name":  visit.visit_name},
                    )
                    count += 1
                    if on_progress:
                        on_progress(count)

    db.commit()
    return count


# ── Auto-vectorization: drain pending_ingestion queue ─────────────────────────

def _chunk_subject(db: Session, row_id: int) -> None:
    """Re-chunk a single clinical subject by id."""
    subj: ClinicalSubject | None = db.query(ClinicalSubject).get(row_id)
    if not subj:
        return
    study: ClinicalStudy | None = db.query(ClinicalStudy).get(subj.study_id)
    study_oid: str = study.study_oid if study else "unknown"

    chunk_text: str = (
        f"Subject {subj.subject_key} enrolled in study {study_oid}. "
        f"Site: {subj.site_name} ({subj.site_id}). "
        f"Age: {subj.age} years, Sex: {subj.sex}, Race: {subj.race}. "
        f"Enrollment date: {subj.enrollment_date}. "
        f"Subject status: {subj.status}."
    )
    _upsert_chunk(db, "subject", subj.id, chunk_text,
                  {"study_oid": study_oid,
                   "subject_key": subj.subject_key,
                   "site": subj.site_name})


def _chunk_visit(db: Session, row_id: int) -> None:
    """Re-chunk a single visit (including vitals, AEs, and labs)."""
    visit: ClinicalVisit | None = db.query(ClinicalVisit).get(row_id)
    if not visit:
        return
    subj: ClinicalSubject | None = db.query(ClinicalSubject).get(visit.subject_id)
    if not subj:
        return
    study: ClinicalStudy | None = db.query(ClinicalStudy).get(subj.study_id)
    study_oid: str = study.study_oid if study else "unknown"

    forms = db.query(ClinicalForm).filter(ClinicalForm.visit_id == visit.id).all()
    form_data: dict = {
        f.form_oid: json.loads(f.data_json)
        for f in forms if f.data_json
    }

    # Visit / vitals chunk
    vs: dict = form_data.get("VS", {})
    text_visit: str = (
        f"Subject {subj.subject_key} attended visit '{visit.visit_name}' "
        f"on {visit.visit_date} at {subj.site_name}. "
        f"Visit status: {visit.status}. "
    )
    if vs:
        text_visit += (
            f"Vital signs recorded: "
            f"heart rate {vs.get('heart_rate')} bpm, "
            f"blood pressure {vs.get('systolic_bp')}/{vs.get('diastolic_bp')} mmHg, "
            f"temperature {vs.get('temperature')} C, "
            f"weight {vs.get('weight')} kg, "
            f"height {vs.get('height')} cm."
        )
    _upsert_chunk(db, "visit", visit.id, text_visit,
                  {"study_oid": study_oid,
                   "subject_key": subj.subject_key,
                   "visit_name": visit.visit_name,
                   "visit_date": str(visit.visit_date)})

    # AE chunks
    ae_events: list = form_data.get("AE", {}).get("events", [])
    for ae_idx, ae in enumerate(ae_events):
        text_ae: str = (
            f"Adverse event reported for subject {subj.subject_key} "
            f"at visit '{visit.visit_name}' ({visit.visit_date}): "
            f"{ae.get('term')}. "
            f"Severity: {ae.get('severity')}. "
            f"Relationship to study drug: {ae.get('relationship')}. "
            f"Outcome: {ae.get('outcome')}."
        )
        _upsert_chunk(db, "adverse_event", visit.id * 100 + ae_idx, text_ae,
                      {"study_oid": study_oid,
                       "subject_key": subj.subject_key,
                       "visit_name": visit.visit_name,
                       "ae_term": ae.get("term"),
                       "ae_severity": ae.get("severity")})

    # Abnormal lab chunk
    lb_results: list = form_data.get("LB", {}).get("results", [])
    abnormal: list = [r for r in lb_results if r.get("flag") not in ("N", None)]
    if abnormal:
        lab_lines: str = ", ".join(
            f"{r['name']} {r['value']} {r['unit']} (flag: {r['flag']})"
            for r in abnormal
        )
        text_lab: str = (
            f"Abnormal laboratory results for subject {subj.subject_key} "
            f"at visit '{visit.visit_name}' ({visit.visit_date}): "
            f"{lab_lines}."
        )
        _upsert_chunk(db, "lab", visit.id * 1000, text_lab,
                      {"study_oid": study_oid,
                       "subject_key": subj.subject_key,
                       "visit_name": visit.visit_name})


def _chunk_form(db: Session, row_id: int) -> None:
    """Re-chunk the parent visit when a form is inserted/updated."""
    form: ClinicalForm | None = db.query(ClinicalForm).get(row_id)
    if not form:
        return
    # Delegate to visit chunker — it reads all forms for the visit
    _chunk_visit(db, form.visit_id)


# Dispatch table: table_name → chunker function
_CHUNKERS: dict[str, callable] = {
    "clinical_subjects": _chunk_subject,
    "clinical_visits":   _chunk_visit,
    "clinical_forms":    _chunk_form,
}


def process_pending(db: Session, batch_size: int = 50) -> int:
    """
    Drain the pending_ingestion queue. For each pending row, re-chunk the
    corresponding clinical record and upsert into document_chunks.
    Returns the number of rows processed.
    """
    rows = db.execute(
        text("""
            DELETE FROM pending_ingestion
            WHERE id IN (
                SELECT id FROM pending_ingestion
                ORDER BY created_at
                LIMIT :batch
            )
            RETURNING table_name, row_id
        """),
        {"batch": batch_size},
    ).fetchall()

    if not rows:
        return 0

    processed: int = 0
    for row in rows:
        chunker = _CHUNKERS.get(row.table_name)
        if chunker:
            try:
                chunker(db, row.row_id)
                processed += 1
            except Exception as exc:
                log.warning(
                    "Auto-ingest failed for %s id=%d: %s",
                    row.table_name, row.row_id, exc,
                )

    db.commit()
    return processed


def get_pending_count(db: Session) -> int:
    """Return the number of rows waiting in the ingestion queue."""
    result = db.execute(text("SELECT COUNT(*) FROM pending_ingestion")).scalar()
    return result or 0
