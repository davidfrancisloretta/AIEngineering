from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models import ApiConfig, User
from schemas import ApiKeyConfig, ApiKeyResponse

router = APIRouter(prefix="/config", tags=["config"])


@router.post("/api-key", response_model=ApiKeyResponse)
def save_api_key(
    data: ApiKeyConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = db.query(ApiConfig).filter(ApiConfig.user_id == current_user.id).first()
    if config:
        config.rave_public_key = data.rave_public_key
        config.rave_secret_key = data.rave_secret_key
        config.updated_at = datetime.now(timezone.utc)
    else:
        config = ApiConfig(
            user_id=current_user.id,
            rave_public_key=data.rave_public_key,
            rave_secret_key=data.rave_secret_key,
        )
        db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("/api-key", response_model=ApiKeyResponse)
def get_api_key(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = db.query(ApiConfig).filter(ApiConfig.user_id == current_user.id).first()
    if not config:
        raise HTTPException(status_code=404, detail="No API key configured")
    return config
