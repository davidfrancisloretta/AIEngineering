from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models import RaveTransaction, User
from services.demo import generate_transactions, transaction_to_yaml, transactions_to_bulk_yaml

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
def seed_demo_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate 60 realistic demo transactions for the current user.
    Clears any existing transactions first so re-seeding is idempotent.
    """
    # Remove previous demo transactions for this user
    db.query(RaveTransaction).filter(RaveTransaction.user_id == current_user.id).delete()
    db.commit()

    fake_txns = generate_transactions(n=60)
    for txn in fake_txns:
        record = RaveTransaction(
            user_id=current_user.id,
            rave_id=txn["id"],
            transaction_ref=txn["tx_ref"],
            amount=txn["amount"],
            currency=txn["currency"],
            status=txn["status"],
            payment_type=txn["payment_type"],
            customer_email=txn["customer"]["email"],
            customer_name=txn["customer"]["name"],
            data_yaml=transaction_to_yaml(txn),
        )
        db.add(record)

    db.commit()
    return {"message": f"Loaded {len(fake_txns)} demo transactions successfully"}


@router.get("/export/yaml", response_class=PlainTextResponse)
def export_all_yaml(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export every stored transaction for this user as a single YAML document.
    """
    records = (
        db.query(RaveTransaction)
        .filter(RaveTransaction.user_id == current_user.id)
        .order_by(RaveTransaction.fetched_at.desc())
        .all()
    )

    txns = []
    for r in records:
        txns.append({
            "id": r.id,
            "rave_id": r.rave_id,
            "transaction_ref": r.transaction_ref,
            "amount": r.amount,
            "currency": r.currency,
            "status": r.status,
            "payment_type": r.payment_type,
            "customer": {
                "email": r.customer_email,
                "name": r.customer_name,
            },
            "fetched_at": r.fetched_at.isoformat() if r.fetched_at else None,
        })

    return transactions_to_bulk_yaml(txns)
