import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.api import ApiClient, ApiError
from utils.styles import page_header

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

page_header("⚙️", "Account", "Settings")
st.markdown("---")

# ──────────────────────────────────────────────────────
# Rave API Keys
# ──────────────────────────────────────────────────────
st.subheader("Rave (Flutterwave) API Keys")
st.markdown(
    "Your keys are stored securely on the server and never exposed to the browser after saving."
)

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
# Mem0 — AI Memory
# ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🧠 AI Memory (Mem0)")
st.markdown(
    "RAVE AI remembers facts from your previous conversations to give more personalised answers. "
    "Powered by [Mem0](https://mem0.ai). Requires `MEM0_API_KEY` to be set in the backend environment."
)

try:
    mem_data = client.get_memories()
    enabled   = mem_data.get("enabled", False)
    memories  = mem_data.get("memories", [])
    count     = mem_data.get("count", 0)

    if not enabled:
        st.warning(
            "Mem0 is not configured. "
            "Add your `MEM0_API_KEY` to the backend environment and rebuild to enable persistent memory."
        )
    else:
        st.success(f"✅ Mem0 active — **{count}** memor{'y' if count == 1 else 'ies'} stored")

        if memories:
            with st.expander(f"View all {count} memories", expanded=False):
                for i, mem in enumerate(memories, start=1):
                    text = mem.get("memory", "")
                    created = mem.get("created_at", "")
                    label = f"**{i}.** {text}"
                    if created:
                        label += f"  \n*{created[:10]}*"
                    st.markdown(label)
                    if i < len(memories):
                        st.divider()
        else:
            st.caption("No memories stored yet — start chatting on the AI Chat page.")

        st.markdown("")
        if st.button("🗑️ Clear all memories", type="secondary", key="clear_mem"):
            try:
                client.clear_memories()
                st.success("All memories cleared.")
                st.rerun()
            except ApiError as e:
                st.error(f"Failed to clear memories: {e}")

except ApiError as e:
    st.error(f"Could not load memory status: {e}")

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
