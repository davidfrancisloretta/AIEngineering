"""
Ingestion service: builds text chunks from the clinical database,
embeds them via Ollama, and stores them in document_chunks for RAG retrieval.
"""
import json

from sqlalchemy.orm import Session
from sqlalchemy import text
import opik

from models_clinical import (
    ClinicalStudy, ClinicalSubject, ClinicalVisit,
    ClinicalForm, DocumentChunk,
)
from services.llm import embed_text


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


@opik.track(name="ingestion")
def ingest_all(db: Session) -> int:
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

    db.commit()
    return count
