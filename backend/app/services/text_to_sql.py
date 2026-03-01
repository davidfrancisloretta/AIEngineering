"""
Text-to-SQL service for clinical trial data.

Pipeline:
  1. Build schema context (tables + views description)
  2. Send question + schema to llama3.2:3b → generate SQL
  3. Extract and safety-validate SQL (SELECT only)
  4. Execute SQL against PostgreSQL
  5. Send question + results back to LLM → natural language answer
"""
import os
import re
import json
import logging

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("text_to_sql")

OLLAMA_BASE = os.getenv("OLLAMA_URL", "http://ollama:11434")
SQL_MODEL   = os.getenv("OLLAMA_SQL_MODEL", "llama3.2:3b")
MAX_ROWS    = 100


# ── SQL Views ──────────────────────────────────────────────────────────────────

_CREATE_VIEWS_SQL = """
-- Generic: every form item as a key-value row (works for Rave and demo data)
CREATE OR REPLACE VIEW v_form_items AS
SELECT
    cs.study_oid,
    s.subject_key,
    s.site_id,
    s.site_name,
    s.status   AS subject_status,
    v.visit_name,
    v.visit_date,
    f.form_oid,
    f.form_name,
    item.key   AS item_name,
    item.value #>> '{}'  AS item_value
FROM clinical_forms f
JOIN clinical_visits   v  ON v.id  = f.visit_id
JOIN clinical_subjects s  ON s.id  = v.subject_id
JOIN clinical_studies  cs ON cs.id = s.study_id
CROSS JOIN jsonb_each(f.data_json::jsonb) AS item
WHERE f.data_json IS NOT NULL
  AND f.data_json <> '{}'
  AND item.key NOT LIKE '\\_%';

-- Demo data: Vital Signs (form_oid = 'VS')
CREATE OR REPLACE VIEW v_vital_signs AS
SELECT
    cs.study_oid,
    s.subject_key,
    s.site_id,
    s.site_name,
    v.visit_name,
    v.visit_date,
    (f.data_json::jsonb->>'heart_rate')::numeric    AS heart_rate,
    (f.data_json::jsonb->>'systolic_bp')::numeric   AS systolic_bp,
    (f.data_json::jsonb->>'diastolic_bp')::numeric  AS diastolic_bp,
    (f.data_json::jsonb->>'temperature')::numeric   AS temperature,
    (f.data_json::jsonb->>'weight')::numeric        AS weight
FROM clinical_forms f
JOIN clinical_visits   v  ON v.id  = f.visit_id
JOIN clinical_subjects s  ON s.id  = v.subject_id
JOIN clinical_studies  cs ON cs.id = s.study_id
WHERE f.form_oid = 'VS';

-- Demo data: Adverse Events (form_oid = 'AE', events is a JSON array)
CREATE OR REPLACE VIEW v_adverse_events AS
SELECT
    cs.study_oid,
    s.subject_key,
    s.site_id,
    s.site_name,
    v.visit_name,
    v.visit_date,
    event->>'term'         AS ae_term,
    event->>'severity'     AS severity,
    event->>'relationship' AS drug_relationship,
    event->>'outcome'      AS outcome
FROM clinical_forms f
JOIN clinical_visits   v  ON v.id  = f.visit_id
JOIN clinical_subjects s  ON s.id  = v.subject_id
JOIN clinical_studies  cs ON cs.id = s.study_id
CROSS JOIN jsonb_array_elements(f.data_json::jsonb->'events') AS event
WHERE f.form_oid = 'AE'
  AND f.data_json::jsonb ? 'events';

-- Demo data: Lab Results (form_oid = 'LB', results is a JSON array)
CREATE OR REPLACE VIEW v_lab_results AS
SELECT
    cs.study_oid,
    s.subject_key,
    s.site_id,
    s.site_name,
    v.visit_name,
    v.visit_date,
    result->>'name'              AS test_name,
    result->>'test'              AS test_code,
    (result->>'value')::numeric  AS value,
    result->>'unit'              AS unit,
    result->>'flag'              AS flag
FROM clinical_forms f
JOIN clinical_visits   v  ON v.id  = f.visit_id
JOIN clinical_subjects s  ON s.id  = v.subject_id
JOIN clinical_studies  cs ON cs.id = s.study_id
CROSS JOIN jsonb_array_elements(f.data_json::jsonb->'results') AS result
WHERE f.form_oid = 'LB'
  AND f.data_json::jsonb ? 'results';
"""

# ── Schema context injected into every LLM prompt ─────────────────────────────

_SCHEMA_CONTEXT = """
PostgreSQL clinical trial database.

TABLES:
  clinical_studies(id, study_oid, protocol_name, phase, sponsor, therapeutic_area, status)
  clinical_subjects(id, study_id, subject_key, site_id, site_name, age, sex, race, enrollment_date, status)
  clinical_visits(id, subject_id, visit_oid, visit_name, visit_date, status)
  clinical_forms(id, visit_id, form_oid, form_name, data_json)

VIEWS (prefer these for analysis):
  v_form_items(study_oid, subject_key, site_id, site_name, subject_status,
               visit_name, visit_date, form_oid, form_name, item_name, item_value)
    -- All form data as flat key-value rows; works for Rave and demo data.

  v_vital_signs(study_oid, subject_key, site_id, site_name,
                visit_name, visit_date, heart_rate, systolic_bp, diastolic_bp,
                temperature, weight)
    -- Demo data only (CARDIO-2024 study).

  v_adverse_events(study_oid, subject_key, site_id, site_name,
                   visit_name, visit_date, ae_term, severity,
                   drug_relationship, outcome)
    -- Demo data only (CARDIO-2024 study).

  v_lab_results(study_oid, subject_key, site_id, site_name,
                visit_name, visit_date, test_name, test_code, value, unit, flag)
    -- Demo data only (CARDIO-2024 study). flag: N=normal, H=high, L=low, HH/LL=critical.

RULES:
  - Write a single SELECT query only.
  - Always add LIMIT {max_rows} unless the user asks for counts/aggregates.
  - Use v_form_items for Rave data (B_Demostudy) since it has no VS/AE/LB views.
  - subject_key in Rave data is a UUID; item_name/item_value hold the actual data.
""".format(max_rows=MAX_ROWS)


# ── View creation ──────────────────────────────────────────────────────────────

def ensure_views(db: Session) -> None:
    """Create or replace all analytical views. Called on app startup."""
    try:
        db.execute(text(_CREATE_VIEWS_SQL))
        db.commit()
        log.info("Text-to-SQL views created/updated.")
    except Exception as exc:
        db.rollback()
        log.error("Failed to create views: %s", exc)


# ── SQL extraction from LLM response ──────────────────────────────────────────

def _extract_sql(response: str) -> str:
    """Pull the SQL statement out of an LLM response."""
    # Try fenced code block first: ```sql ... ```
    m = re.search(r"```(?:sql)?\s*(SELECT[\s\S]*?)```", response, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Try bare SELECT ... ; pattern
    m = re.search(r"(SELECT\s[\s\S]+?);?\s*$", response, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Fallback: return everything after the first SELECT keyword
    idx = response.upper().find("SELECT")
    if idx != -1:
        return response[idx:].strip()

    return response.strip()


def _is_safe(sql: str) -> bool:
    """Reject any non-SELECT or DDL/DML statements."""
    upper = re.sub(r"\s+", " ", sql).strip().upper()
    if not upper.startswith("SELECT"):
        return False
    dangerous = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
                 "ALTER", "TRUNCATE", "GRANT", "REVOKE", "EXEC")
    return not any(f" {kw} " in f" {upper} " for kw in dangerous)


# ── Ollama calls ───────────────────────────────────────────────────────────────

def _ollama_generate(prompt: str, system: str = "") -> str:
    payload: dict = {
        "model":  SQL_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        raise RuntimeError(f"Ollama error ({SQL_MODEL}): {exc}") from exc


def _model_ready() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        return any(SQL_MODEL in m for m in models)
    except Exception:
        return False


# ── Main pipeline ──────────────────────────────────────────────────────────────

def sql_chat(db: Session, question: str) -> dict:
    """
    Full Text-to-SQL pipeline.

    Returns:
      {
        "answer":  str,          # natural language answer
        "sql":     str,          # generated SQL
        "columns": [str, ...],   # result column names
        "rows":    [[...], ...], # result rows (lists)
        "row_count": int,
        "model":   str,
      }
    """
    if not _model_ready():
        raise RuntimeError(
            f"Model '{SQL_MODEL}' is not yet available in Ollama. "
            "It may still be downloading — please wait a few minutes and retry."
        )

    # ── Step 1: Generate SQL ────────────────────────────────────────────────
    sql_prompt = (
        f"Schema:\n{_SCHEMA_CONTEXT}\n\n"
        f"Question: {question}\n\n"
        "SQL query:"
    )
    sql_system = (
        "You are a PostgreSQL expert. "
        "Given a schema and a question, output ONLY a valid SQL SELECT query. "
        "No explanations, no markdown, just the SQL."
    )
    raw_sql_response = _ollama_generate(sql_prompt, system=sql_system)
    generated_sql    = _extract_sql(raw_sql_response)

    if not _is_safe(generated_sql):
        raise ValueError(
            f"Generated SQL is not a safe SELECT statement:\n{generated_sql}"
        )

    # ── Step 2: Execute SQL ─────────────────────────────────────────────────
    try:
        result  = db.execute(text(generated_sql))
        columns = list(result.keys())
        rows    = [list(row) for row in result.fetchmany(MAX_ROWS)]
    except Exception as exc:
        raise ValueError(f"SQL execution failed: {exc}\n\nGenerated SQL:\n{generated_sql}") from exc

    # ── Step 3: Generate natural language answer ────────────────────────────
    if rows:
        # Build a compact table string for the LLM
        header   = " | ".join(columns)
        divider  = "-" * len(header)
        data_str = "\n".join(" | ".join(str(v) for v in row) for row in rows[:20])
        results_text = f"{header}\n{divider}\n{data_str}"
        if len(rows) > 20:
            results_text += f"\n... ({len(rows)} rows total, showing first 20)"
    else:
        results_text = "(no rows returned)"

    answer_prompt = (
        f"Question: {question}\n\n"
        f"SQL executed:\n{generated_sql}\n\n"
        f"Results:\n{results_text}\n\n"
        "Answer:"
    )
    answer_system = (
        "You are a clinical trial data analyst. "
        "Given a question, the SQL that was run, and the query results, "
        "provide a concise, accurate answer in plain English. "
        "Reference specific numbers and findings from the data."
    )
    answer = _ollama_generate(answer_prompt, system=answer_system)

    return {
        "answer":    answer,
        "sql":       generated_sql,
        "columns":   columns,
        "rows":      rows,
        "row_count": len(rows),
        "model":     SQL_MODEL,
    }
