import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.api import ApiClient, ApiError

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

st.title("🤖 Clinical Trial RAG Chat")
st.markdown(
    "Ask natural language questions about the **CARDIO-2024** trial data. "
    "The AI retrieves relevant clinical records and answers using a local LLM."
)
st.markdown("---")

# ── Initialise session state ──────────────────────────────────────────────────
if "rag_history" not in st.session_state:
    st.session_state["rag_history"] = []
if "last_sources" not in st.session_state:
    st.session_state["last_sources"] = []

# ── Two-column layout: chat (left) | sources (right) ─────────────────────────
col_chat, col_src = st.columns([3, 1])

with col_chat:
    # ── Ollama status badge ──────────────────────────────────────────────────
    try:
        status = client.rag_status()
        if status["ollama_ready"]:
            st.success(
                f"✅ Ollama ready  ·  LLM: `{status['llm_model']}`  "
                f"·  Embed: `{status['embed_model']}`  "
                f"·  Chunks indexed: **{status['chunk_count']}**"
            )
            if status["chunk_count"] == 0:
                st.warning(
                    "No chunks indexed yet. Go to **Clinical Trials** → "
                    "**Seed Demo Data** then **Ingest for RAG** first."
                )
        else:
            st.warning(
                "⏳ Ollama is starting up — models are downloading. "
                "This can take 2-5 minutes on first launch. "
                "Run `docker exec ai_ollama ollama list` to check progress."
            )
    except ApiError:
        st.error("Could not reach the backend. Is the service running?")

    st.markdown("---")

    # ── Suggested questions ──────────────────────────────────────────────────
    st.markdown("**Try asking:**")
    suggestions = [
        "Which subjects had severe adverse events?",
        "What were the abnormal lab results at Week 12?",
        "How many subjects are enrolled at the London site?",
        "What is the protocol objective of CARDIO-2024?",
        "List all subjects who have completed the trial.",
    ]
    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        if cols[i].button(suggestion, use_container_width=True, key=f"sug_{i}"):
            st.session_state["rag_history"].append(
                {"role": "user", "content": suggestion}
            )
            with st.spinner("Thinking…"):
                try:
                    result = client.rag_chat(suggestion)
                    st.session_state["rag_history"].append(
                        {"role": "assistant", "content": result["answer"]}
                    )
                    st.session_state["last_sources"] = result.get("sources", [])
                except ApiError as e:
                    st.session_state["rag_history"].append(
                        {"role": "assistant", "content": f"Error: {e}"}
                    )
            st.rerun()

    st.markdown("---")

    # ── Chat history ─────────────────────────────────────────────────────────
    for msg in st.session_state["rag_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ────────────────────────────────────────────────────────────
    question = st.chat_input("Ask a question about the clinical trial data…")
    if question:
        st.session_state["rag_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving data and generating answer…"):
                try:
                    result = client.rag_chat(question)
                    answer = result["answer"]
                    st.session_state["last_sources"] = result.get("sources", [])
                except ApiError as e:
                    answer = f"Error: {e}"
                    st.session_state["last_sources"] = []

            st.markdown(answer)
            st.session_state["rag_history"].append(
                {"role": "assistant", "content": answer}
            )
        st.rerun()

    # ── Clear chat button ─────────────────────────────────────────────────────
    if st.session_state["rag_history"]:
        if st.button("🗑️ Clear chat history", use_container_width=True):
            st.session_state["rag_history"] = []
            st.session_state["last_sources"] = []
            st.rerun()

# ── Sources panel ─────────────────────────────────────────────────────────────
with col_src:
    st.subheader("Sources")
    sources = st.session_state.get("last_sources", [])
    if not sources:
        st.caption("Source chunks from the last answer will appear here.")
    else:
        for i, src in enumerate(sources, start=1):
            similarity_pct = f"{src['similarity'] * 100:.1f}%"
            src_type_icon = {
                "study":         "📚",
                "subject":       "👤",
                "visit":         "📅",
                "adverse_event": "⚠️",
                "lab":           "🔬",
            }.get(src["source_type"], "📄")

            with st.expander(
                f"{src_type_icon} Source {i} · {src['source_type']} · {similarity_pct}",
                expanded=(i == 1),
            ):
                st.caption(f"Similarity: **{similarity_pct}**  ·  Type: `{src['source_type']}`")
                st.markdown(src["chunk_text"])
