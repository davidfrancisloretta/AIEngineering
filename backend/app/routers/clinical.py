from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models import User
from models_clinical import ClinicalStudy, ClinicalSubject, ClinicalVisit, ClinicalForm
from schemas_clinical import (
    StudyResponse,
    SubjectResponse,
    VisitResponse,
    FormResponse,
    ClinicalSeedResponse,
    ODMUploadResponse,
)
from services.clinical_demo import seed_clinical_study
import services.odm_parser as odm_parser

router = APIRouter(prefix="/clinical", tags=["clinical"])


@router.post("/seed", response_model=ClinicalSeedResponse)
def seed_clinical_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate the full CARDIO-2024 Phase III demo dataset (idempotent)."""
    result = seed_clinical_study(db)
    return result


@router.delete("/seed", status_code=204)
def clear_clinical_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove all clinical trial demo data."""
    db.query(ClinicalForm).delete()
    db.query(ClinicalVisit).delete()
    db.query(ClinicalSubject).delete()
    db.query(ClinicalStudy).delete()
    db.commit()


@router.get("/studies", response_model=list[StudyResponse])
def list_studies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all clinical studies."""
    return db.query(ClinicalStudy).all()


@router.get("/subjects", response_model=list[SubjectResponse])
def list_subjects(
    study_id: int | None = None,
    site_id:  str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List subjects, optionally filtered by study_id or site_id."""
    q = db.query(ClinicalSubject)
    if study_id:
        q = q.filter(ClinicalSubject.study_id == study_id)
    if site_id:
        q = q.filter(ClinicalSubject.site_id == site_id)
    return q.order_by(ClinicalSubject.subject_key).all()


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single subject by ID."""
    subj = db.query(ClinicalSubject).filter(ClinicalSubject.id == subject_id).first()
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subj


@router.get("/visits", response_model=list[VisitResponse])
def list_visits(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all visits for a subject."""
    return (
        db.query(ClinicalVisit)
        .filter(ClinicalVisit.subject_id == subject_id)
        .order_by(ClinicalVisit.visit_date)
        .all()
    )


@router.get("/forms/{visit_id}", response_model=list[FormResponse])
def list_forms(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all forms (VS/AE/CM/LB) for a visit."""
    return db.query(ClinicalForm).filter(ClinicalForm.visit_id == visit_id).all()


@router.post("/upload-odm", response_model=ODMUploadResponse)
async def upload_odm(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a CDISC ODM XML file (.xml or .odm) exported from Medidata Rave.
    Parses Study / Subject / Visit / Form data and upserts into clinical tables.
    Supports standard ODM 1.3 and Medidata Rave extensions (mdsol namespace).
    """
    # Validate file type
    filename = file.filename or ""
    if not filename.lower().endswith((".xml", ".odm")):
        raise HTTPException(
            status_code=400,
            detail="Only .xml or .odm files are accepted.",
        )

    xml_bytes = await file.read()
    if not xml_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = odm_parser.parse_and_ingest(xml_bytes, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ODMUploadResponse(
        study    = result["study"],
        subjects = result["subjects"],
        visits   = result["visits"],
        forms    = result["forms"],
        warnings = result.get("warnings", []),
        message  = (
            f"ODM import complete — {result['subjects']} subjects, "
            f"{result['visits']} visits, {result['forms']} forms loaded "
            f"from study {result['study']}."
        ),
    )
