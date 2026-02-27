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

# XML namespaces used by CDISC ODM and Medidata Rave
NS_ODM   = "http://www.cdisc.org/ns/odm/v1.3"
NS_MDSOL = "http://www.mdsol.com/ns/odm/metadata"

# Common CDISC demographic item OID fragments (case-insensitive match)
_AGE_KEYS        = ("AGE", "AGEBIRTH")
_SEX_KEYS        = ("SEX", "GENDER")
_RACE_KEYS       = ("RACE",)
_ENROLL_KEYS     = ("ENRDT", "RFSTDTC", "ICFDAT", "BRTHDAT", "RFICDTC")
_SITE_NAME_KEYS  = ("SITENAME", "SITE_NAME", "LOCATIONNAME")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tag(local: str, ns: str = NS_ODM) -> str:
    return f"{{{ns}}}{local}"


def _attr(elem: ET.Element, *names: str, ns: str = "") -> Optional[str]:
    """Return the first matching attribute value, trying with and without namespace."""
    for name in names:
        v = elem.get(name) or elem.get(f"{{{ns}}}{name}" if ns else name)
        if v:
            return v.strip()
    return None


def _parse_date(value: str) -> Optional[date]:
    """Parse ISO-8601 date string to date, tolerating datetime strings."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10]).date()
    except Exception:
        return None


def _match_key(oid: str, keys: tuple) -> bool:
    """Return True if the item OID contains any of the key fragments (case-insensitive)."""
    upper = oid.upper()
    return any(k in upper for k in keys)


def _clean_text(value: str) -> str:
    return (value or "").strip()


# ---------------------------------------------------------------------------
# Study-level metadata extraction
# ---------------------------------------------------------------------------

def _extract_study_meta(study_elem: ET.Element) -> dict:
    """Extract study-level metadata from <Study> element."""
    oid          = _attr(study_elem, "OID") or "UNKNOWN"
    global_vars  = study_elem.find(_tag("GlobalVariables"))

    name         = ""
    protocol     = ""
    description  = ""

    if global_vars is not None:
        name_el  = global_vars.find(_tag("StudyName"))
        proto_el = global_vars.find(_tag("ProtocolName"))
        desc_el  = global_vars.find(_tag("StudyDescription"))
        name        = _clean_text(name_el.text)  if name_el  is not None else oid
        protocol    = _clean_text(proto_el.text) if proto_el is not None else oid
        description = _clean_text(desc_el.text)  if desc_el  is not None else ""

    # Try to extract phase / sponsor from description or oid
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
# MetaDataVersion — collect form/item name lookups
# ---------------------------------------------------------------------------

def _build_label_maps(study_elem: ET.Element) -> tuple[dict, dict]:
    """
    Return (form_labels, item_labels):
      form_labels[form_oid]  = human-readable form name
      item_labels[item_oid]  = human-readable item name / question text
    """
    form_labels: dict[str, str] = {}
    item_labels: dict[str, str] = {}

    for mdv in study_elem.findall(_tag("MetaDataVersion")):
        for fd in mdv.findall(_tag("FormDef")):
            oid  = _attr(fd, "OID") or ""
            name = _attr(fd, "Name") or oid
            form_labels[oid] = name

        for idef in mdv.findall(_tag("ItemDef")):
            oid      = _attr(idef, "OID") or ""
            name     = _attr(idef, "Name") or ""
            question = idef.find(f".//{_tag('TranslatedText')}")
            label    = (question.text.strip() if question is not None and question.text else name) or oid
            item_labels[oid] = label

    return form_labels, item_labels


# ---------------------------------------------------------------------------
# Subject demographics extraction
# ---------------------------------------------------------------------------

def _extract_demographics(subject_elem: ET.Element, item_labels: dict) -> dict:
    """
    Walk all ItemData under the subject and try to map common demographic fields.
    Returns partial dict suitable for ClinicalSubject fields.
    """
    demo: dict = {}

    for item_data in subject_elem.iter(_tag("ItemData")):
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
# Form data extraction — collect all ItemData into a keyed dict
# ---------------------------------------------------------------------------

def _extract_form_data(form_elem: ET.Element, item_labels: dict) -> dict:
    """
    Collect all ItemData values under a FormData element into a flat dict.
    Keys are human-readable labels (from item_labels) or the raw OID.
    """
    data: dict = {}

    for ig in form_elem.iter(_tag("ItemGroupData")):
        for item in ig.findall(_tag("ItemData")):
            oid   = _attr(item, "ItemOID") or ""
            value = _attr(item, "Value")
            if oid and value is not None:
                label       = item_labels.get(oid, oid)
                data[label] = value

    # Also capture repeat key if present (useful for repeating forms like AE)
    ig_repeat = form_elem.find(_tag("ItemGroupData"))
    if ig_repeat is not None:
        rk = _attr(ig_repeat, "ItemGroupRepeatKey")
        if rk:
            data["_repeat_key"] = rk

    return data


# ---------------------------------------------------------------------------
# Main parse + ingest function
# ---------------------------------------------------------------------------

def parse_and_ingest(xml_bytes: bytes, db: Session) -> dict:
    """
    Parse CDISC ODM XML bytes and upsert into clinical tables.

    Returns:
        {
          "study": study_oid,
          "subjects": int,
          "visits": int,
          "forms": int,
          "warnings": [str, ...]
        }
    """
    warnings: list[str] = []

    # ── Parse XML ──────────────────────────────────────────────────────────
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    # Strip default namespace from tag comparisons by normalising the root tag
    # (ElementTree includes namespace in curly braces)
    odm_ns = NS_ODM
    if root.tag == "ODM":
        # No namespace declared — common in some exports
        odm_ns = ""

    def tag(local: str) -> str:
        return f"{{{odm_ns}}}{local}" if odm_ns else local

    # ── Find Study element (optional — absent in ClinicalAuditRecords format) ─
    study_elem = root.find(tag("Study"))
    if study_elem is None:
        study_elem = root.find("Study")

    if study_elem is not None:
        form_labels, item_labels = _build_label_maps(study_elem)
        study_meta               = _extract_study_meta(study_elem)
    else:
        # ClinicalAuditRecords / transactional ODM — derive study OID from
        # the first <ClinicalData StudyOID="..."> attribute
        form_labels  = {}
        item_labels  = {}
        cd_elem      = root.find(tag("ClinicalData"))
        if cd_elem is None:
            cd_elem  = root.find("ClinicalData")
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

    # ── ClinicalData sections ──────────────────────────────────────────────
    subjects_count = 0
    visits_count   = 0
    forms_count    = 0

    for clinical_data in root.iter(tag("ClinicalData")):
        for subject_elem in clinical_data.findall(tag("SubjectData")):

            # Subject key
            subject_key = (
                _attr(subject_elem, "SubjectKey")
                or _attr(subject_elem, "SubjectKey", ns=NS_MDSOL)
                or "UNKNOWN"
            )

            # Site reference
            site_ref  = subject_elem.find(tag("SiteRef"))
            site_id   = _attr(site_ref, "LocationOID") if site_ref is not None else None
            site_name = site_id  # fallback; Rave sometimes puts name in OID

            # Demographics from ItemData
            demo = _extract_demographics(subject_elem, item_labels)

            # Status heuristic
            status = "Enrolled"
            status_raw = _attr(subject_elem, "mdsol:SubjectStatus") or ""
            if status_raw:
                status = status_raw

            # Upsert subject
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
                    study_id        = study_id,
                    subject_key     = subject_key,
                    site_id         = site_id,
                    site_name       = site_name,
                    status          = status,
                    **{k: v for k, v in demo.items() if v is not None},
                )
                db.add(subj_obj)
                db.flush()
                subjects_count += 1
            else:
                if site_id:
                    subj_obj.site_id   = site_id
                    subj_obj.site_name = site_name
                for k, v in demo.items():
                    if v is not None:
                        setattr(subj_obj, k, v)
                db.flush()

            subject_id = subj_obj.id

            # ── Visits (StudyEventData) ────────────────────────────────────
            for event_elem in subject_elem.findall(tag("StudyEventData")):
                visit_oid  = _attr(event_elem, "StudyEventOID") or "VISIT"
                repeat_key = _attr(event_elem, "StudyEventRepeatKey") or "1"
                visit_name = (
                    _attr(event_elem, "mdsol:InstanceName")
                    or _attr(event_elem, f"{{{NS_MDSOL}}}InstanceName")
                    or visit_oid
                )

                # Derive visit date from any date-looking ItemData in this event
                visit_date: Optional[date] = None
                for item in event_elem.iter(tag("ItemData")):
                    val = _attr(item, "Value") or ""
                    if re.match(r"\d{4}-\d{2}-\d{2}", val):
                        visit_date = _parse_date(val)
                        break

                # Unique key: subject + visit OID + repeat key
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

                # ── Forms (FormData) ───────────────────────────────────────
                for form_elem in event_elem.findall(tag("FormData")):
                    form_oid  = _attr(form_elem, "FormOID") or "FORM"
                    form_name = form_labels.get(form_oid, form_oid)
                    form_data = _extract_form_data(form_elem, item_labels)

                    if not form_data:
                        continue  # skip empty forms

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
                        # Merge new fields into existing data_json
                        existing = json.loads(form_obj.data_json or "{}")
                        existing.update(form_data)
                        form_obj.data_json = json.dumps(existing)
                        form_obj.form_name = form_name

    db.commit()

    return {
        "study":    study_meta["study_oid"],
        "subjects": subjects_count,
        "visits":   visits_count,
        "forms":    forms_count,
        "warnings": warnings,
    }
