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

page_header("🤖", "AI", "Chat",
            subtitle="Ask questions about clinical trial data")
st.markdown("---")

# ── Initialize chat history ────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Display chat history ───────────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"], avatar="🧬" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        if "sources" in msg and msg["sources"]:
            with st.expander("📚 Sources"):
                for i, source in enumerate(msg["sources"], 1):
                    st.markdown(
                        f"""
                        **Source {i}**: {source['source_type']} (ID: {source['source_id']})

                        > {source['chunk_text'][:300]}...
                        """
                    )

# ── Suggested questions ───────────────────────────────────────────────────────
if not st.session_state.chat_history:
    st.markdown("### 💡 Suggested Questions")
    suggestions = [
        "Which subjects had severe adverse events?",
        "What were the abnormal lab results at Week 12?",
        "How many subjects are enrolled at the London site?",
        "What is the protocol objective of CARDIO-2024?",
        "List all subjects who have completed the trial.",
    ]
    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            if st.button(suggestion, use_container_width=True, key=f"suggest_{i}"):
                st.session_state._suggested_question = suggestion
                st.rerun()

# ── Chat input ─────────────────────────────────────────────────────────────────
st.markdown("---")

col1, col2 = st.columns([5, 1])
with col1:
    user_input = st.chat_input("Ask a question about the clinical trial...")
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    clear_btn = st.button("🗑️ Clear", use_container_width=True)

if clear_btn:
    st.session_state.chat_history = []
    st.rerun()

# Handle suggested question click
if "_suggested_question" in st.session_state and st.session_state._suggested_question:
    user_input = st.session_state._suggested_question
    st.session_state._suggested_question = None

# ── Process user message ───────────────────────────────────────────────────────
if user_input:
    # Add user message to history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "sources": []
    })

    # Display user message
    with st.chat_message("user", avatar="🧬"):
        st.markdown(user_input)

    # Show typing indicator
    with st.spinner("🤖 Thinking..."):
        try:
            # Call RAG API
            result = client.chat_rag(question=user_input, top_k=5)
            answer = result.get("answer", "")
            sources = result.get("sources", [])

            # Add assistant message to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": answer,
                "sources": sources
            })

            # Display assistant message with streaming effect
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(answer)

                if sources:
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(sources, 1):
                            st.markdown(
                                f"""
                                **Source {i}**: {source['source_type']} (ID: {source['source_id']})

                                > {source['chunk_text'][:300]}...
                                """
                            )
                else:
                    st.warning("⚠️ No relevant sources found for this question.")

            # Rerun to update chat display
            time.sleep(0.5)
            st.rerun()

        except ApiError as e:
            st.error(f"❌ Error: {e}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")

# ── Status indicator ───────────────────────────────────────────────────────────
st.markdown("---")

try:
    rag_st = client.rag_status()
    ollama_ready = rag_st.get("ollama_ready", False)
    chunk_count = rag_st.get("chunk_count", 0)
    embed_model = rag_st.get("embed_model", "unknown")
    llm_model = rag_st.get("llm_model", "unknown")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        status_color = "🟢" if ollama_ready else "🔴"
        st.metric("Ollama Status", status_color, "Ready" if ollama_ready else "Down")
    with col2:
        st.metric("Chunks Indexed", chunk_count)
    with col3:
        st.metric("Embed Model", embed_model.split(":")[0] if ":" in embed_model else embed_model)
    with col4:
        st.metric("LLM Model", llm_model.split(":")[0] if ":" in llm_model else llm_model)

except ApiError:
    st.warning("⚠️ Unable to fetch RAG status")
