import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import yaml
from utils.api import ApiClient, ApiError

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

st.title("🔄 Fetch Data")
st.markdown("Pull live transaction data from the Rave API and store it for dashboard analysis.")
st.markdown("---")

# ──────────────────────────────────────────────────────
# API key status check
# ──────────────────────────────────────────────────────
try:
    config = client.get_api_key()
except ApiError:
    config = None

if not config:
    st.warning("⚠️ No Rave API key configured. Go to **Settings** to add your keys first.")
    st.stop()

pub = config["rave_public_key"]
masked = pub[:12] + "..." + pub[-4:] if len(pub) > 16 else pub
st.info(f"Using key: `{masked}`")

# ──────────────────────────────────────────────────────
# Fetch button
# ──────────────────────────────────────────────────────
if st.button("🚀 Fetch Transactions from Rave API", use_container_width=True, type="primary"):
    with st.spinner("Contacting Rave API…"):
        try:
            result = client.fetch_rave_data()
            st.success(f"✅ {result['message']}")
        except ApiError as e:
            st.error(f"❌ Fetch failed: {e}")

# ──────────────────────────────────────────────────────
# Stored transactions — YAML viewer
# ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Stored Transactions")

try:
    transactions = client.get_transactions()
except ApiError as e:
    st.error(f"Could not load transactions: {e}")
    st.stop()

if not transactions:
    st.info("No transactions stored yet. Click the button above to fetch data.")
else:
    st.markdown(f"**{len(transactions)} transaction(s) stored**")

    def label(t):
        ref = t.get("transaction_ref") or f"ID {t['id']}"
        amt = t.get("amount") or 0
        cur = t.get("currency") or ""
        return f"{ref} — {amt:,.2f} {cur}"

    selected_idx = st.selectbox(
        "Select a transaction to view its YAML snapshot:",
        options=range(len(transactions)),
        format_func=lambda i: label(transactions[i]),
    )

    txn = transactions[selected_idx]

    # Build a clean YAML view from fields (data_yaml not exposed via list endpoint)
    yaml_dict = {
        "id": txn.get("id"),
        "rave_id": txn.get("rave_id"),
        "transaction_ref": txn.get("transaction_ref"),
        "amount": txn.get("amount"),
        "currency": txn.get("currency"),
        "status": txn.get("status"),
        "payment_type": txn.get("payment_type"),
        "customer": {
            "email": txn.get("customer_email"),
            "name": txn.get("customer_name"),
        },
        "fetched_at": str(txn.get("fetched_at")),
    }

    st.code(yaml.dump(yaml_dict, default_flow_style=False, allow_unicode=True), language="yaml")

    # Download button
    st.download_button(
        label="⬇️ Download YAML",
        data=yaml.dump(yaml_dict, default_flow_style=False, allow_unicode=True),
        file_name=f"transaction_{txn.get('transaction_ref', txn['id'])}.yaml",
        mime="text/yaml",
    )
