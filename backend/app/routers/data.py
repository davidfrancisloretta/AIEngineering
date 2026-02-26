from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models import ApiConfig, RaveTransaction, User
from schemas import RaveTransactionResponse
from services.rave import fetch_transactions, to_yaml

router = APIRouter(prefix="/rave", tags=["rave"])


@router.post("/fetch")
def fetch_rave_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = db.query(ApiConfig).filter(ApiConfig.user_id == current_user.id).first()
    if not config or not config.rave_secret_key:
        raise HTTPException(status_code=400, detail="No Rave API key configured")

    try:
        response = fetch_transactions(config.rave_secret_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Rave API error: {exc}")

    raw = response.get("data", [])
    # Flutterwave v3 wraps transactions under data.transactions in some endpoints
    if isinstance(raw, dict):
        raw = raw.get("transactions", [])

    count = 0
    for txn in raw:
        rave_id = txn.get("id")
        if rave_id and db.query(RaveTransaction).filter(RaveTransaction.rave_id == rave_id).first():
            continue  # already stored
        record = RaveTransaction(
            user_id=current_user.id,
            rave_id=rave_id,
            transaction_ref=txn.get("tx_ref"),
            amount=txn.get("amount"),
            currency=txn.get("currency"),
            status=txn.get("status"),
            payment_type=txn.get("payment_type"),
            customer_email=(txn.get("customer") or {}).get("email"),
            customer_name=(txn.get("customer") or {}).get("name"),
            data_yaml=to_yaml(txn),
        )
        db.add(record)
        count += 1

    db.commit()
    return {"message": f"Fetched and stored {count} new transaction(s)"}


@router.get("/transactions", response_model=list[RaveTransactionResponse])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(RaveTransaction)
        .filter(RaveTransaction.user_id == current_user.id)
        .order_by(RaveTransaction.fetched_at.desc())
        .all()
    )


@router.get("/transactions/{txn_id}/yaml")
def get_transaction_yaml(
    txn_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    txn = (
        db.query(RaveTransaction)
        .filter(RaveTransaction.id == txn_id, RaveTransaction.user_id == current_user.id)
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"yaml": txn.data_yaml}
