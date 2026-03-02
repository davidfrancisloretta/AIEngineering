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
    ("rag_history",  []),
    ("last_sources", []),
    ("sql_history",  []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_rag, tab_sql = st.tabs([
    "🔍 Vector RAG Chat",
    "🗄️ Vectorless RAG",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Vector RAG Chat (existing)
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
                    f"·  Chunks indexed: **{status['chunk_count']}**"
                )
                if status["chunk_count"] == 0:
                    st.warning(
                        "No chunks indexed yet. Go to **Clinical Trials** → "
                        "**Seed Demo Data** then **Ingest for RAG** first."
                    )
            else:
                st.warning(
                    "⏳ Ollama is starting up — models may still be downloading. "
                    "Run `docker exec ai_ollama ollama list` to check progress."
                )
        except ApiError:
            st.error("Could not reach the backend.")

        st.markdown("---")

        # Suggested questions
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

        for msg in st.session_state["rag_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        question = st.chat_input("Ask about clinical trial data (vector search)…", key="rag_input")
        if question:
            st.session_state["rag_history"].append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                with st.spinner("Retrieving and answering…"):
                    try:
                        result = client.rag_chat(question)
                        answer = result["answer"]
                        st.session_state["last_sources"] = result.get("sources", [])
                    except ApiError as e:
                        answer = f"Error: {e}"
                        st.session_state["last_sources"] = []
                st.markdown(answer)
                st.session_state["rag_history"].append({"role": "assistant", "content": answer})
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
# TAB 2 — Text-to-SQL Chat
# ═══════════════════════════════════════════════════════════════════════════════
with tab_sql:
    st.markdown(
        "Ask questions in plain English. Instead of vector similarity search, "
        "the AI writes SQL directly against your structured clinical database and explains the results. "
        "Uses **llama3.2:3b** — no embeddings, no vector index, exact answers. "
        "**Follow-up questions work** — the AI remembers the last 3 exchanges."
    )

    # Model status
    try:
        status = client.rag_status()
        sql_ready = status.get("ollama_ready", False)
        if sql_ready:
            st.info("Model: `llama3.2:3b`  ·  Direct SQL against PostgreSQL  ·  HealerAgent enabled")
        else:
            st.warning("⏳ Ollama still loading — llama3.2:3b may not be ready yet.")
    except ApiError:
        pass

    st.markdown("---")

    # Suggested SQL questions
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
            # Build history for memory context (exclude rows/columns — too large)
            history_payload = [
                {"role": m["role"], "content": m["content"], "sql": m.get("sql", "")}
                for m in st.session_state["sql_history"]
            ]
            st.session_state["sql_history"].append({"role": "user", "content": suggestion})
            with st.spinner("Generating SQL and querying database…"):
                try:
                    result = client.rag_sql_query(suggestion, history=history_payload)
                    st.session_state["sql_history"].append({
                        "role":         "assistant",
                        "content":      result["answer"],
                        "sql":          result["sql"],
                        "columns":      result["columns"],
                        "rows":         result["rows"],
                        "count":        result["row_count"],
                        "heal_attempts": result.get("heal_attempts", 0),
                    })
                except ApiError as e:
                    st.session_state["sql_history"].append(
                        {"role": "assistant", "content": f"Error: {e}", "sql": "",
                         "columns": [], "rows": [], "count": 0, "heal_attempts": 0}
                    )
            st.rerun()

    st.markdown("---")

    # Chat history
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

    # Chat input
    sql_question = st.chat_input(
        "Ask a data question — follow-ups work, e.g. 'now show only the severe ones'",
        key="sql_input",
    )
    if sql_question:
        # Snapshot history before appending the new user message
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
                    result       = client.rag_sql_query(sql_question, history=history_payload)
                    answer       = result["answer"]
                    sql_out      = result["sql"]
                    columns      = result["columns"]
                    rows         = result["rows"]
                    count        = result["row_count"]
                    heal_attempts = result.get("heal_attempts", 0)
                except ApiError as e:
                    answer        = f"Error: {e}"
                    sql_out       = ""
                    columns       = []
                    rows          = []
                    count         = 0
                    heal_attempts = 0

            st.markdown(answer)
            if sql_out:
                heal_badge = f"  ·  🔧 healed {heal_attempts}x" if heal_attempts > 0 else ""
                with st.expander(f"🔍 Generated SQL  ·  {count} rows returned{heal_badge}"):
                    st.code(sql_out, language="sql")
                    if columns and rows:
                        df = pd.DataFrame(rows, columns=columns)
                        st.dataframe(df, use_container_width=True, hide_index=True)

            st.session_state["sql_history"].append({
                "role":          "assistant",
                "content":       answer,
                "sql":           sql_out,
                "columns":       columns,
                "rows":          rows,
                "count":         count,
                "heal_attempts": heal_attempts,
            })
        st.rerun()

    if st.session_state["sql_history"]:
        if st.button("🗑️ Clear SQL history", key="sql_clear"):
            st.session_state["sql_history"] = []
            st.rerun()
