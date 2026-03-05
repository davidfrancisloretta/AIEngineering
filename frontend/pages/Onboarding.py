import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.api import ApiClient, ApiError
from utils.styles import page_header

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

page_header("🚀", "Getting", "Started",
            subtitle="3 steps to your first AI-powered clinical data query")
st.markdown("---")

# ── Initialise wizard step ─────────────────────────────────────────────────────
if "wizard_step" not in st.session_state:
    st.session_state["wizard_step"] = 0
if "wizard_seed_done" not in st.session_state:
    st.session_state["wizard_seed_done"] = False
if "wizard_ingest_running" not in st.session_state:
    st.session_state["wizard_ingest_running"] = False
if "wizard_ingest_done" not in st.session_state:
    st.session_state["wizard_ingest_done"] = False

step = st.session_state["wizard_step"]

# ── Step indicator ─────────────────────────────────────────────────────────────
def _step_label(idx: int, label: str, icon: str) -> str:
    if idx < step:
        color, weight = "#3FB950", "700"
        prefix = "✅"
    elif idx == step:
        color, weight = "#FF8400", "700"
        prefix = icon
    else:
        color, weight = "#484F58", "400"
        prefix = icon
    return (
        f'<span style="color:{color};font-weight:{weight};font-size:15px;">'
        f'{prefix} {label}</span>'
    )

steps_html = (
    _step_label(0, "Seed Demo Data",   "1️⃣") + "&nbsp;&nbsp;&nbsp;›&nbsp;&nbsp;&nbsp;"
    + _step_label(1, "Ingest for RAG", "2️⃣") + "&nbsp;&nbsp;&nbsp;›&nbsp;&nbsp;&nbsp;"
    + _step_label(2, "Ask a Question", "3️⃣")
)
st.markdown(steps_html, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── Auto-detect progress from existing data ────────────────────────────────────
rag_st: dict = {}
try:
    rag_st = client.rag_status()
    chunk_count = rag_st.get("chunk_count", 0)
except ApiError:
    chunk_count = 0

try:
    subjects = client.get_subjects()
    has_data = len(subjects) > 0
except ApiError:
    has_data = False

# Auto-advance step if data already present
if has_data and not st.session_state["wizard_seed_done"]:
    st.session_state["wizard_seed_done"] = True
    if step == 0:
        st.session_state["wizard_step"] = 1
        step = 1

if chunk_count > 0 and not st.session_state["wizard_ingest_done"]:
    st.session_state["wizard_ingest_done"] = True
    if step == 0:
        st.session_state["wizard_step"] = 2
        step = 2


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 0 — Seed Demo Data
# ═══════════════════════════════════════════════════════════════════════════════
if step == 0:
    st.markdown(
        """
        ### Step 1 — Seed Demo Data

        Load the **CARDIO-2024** Phase III demo dataset into the database.
        This creates 20 synthetic subjects across 5 clinical sites, with visits,
        adverse events, lab results, and vital signs.
        """
    )

    col_btn, col_info = st.columns([1, 2])
    with col_btn:
        if st.button("🧬 Seed Demo Data", type="primary", use_container_width=True):
            with st.spinner("Generating CARDIO-2024 demo dataset…"):
                try:
                    r = client.seed_clinical_data()
                    st.success(
                        f"✅ Loaded: {r['subjects']} subjects, "
                        f"{r['visits']} visits, {r['forms']} forms"
                    )
                    st.session_state["wizard_seed_done"] = True
                    st.session_state["wizard_step"] = 1
                    time.sleep(1)
                    st.rerun()
                except ApiError as e:
                    st.error(f"❌ {e}")

    with col_info:
        st.markdown(
            """
            **What this creates:**
            - 1 clinical study (CARDIO-2024)
            - 20 subjects across 5 sites (London, Manchester, Leeds, Bristol, Edinburgh)
            - 5 visits per subject (Screening through Week 24)
            - Vital signs, adverse events, concomitant meds, lab results per visit
            """
        )

    st.markdown("---")
    if st.button("Skip this step →", key="skip_0"):
        st.session_state["wizard_step"] = 1
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Ingest for RAG
# ═══════════════════════════════════════════════════════════════════════════════
elif step == 1:
    st.markdown(
        """
        ### Step 2 — Ingest Data for AI Chat

        Convert all clinical records into **vector embeddings** so the AI can
        retrieve relevant context when you ask questions. This runs in the background
        and takes about 30–60 seconds.
        """
    )

    if st.session_state["wizard_ingest_running"]:
        try:
            ingest_st = client.rag_ingest_status()
            s     = ingest_st.get("status", "idle")
            done  = ingest_st.get("done", 0)
            total = max(ingest_st.get("total", 1), 1)

            if s == "running":
                pct = min(done / total, 0.99)
                st.progress(pct, text=f"Embedding chunk {done} / {total}…")
                st.caption("The AI is reading and indexing every subject, visit, adverse event, and lab result.")
                time.sleep(2)
                st.rerun()
            elif s == "done":
                chunks = ingest_st.get("chunks_created", 0)
                st.success(f"✅ {chunks} chunks embedded — AI Chat is ready!")
                st.session_state["wizard_ingest_running"] = False
                st.session_state["wizard_ingest_done"] = True
                st.session_state["wizard_step"] = 2
                time.sleep(1)
                st.rerun()
            elif s == "error":
                st.error(f"❌ {ingest_st.get('error', 'Unknown error')}")
                st.session_state["wizard_ingest_running"] = False
            else:
                st.session_state["wizard_ingest_running"] = False
        except ApiError as e:
            st.error(f"❌ {e}")
            st.session_state["wizard_ingest_running"] = False
    else:
        rag_ready = rag_st.get("ollama_ready", False)
        if not rag_ready:
            st.warning("⏳ Ollama is still starting up — wait a moment then try again.")

        col_btn, col_info = st.columns([1, 2])
        with col_btn:
            if st.button("🔍 Ingest for RAG", type="primary", use_container_width=True,
                         disabled=not rag_ready):
                try:
                    client.rag_ingest()
                    st.session_state["wizard_ingest_running"] = True
                    time.sleep(0.3)
                    st.rerun()
                except ApiError as e:
                    st.error(f"❌ {e}")

        with col_info:
            st.markdown(
                f"""
                **Current status:**
                - Ollama: {"✅ Ready" if rag_ready else "⏳ Starting…"}
                - Chunks indexed: **{chunk_count}**
                - Embed model: `{rag_st.get("embed_model", "nomic-embed-text")}`
                """
            )

    st.markdown("---")
    if st.button("Skip this step →", key="skip_1"):
        st.session_state["wizard_step"] = 2
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Ask First Question
# ═══════════════════════════════════════════════════════════════════════════════
elif step == 2:
    st.markdown(
        f"""
        ### Step 3 — Ask Your First Question

        You're all set! **{chunk_count} chunks** are indexed and ready.
        Head over to **AI Chat** and try one of the suggested questions below.
        """
    )

    st.markdown("**Suggested first questions:**")
    suggestions = [
        "Which subjects had severe adverse events?",
        "What were the abnormal lab results at Week 12?",
        "How many subjects are enrolled at the London site?",
        "What is the protocol objective of CARDIO-2024?",
        "List all subjects who have completed the trial.",
    ]
    for s in suggestions:
        st.markdown(f"- *{s}*")

    st.markdown("<br>", unsafe_allow_html=True)
    col_chat, col_sql, _ = st.columns([1, 1, 2])
    with col_chat:
        if st.button("🤖 Go to AI Chat", type="primary", use_container_width=True):
            st.switch_page("pages/RAG_Chat.py")
    with col_sql:
        if st.button("🗄️ Try SQL Chat", use_container_width=True):
            st.switch_page("pages/RAG_Chat.py")

    st.markdown("---")
    st.caption(
        "You can always return here from the sidebar. "
        "Reseed or re-ingest at any time via the **Clinical Trials** page."
    )

    if st.button("↺ Restart wizard", key="restart"):
        for k in ["wizard_step", "wizard_seed_done", "wizard_ingest_running", "wizard_ingest_done"]:
            st.session_state.pop(k, None)
        st.rerun()
