import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.api import ApiClient, ApiError

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

st.title("⚙️ Settings")

# ──────────────────────────────────────────────────────
# Rave API Keys
# ──────────────────────────────────────────────────────
st.subheader("Rave (Flutterwave) API Keys")
st.markdown(
    "Your keys are stored securely on the server and never exposed to the browser after saving."
)

# Show current status
try:
    current = client.get_api_key()
    if current:
        pub = current["rave_public_key"]
        masked = pub[:12] + "..." + pub[-4:] if len(pub) > 16 else pub
        st.success(f"✅ API key configured — public key: `{masked}`")
except ApiError:
    current = None
    st.info("No API key configured yet.")

st.markdown("---")

with st.form("api_key_form"):
    public_key = st.text_input(
        "Public Key",
        placeholder="FLWPUBK-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-X",
        help="Found in your Flutterwave dashboard → Settings → API",
    )
    secret_key = st.text_input(
        "Secret Key",
        type="password",
        placeholder="FLWSECK-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-X",
        help="Keep this private — it authorises live transactions",
    )
    save = st.form_submit_button("Save Keys", use_container_width=True, type="primary")

if save:
    if not public_key or not secret_key:
        st.error("Both keys are required.")
    else:
        try:
            client.save_api_key(public_key, secret_key)
            st.success("Keys saved successfully!")
            st.rerun()
        except ApiError as e:
            st.error(f"Failed to save: {e}")

# ──────────────────────────────────────────────────────
# Account
# ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Account")
st.write(f"Logged in as **{st.session_state.get('email', 'Unknown')}**")

if st.button("Logout", type="secondary"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
