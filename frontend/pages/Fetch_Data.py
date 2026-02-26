import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import yaml
import pandas as pd
from utils.api import ApiClient, ApiError

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

st.title("📂 Import Data")
st.markdown("Upload an Excel file to ingest transaction data, or load the built-in demo dataset.")
st.markdown("---")

# ═══════════════════════════════════════════════════════
# 1 — Excel Upload (primary)
# ═══════════════════════════════════════════════════════
st.subheader("Upload Excel / CSV File")
st.markdown(
    "Supports `.xlsx`, `.xls`, and `.csv`. "
    "Column names are detected automatically — "
    "works with standard Flutterwave exports and custom sheets."
)

uploaded = st.file_uploader(
    "Choose a file",
    type=["xlsx", "xls", "csv"],
    label_visibility="collapsed",
)

if uploaded is not None:
    st.info(f"📄 **{uploaded.name}** — {uploaded.size:,} bytes")

    # Preview first 5 rows before importing
    try:
        if uploaded.name.endswith(".csv"):
            preview_df = pd.read_csv(uploaded)
        else:
            preview_df = pd.read_excel(uploaded)
        with st.expander("Preview first 5 rows", expanded=True):
            st.dataframe(preview_df.head(5), use_container_width=True)
            st.caption(f"{len(preview_df)} rows × {len(preview_df.columns)} columns detected")
        uploaded.seek(0)
    except Exception as e:
        st.warning(f"Could not preview file: {e}")

    if st.button("⬆️ Import File", use_container_width=True, type="primary"):
        with st.spinner("Parsing and importing rows…"):
            try:
                result = client.upload_excel(uploaded.read(), uploaded.name)
                st.success(f"✅ {result['message']}")

                detected = result.get("columns_detected", {})
                undetected = result.get("columns_not_found", [])

                col_a, col_b = st.columns(2)
                with col_a:
                    if detected:
                        st.markdown("**Columns mapped:**")
                        for field, col in detected.items():
                            st.markdown(f"- `{col}` → **{field}**")
                with col_b:
                    if undetected:
                        st.markdown("**Not found (stored as blank):**")
                        for field in undetected:
                            st.markdown(f"- {field}")

                st.rerun()
            except ApiError as e:
                st.error(f"❌ Import failed: {e}")

st.markdown("---")

# ═══════════════════════════════════════════════════════
# 2 — Demo Dataset
# ═══════════════════════════════════════════════════════
with st.expander("🎯 No file yet? Load the built-in demo dataset (60 transactions)"):
    st.markdown(
        "Generates 60 realistic transactions across NGN, USD, GHS, KES and GBP "
        "with 90 days of history — no file or API key needed."
    )
    if st.button("⚡ Load Demo Data", use_container_width=True, type="secondary"):
        with st.spinner("Generating demo transactions…"):
            try:
                result = client.seed_demo_data()
                st.success(f"✅ {result['message']}")
                st.rerun()
            except ApiError as e:
                st.error(f"❌ {e}")

st.markdown("---")

# ═══════════════════════════════════════════════════════
# 3 — Stored Data Viewer + YAML Export
# ═══════════════════════════════════════════════════════
st.subheader("Stored Transactions")

try:
    transactions = client.get_transactions()
except ApiError as e:
    st.error(f"Could not load transactions: {e}")
    st.stop()

if not transactions:
    st.info("No data yet — upload a file or load the demo dataset above.")
    st.stop()

# ── Summary row ───────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Rows", len(transactions))
c2.metric("Successful", sum(1 for t in transactions if t.get("status") == "successful"))
c3.metric("Currencies", len({t.get("currency") for t in transactions if t.get("currency")}))
c4.metric(
    "Total Revenue",
    f"{sum(t.get('amount') or 0 for t in transactions if t.get('status') == 'successful'):,.2f}",
)

st.markdown("---")

# ── Bulk YAML export ──────────────────────────────────
col_hdr, col_btn = st.columns([3, 1])
col_hdr.markdown(f"**{len(transactions)} row(s)** stored — select one below to view its YAML")

with col_btn:
    try:
        bulk_yaml = client.export_yaml()
        st.download_button(
            label="⬇️ Export All YAML",
            data=bulk_yaml,
            file_name="transactions.yaml",
            mime="text/yaml",
            use_container_width=True,
        )
    except ApiError:
        pass

# ── Per-row YAML viewer ───────────────────────────────
def _label(t):
    ref  = t.get("transaction_ref") or f"row {t['id']}"
    amt  = t.get("amount") or 0
    cur  = t.get("currency") or ""
    s    = t.get("status", "")
    icon = "✅" if s == "successful" else ("❌" if s == "failed" else "⏳")
    return f"{icon}  {ref}  |  {amt:,.2f} {cur}"

selected_idx = st.selectbox(
    "Select a row to view its YAML snapshot:",
    options=range(len(transactions)),
    format_func=lambda i: _label(transactions[i]),
)

txn = transactions[selected_idx]

yaml_dict = {
    "id":              txn.get("id"),
    "transaction_ref": txn.get("transaction_ref"),
    "amount":          txn.get("amount"),
    "currency":        txn.get("currency"),
    "status":          txn.get("status"),
    "payment_type":    txn.get("payment_type"),
    "customer": {
        "name":  txn.get("customer_name"),
        "email": txn.get("customer_email"),
    },
    "imported_at": str(txn.get("fetched_at")),
}

yaml_str = yaml.dump(yaml_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
st.code(yaml_str, language="yaml")

st.download_button(
    label="⬇️ Download this row as YAML",
    data=yaml_str,
    file_name=f"row_{txn.get('transaction_ref', txn['id'])}.yaml",
    mime="text/yaml",
)
