"""
CDISC ODM XML parser for Medidata Rave data.

Supports:
  - ODM 1.3 standard (http://www.cdisc.org/ns/odm/v1.3)
  - Medidata Rave extensions (mdsol namespace)
  - ClinicalAuditRecords.odm format
  - Standard clinical data export format

Maps to existing clinical tables:
  clinical_studies, clinical_subjects, clinical_visits, clinical_forms
"""
import json
import re
from datetime import date, datetime
from typing import Optional
import xml.etree.ElementTree as ET

from sqlalchemy.orm import Session

from models_clinical import ClinicalStudy, ClinicalSubject, ClinicalVisit, ClinicalForm

# Common CDISC demographic item OID fragments (case-insensitive match)
_AGE_KEYS        = ("AGE", "AGEBIRTH")
_SEX_KEYS        = ("SEX", "GENDER")
_RACE_KEYS       = ("RACE",)
_ENROLL_KEYS     = ("ENRDT", "RFSTDTC", "ICFDAT", "BRTHDAT", "RFICDTC")


# ---------------------------------------------------------------------------
# Namespace-agnostic helpers
# ---------------------------------------------------------------------------

def _local(tag: str) -> str:
    """Strip Clark-notation namespace from tag: {ns}local → local."""
    return tag.split("}")[-1] if "}" in tag else tag


def _find(elem: ET.Element, local_name: str) -> Optional[ET.Element]:
    """Find first DIRECT child matching local name, ignoring namespace."""
    for child in elem:
        if _local(child.tag) == local_name:
            return child
    return None


def _findall(elem: ET.Element, local_name: str) -> list:
    """Find all DIRECT children matching local name, ignoring namespace."""
    return [child for child in elem if _local(child.tag) == local_name]


def _iterlocal(elem: ET.Element, local_name: str):
    """Iterate ALL descendants matching local name, ignoring namespace."""
    for el in elem.iter():
        if _local(el.tag) == local_name:
            yield el


def _attr(elem: ET.Element, *names: str) -> Optional[str]:
    """Return first matching attribute value, trying plain name and all
    Clark-notation variants found on the element."""
    for name in names:
        # Plain attribute
        v = elem.get(name)
        if v:
            return v.strip()
        # Try any namespace variant: scan all attrib keys
        for k, v in elem.attrib.items():
            if _local(k) == name and v:
                return v.strip()
    return None


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10]).date()
    except Exception:
        return None


def _match_key(oid: str, keys: tuple) -> bool:
    upper = oid.upper()
    return any(k in upper for k in keys)


def _clean_text(value: str) -> str:
    return (value or "").strip()


# ---------------------------------------------------------------------------
# Study-level metadata
# ---------------------------------------------------------------------------

def _extract_study_meta(study_elem: ET.Element) -> dict:
    oid         = _attr(study_elem, "OID") or "UNKNOWN"
    global_vars = _find(study_elem, "GlobalVariables")

    name = protocol = description = ""
    if global_vars is not None:
        name_el  = _find(global_vars, "StudyName")
        proto_el = _find(global_vars, "ProtocolName")
        desc_el  = _find(global_vars, "StudyDescription")
        name        = _clean_text(name_el.text)  if name_el  is not None else oid
        protocol    = _clean_text(proto_el.text) if proto_el is not None else oid
        description = _clean_text(desc_el.text)  if desc_el  is not None else ""

    phase   = _guess_phase(oid + " " + description)
    sponsor = _guess_sponsor(oid + " " + description)

    return {
        "study_oid":        oid,
        "protocol_name":    protocol or name or oid,
        "phase":            phase,
        "sponsor":          sponsor,
        "therapeutic_area": _guess_ta(oid + " " + description),
        "objective":        description[:500] if description else None,
        "status":           "Active",
    }


def _guess_phase(text: str) -> Optional[str]:
    m = re.search(r"phase\s*(i{1,3}v?|[1-4])", text, re.IGNORECASE)
    if m:
        raw = m.group(1).upper()
        mapping = {"1": "Phase I", "2": "Phase II", "3": "Phase III", "4": "Phase IV",
                   "I": "Phase I", "II": "Phase II", "III": "Phase III", "IV": "Phase IV"}
        return mapping.get(raw, f"Phase {raw}")
    return None


def _guess_sponsor(text: str) -> Optional[str]:
    m = re.search(r"(sponsor|company|pharma|biotech)[:\s]+([A-Za-z0-9 &]+)", text, re.IGNORECASE)
    return m.group(2).strip()[:100] if m else None


def _guess_ta(text: str) -> Optional[str]:
    areas = {
        "cardio": "Cardiovascular", "cardiac": "Cardiovascular", "heart": "Cardiovascular",
        "onco": "Oncology", "cancer": "Oncology", "tumor": "Oncology",
        "neuro": "Neurology", "alzheimer": "Neurology", "parkinson": "Neurology",
        "diabet": "Endocrinology", "insulin": "Endocrinology",
        "immun": "Immunology", "rheumat": "Immunology",
        "infect": "Infectious Disease", "covid": "Infectious Disease", "hiv": "Infectious Disease",
        "respir": "Respiratory", "pulmon": "Respiratory", "asthma": "Respiratory",
    }
    lower = text.lower()
    for key, area in areas.items():
        if key in lower:
            return area
    return None


# ---------------------------------------------------------------------------
# MetaDataVersion — form / item label lookup maps
# ---------------------------------------------------------------------------

def _build_label_maps(study_elem: ET.Element) -> tuple:
    form_labels: dict = {}
    item_labels: dict = {}

    for mdv in _iterlocal(study_elem, "MetaDataVersion"):
        for fd in _findall(mdv, "FormDef"):
            oid  = _attr(fd, "OID") or ""
            name = _attr(fd, "Name") or oid
            form_labels[oid] = name

        for idef in _iterlocal(mdv, "ItemDef"):
            oid      = _attr(idef, "OID") or ""
            name     = _attr(idef, "Name") or ""
            question = next(_iterlocal(idef, "TranslatedText"), None)
            label    = (question.text.strip()
                        if question is not None and question.text else name) or oid
            item_labels[oid] = label

    return form_labels, item_labels


# ---------------------------------------------------------------------------
# Demographics extraction
# ---------------------------------------------------------------------------

def _extract_demographics(subject_elem: ET.Element, item_labels: dict) -> dict:
    demo: dict = {}
    for item_data in _iterlocal(subject_elem, "ItemData"):
        oid   = _attr(item_data, "ItemOID") or ""
        value = _attr(item_data, "Value") or ""
        if not oid or not value:
            continue
        if not demo.get("age") and _match_key(oid, _AGE_KEYS):
            try:
                demo["age"] = int(float(value))
            except ValueError:
                pass
        if not demo.get("sex") and _match_key(oid, _SEX_KEYS):
            demo["sex"] = value[:10]
        if not demo.get("race") and _match_key(oid, _RACE_KEYS):
            demo["race"] = value[:50]
        if not demo.get("enrollment_date") and _match_key(oid, _ENROLL_KEYS):
            demo["enrollment_date"] = _parse_date(value)
    return demo


# ---------------------------------------------------------------------------
# Form data extraction
# ---------------------------------------------------------------------------

def _extract_form_data(form_elem: ET.Element, item_labels: dict) -> dict:
    data: dict = {}
    for ig in _iterlocal(form_elem, "ItemGroupData"):
        for item in _findall(ig, "ItemData"):
            oid   = _attr(item, "ItemOID") or ""
            value = _attr(item, "Value")
            if oid and value is not None:
                label       = item_labels.get(oid, oid)
                data[label] = value
        rk = _attr(ig, "ItemGroupRepeatKey")
        if rk:
            data["_repeat_key"] = rk
    return data


# ---------------------------------------------------------------------------
# Main parse + ingest
# ---------------------------------------------------------------------------

def parse_and_ingest(xml_bytes: bytes, db: Session) -> dict:
    """
    Parse CDISC ODM XML bytes and upsert into clinical tables.
    Uses local-name matching throughout — works regardless of namespace
    declarations in the source file (standard ODM, Rave transactional, etc.).
    """
    import logging
    log = logging.getLogger("odm_parser")

    warnings: list = []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    log.warning("ODM root tag: %s", root.tag)
    all_cd = list(_iterlocal(root, "ClinicalData"))
    log.warning("ClinicalData blocks found: %d", len(all_cd))
    if all_cd:
        first_sd = list(_findall(all_cd[0], "SubjectData"))
        log.warning("SubjectData in first ClinicalData: %d  (children: %s)",
                    len(first_sd),
                    [_local(c.tag) for c in all_cd[0]])

    # ── Study metadata ──────────────────────────────────────────────────────
    study_elem = _find(root, "Study")

    if study_elem is not None:
        form_labels, item_labels = _build_label_maps(study_elem)
        study_meta               = _extract_study_meta(study_elem)
    else:
        form_labels = {}
        item_labels = {}
        cd_elem = next(_iterlocal(root, "ClinicalData"), None)
        if cd_elem is None:
            raise ValueError(
                "No <Study> or <ClinicalData> element found. "
                "File does not appear to be a valid CDISC ODM document."
            )
        raw_oid    = _attr(cd_elem, "StudyOID") or "UNKNOWN"
        study_meta = {
            "study_oid":        raw_oid,
            "protocol_name":    raw_oid,
            "phase":            _guess_phase(raw_oid),
            "sponsor":          None,
            "therapeutic_area": _guess_ta(raw_oid),
            "objective":        f"Imported from Medidata Rave ClinicalAuditRecords — {raw_oid}",
            "status":           "Active",
        }
        warnings.append(
            "File is in ClinicalAuditRecords (transactional) format — "
            "study metadata (phase, sponsor) not available; defaults applied."
        )

    # ── Upsert Study ───────────────────────────────────────────────────────
    study_obj = (
        db.query(ClinicalStudy)
        .filter(ClinicalStudy.study_oid == study_meta["study_oid"])
        .first()
    )
    if not study_obj:
        study_obj = ClinicalStudy(**study_meta)
        db.add(study_obj)
        db.flush()
    else:
        for k, v in study_meta.items():
            if v is not None:
                setattr(study_obj, k, v)
        db.flush()

    study_id = study_obj.id

    # ── Walk ClinicalData → SubjectData → StudyEventData → FormData ────────
    subjects_new    = 0
    subjects_seen   = set()   # track unique keys processed this run
    visits_count    = 0
    forms_count     = 0

    for clinical_data in _iterlocal(root, "ClinicalData"):
        for subject_elem in _findall(clinical_data, "SubjectData"):

            subject_key = _attr(subject_elem, "SubjectKey") or "UNKNOWN"

            site_ref  = _find(subject_elem, "SiteRef")
            site_id   = _attr(site_ref, "LocationOID") if site_ref is not None else None
            site_name = site_id

            demo   = _extract_demographics(subject_elem, item_labels)
            status = _attr(subject_elem, "SubjectStatus") or "Enrolled"

            subj_obj = (
                db.query(ClinicalSubject)
                .filter(
                    ClinicalSubject.study_id    == study_id,
                    ClinicalSubject.subject_key == subject_key,
                )
                .first()
            )
            if not subj_obj:
                subj_obj = ClinicalSubject(
                    study_id    = study_id,
                    subject_key = subject_key,
                    site_id     = site_id,
                    site_name   = site_name,
                    status      = status,
                    **{k: v for k, v in demo.items() if v is not None},
                )
                db.add(subj_obj)
                db.flush()
                subjects_new += 1
            else:
                if site_id:
                    subj_obj.site_id   = site_id
                    subj_obj.site_name = site_name
                for k, v in demo.items():
                    if v is not None:
                        setattr(subj_obj, k, v)
                db.flush()

            subjects_seen.add(subject_key)

            subject_id = subj_obj.id

            for event_elem in _findall(subject_elem, "StudyEventData"):
                visit_oid  = _attr(event_elem, "StudyEventOID") or "VISIT"
                repeat_key = _attr(event_elem, "StudyEventRepeatKey") or "1"
                visit_name = (
                    _attr(event_elem, "InstanceName")   # mdsol extension
                    or visit_oid
                )

                visit_date: Optional[date] = None
                for item in _iterlocal(event_elem, "ItemData"):
                    val = _attr(item, "Value") or ""
                    if re.match(r"\d{4}-\d{2}-\d{2}", val):
                        visit_date = _parse_date(val)
                        break

                unique_visit_oid = f"{visit_oid}_{repeat_key}"

                visit_obj = (
                    db.query(ClinicalVisit)
                    .filter(
                        ClinicalVisit.subject_id == subject_id,
                        ClinicalVisit.visit_oid  == unique_visit_oid,
                    )
                    .first()
                )
                if not visit_obj:
                    visit_obj = ClinicalVisit(
                        subject_id = subject_id,
                        visit_oid  = unique_visit_oid,
                        visit_name = visit_name,
                        visit_date = visit_date,
                        status     = "Complete",
                    )
                    db.add(visit_obj)
                    db.flush()
                    visits_count += 1
                else:
                    if visit_date:
                        visit_obj.visit_date = visit_date
                    visit_obj.visit_name = visit_name
                    db.flush()

                visit_id = visit_obj.id

                for form_elem in _findall(event_elem, "FormData"):
                    form_oid  = _attr(form_elem, "FormOID") or "FORM"
                    form_name = form_labels.get(form_oid, form_oid)
                    form_data = _extract_form_data(form_elem, item_labels)

                    if not form_data:
                        continue

                    form_obj = (
                        db.query(ClinicalForm)
                        .filter(
                            ClinicalForm.visit_id == visit_id,
                            ClinicalForm.form_oid == form_oid,
                        )
                        .first()
                    )
                    if not form_obj:
                        form_obj = ClinicalForm(
                            visit_id  = visit_id,
                            form_oid  = form_oid,
                            form_name = form_name,
                            data_json = json.dumps(form_data),
                        )
                        db.add(form_obj)
                        forms_count += 1
                    else:
                        existing = json.loads(form_obj.data_json or "{}")
                        existing.update(form_data)
                        form_obj.data_json = json.dumps(existing)
                        form_obj.form_name = form_name

    db.commit()

    return {
        "study":    study_meta["study_oid"],
        "subjects": len(subjects_seen),   # total unique subjects processed
        "visits":   visits_count,
        "forms":    forms_count,
        "warnings": warnings,
    }
