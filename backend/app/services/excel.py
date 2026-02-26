"""
Parse an uploaded Excel file into RaveTransaction-compatible dicts.
Column detection is case-insensitive and handles common Flutterwave
export names as well as generic payment-data spreadsheet headers.
"""
import io
from typing import Any

import pandas as pd
import yaml

# Ordered lists of aliases for each target field (first match wins)
FIELD_ALIASES: dict[str, list[str]] = {
    "transaction_ref": [
        "id", "transaction id", "tx ref", "tx_ref", "txn id", "txn ref",
        "flw ref", "flw_ref", "reference", "ref", "transaction_ref",
        "order id", "order_id",
    ],
    "amount": [
        "amount", "charged amount", "transaction amount", "value",
        "total", "sum", "amt", "debit", "credit",
    ],
    "currency": [
        "currency", "currency code", "curr", "ccy",
    ],
    "status": [
        "status", "payment status", "transaction status", "txn status",
        "state", "result",
    ],
    "payment_type": [
        "payment type", "payment method", "payment_type", "method",
        "channel", "type", "instrument",
    ],
    "customer_name": [
        "customer name", "customer_name", "name", "full name",
        "payer", "customer", "beneficiary", "account name",
    ],
    "customer_email": [
        "customer email", "customer_email", "email", "e-mail",
        "email address", "payer email",
    ],
}


def _normalise(text: str) -> str:
    return str(text).lower().strip()


def _detect_columns(df_columns: list[str]) -> dict[str, str | None]:
    """
    Return a mapping {field_name: excel_column_name | None}.
    """
    norm_to_original = {_normalise(c): c for c in df_columns}
    detected: dict[str, str | None] = {}

    for field, aliases in FIELD_ALIASES.items():
        matched = None
        for alias in aliases:
            if alias in norm_to_original:
                matched = norm_to_original[alias]
                break
        detected[field] = matched

    return detected


def _safe_str(val: Any) -> str | None:
    if pd.isna(val):
        return None
    return str(val).strip() or None


def _safe_float(val: Any) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def parse_excel(file_bytes: bytes, filename: str) -> tuple[list[dict], dict]:
    """
    Parse Excel/CSV bytes into a list of transaction dicts.
    Also returns the column-detection map for UI feedback.

    Returns (transactions, column_map)
    """
    buf = io.BytesIO(file_bytes)

    if filename.lower().endswith(".csv"):
        df = pd.read_csv(buf, dtype=str)
    else:
        df = pd.read_excel(buf, dtype=str)

    df.columns = [str(c).strip() for c in df.columns]
    col_map = _detect_columns(list(df.columns))

    transactions = []
    for _, row in df.iterrows():
        def get(field: str) -> Any:
            col = col_map.get(field)
            return row[col] if col and col in row else None

        # Build a YAML snapshot of the full raw row
        raw_row = {c: (None if pd.isna(v) else str(v)) for c, v in row.items()}
        data_yaml = yaml.dump(raw_row, default_flow_style=False, allow_unicode=True, sort_keys=False)

        txn = {
            "transaction_ref": _safe_str(get("transaction_ref")),
            "amount": _safe_float(get("amount")),
            "currency": _safe_str(get("currency")),
            "status": _safe_str(get("status")),
            "payment_type": _safe_str(get("payment_type")),
            "customer_name": _safe_str(get("customer_name")),
            "customer_email": _safe_str(get("customer_email")),
            "data_yaml": data_yaml,
        }
        transactions.append(txn)

    return transactions, col_map
