import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st
from utils.api import ApiClient, ApiError

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

st.title("🤖 Clinical Trial AI Chat")
st.markdown("Ask natural language questions about your clinical trial data using two AI approaches.")
st.markdown("---")

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("rag_history",    []),
    ("last_sources",   []),
    ("sql_history",    []),
    ("rated_logs",     {}),
    ("stream_rag_q",   None),   # pending Vector RAG question to stream
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_rag, tab_sql = st.tabs([
    "🔍 Vector RAG Chat",
    "🗄️ Vectorless RAG",
])


# ── Shared: feedback buttons ───────────────────────────────────────────────────
def _feedback_row(log_id):
    """Render 👍/👎 for a log entry, or a confirmation if already rated."""
    if not log_id:
        return
    rated = st.session_state["rated_logs"]
    if log_id in rated:
        icon = "👍" if rated[log_id] == 1 else "👎"
        st.caption(f"{icon} Feedback recorded")
        return
    col1, col2, _ = st.columns([1, 1, 10])
    if col1.button("👍", key=f"up_{log_id}", help="Helpful"):
        try:
            client.submit_feedback(log_id, 1)
            st.session_state["rated_logs"][log_id] = 1
            st.rerun()
        except ApiError:
            pass
    if col2.button("👎", key=f"dn_{log_id}", help="Not helpful"):
        try:
            client.submit_feedback(log_id, -1)
            st.session_state["rated_logs"][log_id] = -1
            st.rerun()
        except ApiError:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Vector RAG Chat (streaming)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_rag:
    col_chat, col_src = st.columns([3, 1])

    with col_chat:
        # Status badge
        try:
            status = client.rag_status()
            if status["ollama_ready"]:
                st.success(
                    f"✅ Ollama ready  ·  LLM: `{status['llm_model']}`  "
                    f"·  Embed: `{status['embed_model']}`  "
                    f"·  Chunks indexed: **{status['chunk_count']}**  "
                    f"·  Hybrid search enabled"
                )
                if status["chunk_count"] == 0:
                    st.warning(
                        "No chunks indexed yet. Go to **Clinical Trials** → "
                        "**Seed Demo Data** then **Ingest for RAG** first."
                    )
            else:
                st.warning("⏳ Ollama is starting up — models may still be downloading.")
        except ApiError:
            st.error("Could not reach the backend.")

        st.markdown("---")

        # Suggestion buttons — queue question for streaming on next render
        st.markdown("**Try asking:**")
        rag_suggestions = [
            "Which subjects had severe adverse events?",
            "What were the abnormal lab results at Week 12?",
            "How many subjects are enrolled at the London site?",
            "What is the protocol objective of CARDIO-2024?",
            "List all subjects who have completed the trial.",
        ]
        cols = st.columns(len(rag_suggestions))
        for i, suggestion in enumerate(rag_suggestions):
            if cols[i].button(suggestion, use_container_width=True, key=f"rag_sug_{i}"):
                st.session_state["rag_history"].append({"role": "user", "content": suggestion})
                st.session_state["stream_rag_q"] = suggestion
                st.rerun()

        st.markdown("---")

        # Render settled history (all completed exchanges)
        for msg in st.session_state["rag_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant":
                    _feedback_row(msg.get("log_id"))

        # Chat input
        question = st.chat_input("Ask about clinical trial data…", key="rag_input")
        if question:
            st.session_state["rag_history"].append({"role": "user", "content": question})
            st.session_state["stream_rag_q"] = question
            st.rerun()

        # ── Streaming block — runs only when a question is pending ─────────────
        pending_q = st.session_state.get("stream_rag_q")
        if pending_q:
            st.session_state["stream_rag_q"] = None   # clear before streaming

            sources_out = []
            log_id_out  = [None]

            def _rag_token_gen(q=pending_q):
                for event in client.rag_chat_stream(q):
                    etype = event.get("type")
                    if etype in ("token", "guardrail"):
                        yield event["text"]
                    elif etype == "done":
                        sources_out.extend(event.get("sources", []))
                        log_id_out[0] = event.get("log_id")

            with st.chat_message("assistant"):
                full_answer = st.write_stream(_rag_token_gen())
                log_id = log_id_out[0]
                _feedback_row(log_id)

            st.session_state["last_sources"] = sources_out
            st.session_state["rag_history"].append({
                "role":    "assistant",
                "content": full_answer or "",
                "log_id":  log_id,
            })
            st.rerun()

        if st.session_state["rag_history"]:
            if st.button("🗑️ Clear chat history", key="rag_clear"):
                st.session_state["rag_history"] = []
                st.session_state["last_sources"] = []
                st.rerun()

    with col_src:
        st.subheader("Sources")
        sources = st.session_state.get("last_sources", [])
        if not sources:
            st.caption("Source chunks from the last answer will appear here.")
        else:
            for i, src in enumerate(sources, start=1):
                similarity_pct = f"{src['similarity'] * 100:.1f}%"
                icon = {"study": "📚", "subject": "👤", "visit": "📅",
                        "adverse_event": "⚠️", "lab": "🔬"}.get(src["source_type"], "📄")
                with st.expander(
                    f"{icon} Source {i} · {src['source_type']} · {similarity_pct}",
                    expanded=(i == 1),
                ):
                    st.caption(f"Similarity: **{similarity_pct}**  ·  Type: `{src['source_type']}`")
                    st.markdown(src["chunk_text"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Vectorless RAG (Text-to-SQL)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sql:
    st.markdown(
        "Ask questions in plain English. Instead of vector similarity search, "
        "the AI writes directly against your structured clinical database and explains the results. "
        "Uses **llama3.2:3b**. Follow-up questions work — the AI remembers the last 3 exchanges."
    )

    try:
        status = client.rag_status()
        if status.get("ollama_ready", False):
            st.info("Model: `llama3.2:3b`")
        else:
            st.warning("⏳ Ollama still loading — llama3.2:3b may not be ready yet.")
    except ApiError:
        pass

    st.markdown("---")

    st.markdown("**Try asking:**")
    sql_suggestions = [
        "How many subjects are in each site?",
        "Show me all subjects enrolled at site 003.",
        "Which subjects have more than 2 visits?",
        "List subjects with severe adverse events.",
        "List all unique form types in the database.",
    ]
    sql_cols = st.columns(len(sql_suggestions))
    for i, suggestion in enumerate(sql_suggestions):
        if sql_cols[i].button(suggestion, use_container_width=True, key=f"sql_sug_{i}"):
            history_payload = [
                {"role": m["role"], "content": m["content"], "sql": m.get("sql", "")}
                for m in st.session_state["sql_history"]
            ]
            st.session_state["sql_history"].append({"role": "user", "content": suggestion})
            with st.spinner("Generating SQL and querying database…"):
                try:
                    result = client.rag_sql_query(suggestion, history=history_payload)
                    st.session_state["sql_history"].append({
                        "role":          "assistant",
                        "content":       result["answer"],
                        "sql":           result["sql"],
                        "columns":       result["columns"],
                        "rows":          result["rows"],
                        "count":         result["row_count"],
                        "heal_attempts": result.get("heal_attempts", 0),
                        "log_id":        result.get("log_id"),
                    })
                except ApiError as e:
                    st.session_state["sql_history"].append({
                        "role": "assistant", "content": f"Error: {e}",
                        "sql": "", "columns": [], "rows": [],
                        "count": 0, "heal_attempts": 0, "log_id": None,
                    })
            st.rerun()

    st.markdown("---")

    for msg in st.session_state["sql_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sql"):
                heal = msg.get("heal_attempts", 0)
                heal_badge = f"  ·  🔧 healed {heal}x" if heal > 0 else ""
                with st.expander(
                    f"🔍 Generated SQL  ·  {msg.get('count', 0)} rows returned{heal_badge}"
                ):
                    st.code(msg["sql"], language="sql")
                    if msg.get("columns") and msg.get("rows"):
                        df = pd.DataFrame(msg["rows"], columns=msg["columns"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
            if msg["role"] == "assistant":
                _feedback_row(msg.get("log_id"))

    sql_question = st.chat_input(
        "Ask a data question — follow-ups work, e.g. 'now show only the severe ones'",
        key="sql_input",
    )
    if sql_question:
        history_payload = [
            {"role": m["role"], "content": m["content"], "sql": m.get("sql", "")}
            for m in st.session_state["sql_history"]
        ]
        st.session_state["sql_history"].append({"role": "user", "content": sql_question})
        with st.chat_message("user"):
            st.markdown(sql_question)

        with st.chat_message("assistant"):
            with st.spinner("Generating SQL and querying database…"):
                try:
                    result        = client.rag_sql_query(sql_question, history=history_payload)
                    answer        = result["answer"]
                    sql_out       = result["sql"]
                    columns       = result["columns"]
                    rows          = result["rows"]
                    count         = result["row_count"]
                    heal_attempts = result.get("heal_attempts", 0)
                    log_id        = result.get("log_id")
                except ApiError as e:
                    answer        = f"Error: {e}"
                    sql_out       = ""
                    columns       = []
                    rows          = []
                    count         = 0
                    heal_attempts = 0
                    log_id        = None

            st.markdown(answer)
            if sql_out:
                heal_badge = f"  ·  🔧 healed {heal_attempts}x" if heal_attempts > 0 else ""
                with st.expander(f"🔍 Generated SQL  ·  {count} rows returned{heal_badge}"):
                    st.code(sql_out, language="sql")
                    if columns and rows:
                        df = pd.DataFrame(rows, columns=columns)
                        st.dataframe(df, use_container_width=True, hide_index=True)
            _feedback_row(log_id)

            st.session_state["sql_history"].append({
                "role":          "assistant",
                "content":       answer,
                "sql":           sql_out,
                "columns":       columns,
                "rows":          rows,
                "count":         count,
                "heal_attempts": heal_attempts,
                "log_id":        log_id,
            })
        st.rerun()

    if st.session_state["sql_history"]:
        if st.button("🗑️ Clear SQL history", key="sql_clear"):
            st.session_state["sql_history"] = []
            st.rerun()
