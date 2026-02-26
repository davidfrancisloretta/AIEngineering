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
st.markdown("Pull transaction data from the Rave API, or load the built-in demo dataset.")
st.markdown("---")

# ──────────────────────────────────────────────────────
# Demo Data Section (always visible)
# ──────────────────────────────────────────────────────
with st.container():
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1565C0 0%, #1976D2 100%);
            border-radius: 10px;
            padding: 18px 22px;
            color: white;
            margin-bottom: 8px;
        ">
            <div style="font-size:16px; font-weight:700; margin-bottom:4px;">
                🎯 Demo Dataset
            </div>
            <div style="font-size:13px; opacity:0.9;">
                Load 60 realistic Rave transactions instantly — no API key needed.
                Includes multiple currencies, payment methods, and 90 days of history.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("⚡ Load Demo Data (60 transactions)", use_container_width=True, type="primary"):
        with st.spinner("Generating demo transactions…"):
            try:
                result = client.seed_demo_data()
                st.success(f"✅ {result['message']}")
                st.rerun()
            except ApiError as e:
                st.error(f"❌ Failed: {e}")

st.markdown("---")

# ──────────────────────────────────────────────────────
# Live Rave API Section
# ──────────────────────────────────────────────────────
st.subheader("Live Rave API")

try:
    config = client.get_api_key()
except ApiError:
    config = None

if not config:
    st.info("No API key configured. Add one in **Settings** to fetch live data, or use Demo Data above.")
else:
    pub = config["rave_public_key"]
    masked = pub[:12] + "..." + pub[-4:] if len(pub) > 16 else pub
    st.info(f"Connected — public key: `{masked}`")

    if st.button("🚀 Fetch from Rave API", use_container_width=True):
        with st.spinner("Contacting Rave API…"):
            try:
                result = client.fetch_rave_data()
                st.success(f"✅ {result['message']}")
                st.rerun()
            except ApiError as e:
                st.error(f"❌ Fetch failed: {e}")

st.markdown("---")

# ──────────────────────────────────────────────────────
# Stored Transactions — YAML Viewer + Export
# ──────────────────────────────────────────────────────
st.subheader("Stored Transactions — YAML")

try:
    transactions = client.get_transactions()
except ApiError as e:
    st.error(f"Could not load transactions: {e}")
    st.stop()

if not transactions:
    st.info("No transactions stored yet. Load demo data or fetch from Rave API above.")
    st.stop()

# Summary metrics
c1, c2, c3 = st.columns(3)
c1.metric("Total Stored", len(transactions))
c2.metric(
    "Successful",
    sum(1 for t in transactions if t.get("status") == "successful"),
)
c3.metric(
    "Currencies",
    len({t.get("currency") for t in transactions if t.get("currency")}),
)

st.markdown("---")

# ── Bulk YAML export ──────────────────────────────────
col_a, col_b = st.columns([3, 1])
col_a.markdown(f"**{len(transactions)} transaction(s)** stored — browse or download as YAML")

with col_b:
    try:
        bulk_yaml = client.export_yaml()
        st.download_button(
            label="⬇️ Export All YAML",
            data=bulk_yaml,
            file_name="rave_transactions.yaml",
            mime="text/yaml",
            use_container_width=True,
        )
    except ApiError:
        pass

# ── Per-transaction YAML viewer ───────────────────────
def _label(t):
    ref = t.get("transaction_ref") or f"ID {t['id']}"
    amt = t.get("amount") or 0
    cur = t.get("currency") or ""
    status = t.get("status", "")
    icon = "✅" if status == "successful" else ("❌" if status == "failed" else "⏳")
    return f"{icon}  {ref}  |  {amt:,.2f} {cur}"

selected_idx = st.selectbox(
    "Select a transaction to view its YAML snapshot:",
    options=range(len(transactions)),
    format_func=lambda i: _label(transactions[i]),
)

txn = transactions[selected_idx]

yaml_dict = {
    "id": txn.get("id"),
    "rave_id": txn.get("rave_id"),
    "transaction_ref": txn.get("transaction_ref"),
    "amount": txn.get("amount"),
    "currency": txn.get("currency"),
    "status": txn.get("status"),
    "payment_type": txn.get("payment_type"),
    "customer": {
        "name": txn.get("customer_name"),
        "email": txn.get("customer_email"),
    },
    "fetched_at": str(txn.get("fetched_at")),
}

yaml_str = yaml.dump(yaml_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)

st.code(yaml_str, language="yaml")

col_dl1, col_dl2 = st.columns(2)
col_dl1.download_button(
    label="⬇️ Download this YAML",
    data=yaml_str,
    file_name=f"transaction_{txn.get('transaction_ref', txn['id'])}.yaml",
    mime="text/yaml",
    use_container_width=True,
)
