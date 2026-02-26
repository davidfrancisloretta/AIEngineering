"""
Generates the CARDIO-2024 Phase III clinical trial demo dataset.

Structure mirrors CDISC ODM:
  Study → Subject → Visit → Form (VS / AE / CM / LB)

All data is deterministic (seeded RNG seed=42) so re-seeding is idempotent
and produces the same subjects, visits, and form values every time.
"""
import json
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models_clinical import ClinicalStudy, ClinicalSubject, ClinicalVisit, ClinicalForm


# ── Study definition ────────────────────────────────────────────────────────────

STUDY_DEF = {
    "study_oid":         "CARDIO-2024",
    "protocol_name":     (
        "A Phase III Randomised, Double-Blind, Placebo-Controlled Study of CardioMax 50 mg "
        "Once Daily in Patients with Moderate-to-Severe Heart Failure (NYHA Class II-III)"
    ),
    "phase":             "Phase III",
    "sponsor":           "CardioPharm International Ltd.",
    "therapeutic_area":  "Cardiovascular",
    "objective":         (
        "To evaluate the efficacy and safety of CardioMax 50 mg once daily in reducing "
        "Major Adverse Cardiovascular Events (MACE) over 52 weeks compared to placebo "
        "in patients with reduced ejection fraction heart failure."
    ),
    "status":            "Active",
}

SITES = [
    ("SITE-001", "London Cardiology Centre"),
    ("SITE-002", "Manchester Heart Institute"),
    ("SITE-003", "Edinburgh Royal Infirmary"),
]

VISITS = [
    ("SCREENING", "Screening",         -14),
    ("DAY1",      "Day 1 (Baseline)",    0),
    ("WEEK4",     "Week 4",             28),
    ("WEEK12",    "Week 12",            84),
    ("EOT",       "End of Treatment",  364),
]

RACES = ["White", "Black or African American", "Asian", "Mixed", "Other"]

AE_TERMS = [
    ("Headache",      "Mild",     "Unlikely", "Resolved"),
    ("Nausea",        "Mild",     "Possible", "Resolved"),
    ("Dizziness",     "Moderate", "Probable", "Resolved"),
    ("Fatigue",       "Mild",     "Unlikely", "Ongoing"),
    ("Dyspnoea",      "Moderate", "Possible", "Resolved"),
    ("Peripheral oedema", "Severe", "Probable", "Resolved"),
    ("Palpitations",  "Mild",     "Unlikely", "Resolved"),
    ("Hypotension",   "Moderate", "Probable", "Resolved"),
    ("Chest pain",    "Severe",   "Possible", "Hospitalised"),
    ("Bradycardia",   "Moderate", "Probable", "Resolved"),
]

LAB_TESTS = [
    ("HGB",  "Haemoglobin",       "g/dL",    11.0, 17.5),
    ("WBC",  "White Blood Count", "10^9/L",   4.0, 11.0),
    ("PLT",  "Platelets",         "10^9/L", 150.0, 400.0),
    ("CREAT","Creatinine",        "umol/L",  62.0, 115.0),
    ("CHOL", "Total Cholesterol", "mmol/L",   3.5,   6.5),
    ("BNP",  "BNP",               "pg/mL",    0.0, 100.0),
    ("TROP", "Troponin I",        "ng/L",     0.0,  14.0),
    ("K",    "Potassium",         "mmol/L",   3.5,   5.0),
    ("NA",   "Sodium",            "mmol/L", 135.0, 145.0),
]

MEDICATIONS = [
    "Aspirin 75 mg",
    "Bisoprolol 5 mg",
    "Ramipril 10 mg",
    "Atorvastatin 40 mg",
    "Furosemide 40 mg",
    "Spironolactone 25 mg",
    "Metformin 500 mg",
    "Amlodipine 5 mg",
    "Warfarin 5 mg",
    "Clopidogrel 75 mg",
]


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _weighted(rng: random.Random, options: list[tuple]) -> str:
    population = [item for item, weight in options for _ in range(weight)]
    return rng.choice(population)


def _generate_vitals(rng: random.Random, visit_index: int) -> dict:
    """Vital signs with gradual improvement over trial visits."""
    return {
        "heart_rate":   rng.randint(58, 102) - visit_index * rng.randint(0, 2),
        "systolic_bp":  rng.randint(108, 155) - visit_index * rng.randint(0, 3),
        "diastolic_bp": rng.randint(68, 96) - visit_index * rng.randint(0, 2),
        "temperature":  round(36.1 + rng.uniform(0.0, 1.3), 1),
        "weight":       round(rng.uniform(56.0, 108.0), 1),
        "height":       rng.randint(153, 192),
    }


def _generate_labs(rng: random.Random) -> dict:
    """Lab panel: 80% normal, 20% abnormal per analyte."""
    results = []
    for code, name, unit, lo, hi in LAB_TESTS:
        r = rng.random()
        if r < 0.80:
            value = round(rng.uniform(lo, hi), 2)
            flag = "N"
        elif r < 0.90:
            value = round(rng.uniform(hi, hi * 1.45), 2)
            flag = "HH" if value > hi * 1.30 else "H"
        else:
            value = round(rng.uniform(lo * 0.55, lo), 2)
            flag = "LL" if value < lo * 0.70 else "L"
        results.append({
            "test": code, "name": name,
            "value": value, "unit": unit, "flag": flag,
        })
    return {"results": results}


def _generate_aes(rng: random.Random, visit_index: int) -> dict:
    """0-2 adverse events per visit; none at Screening."""
    if visit_index == 0:
        return {"events": []}
    n = rng.choices([0, 1, 2], weights=[65, 25, 10])[0]
    events = []
    for _ in range(n):
        term, severity, relationship, outcome = rng.choice(AE_TERMS)
        events.append({
            "term": term, "severity": severity,
            "relationship": relationship, "outcome": outcome,
        })
    return {"events": events}


def _generate_meds(rng: random.Random) -> dict:
    meds = rng.sample(MEDICATIONS, k=rng.randint(1, 5))
    return {"medications": meds}


# ── Main seed function ───────────────────────────────────────────────────────────

def seed_clinical_study(db: Session, seed: int = 42) -> dict:
    """
    Generate and persist the full CARDIO-2024 demo dataset.
    Clears existing clinical data first (fully idempotent).
    Returns summary counts.
    """
    rng = random.Random(seed)

    # Clear in reverse FK order
    db.query(ClinicalForm).delete()
    db.query(ClinicalVisit).delete()
    db.query(ClinicalSubject).delete()
    db.query(ClinicalStudy).delete()
    db.commit()

    # Create study
    study = ClinicalStudy(**STUDY_DEF)
    db.add(study)
    db.flush()

    enrollment_start = date(2024, 1, 15)
    subject_count = 0
    visit_count   = 0
    form_count    = 0

    for i in range(20):
        site_id, site_name = rng.choice(SITES)
        enroll_date = enrollment_start + timedelta(days=rng.randint(0, 120))
        subj_status = _weighted(rng, [("Enrolled", 70), ("Completed", 20), ("Withdrawn", 10)])

        subject = ClinicalSubject(
            study_id=study.id,
            subject_key=f"CARDIO-2024-{i + 1:03d}",
            site_id=site_id,
            site_name=site_name,
            age=rng.randint(45, 82),
            sex=rng.choice(["M", "F"]),
            race=rng.choice(RACES),
            enrollment_date=enroll_date,
            status=subj_status,
        )
        db.add(subject)
        db.flush()
        subject_count += 1

        # Completed subjects get all 5 visits; others get 2-4
        n_visits = len(VISITS) if subj_status == "Completed" else rng.randint(2, 4)

        for v_idx, (v_oid, v_name, v_day_offset) in enumerate(VISITS[:n_visits]):
            visit_date = enroll_date + timedelta(days=v_day_offset)
            visit = ClinicalVisit(
                subject_id=subject.id,
                visit_oid=v_oid,
                visit_name=v_name,
                visit_date=visit_date,
                status="Completed",
            )
            db.add(visit)
            db.flush()
            visit_count += 1

            # Four forms per visit
            db.add(ClinicalForm(
                visit_id=visit.id, form_oid="VS", form_name="Vital Signs",
                data_json=json.dumps(_generate_vitals(rng, v_idx)),
            ))
            db.add(ClinicalForm(
                visit_id=visit.id, form_oid="AE", form_name="Adverse Events",
                data_json=json.dumps(_generate_aes(rng, v_idx)),
            ))
            db.add(ClinicalForm(
                visit_id=visit.id, form_oid="CM", form_name="Concomitant Medications",
                data_json=json.dumps(_generate_meds(rng)),
            ))
            db.add(ClinicalForm(
                visit_id=visit.id, form_oid="LB", form_name="Lab Results",
                data_json=json.dumps(_generate_labs(rng)),
            ))
            form_count += 4

    db.commit()
    return {
        "study":    study.study_oid,
        "subjects": subject_count,
        "visits":   visit_count,
        "forms":    form_count,
    }
