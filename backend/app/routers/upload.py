from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models import RaveTransaction, User
from services.excel import parse_excel

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


@router.post("/excel")
async def upload_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload .xlsx, .xls, or .csv",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        transactions, col_map = parse_excel(contents, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {exc}")

    if not transactions:
        raise HTTPException(status_code=422, detail="No data rows found in the file")

    # Clear previously Excel-uploaded rows for this user (rave_id IS NULL)
    db.query(RaveTransaction).filter(
        RaveTransaction.user_id == current_user.id,
        RaveTransaction.rave_id.is_(None),
    ).delete(synchronize_session=False)
    db.commit()

    count = 0
    for txn in transactions:
        record = RaveTransaction(
            user_id=current_user.id,
            rave_id=None,               # NULL — allowed by Postgres UNIQUE
            transaction_ref=txn["transaction_ref"],
            amount=txn["amount"],
            currency=txn["currency"],
            status=txn["status"],
            payment_type=txn["payment_type"],
            customer_email=txn["customer_email"],
            customer_name=txn["customer_name"],
            data_yaml=txn["data_yaml"],
        )
        db.add(record)
        count += 1

    db.commit()

    detected = {k: v for k, v in col_map.items() if v}
    undetected = [k for k, v in col_map.items() if not v]

    return {
        "message": f"Imported {count} row(s) from '{file.filename}'",
        "rows_imported": count,
        "columns_detected": detected,
        "columns_not_found": undetected,
    }
