from fastapi import APIRouter, Depends, HTTPException
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
)
from services.clinical_demo import seed_clinical_study

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
