import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import streamlit as st
from utils.api import ApiClient, ApiError
from utils.styles import page_header

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

page_header("📊", "RAG", "Analytics",
            subtitle="Query logs · Feedback · Response times · Top questions")
st.markdown("---")

# ── Fetch all data ─────────────────────────────────────────────────────────────
try:
    summary       = client.get_rag_analytics_summary()
    daily_raw     = client.get_rag_analytics_daily()
    top_questions = client.get_rag_analytics_top_questions()
except ApiError as e:
    st.error(f"Could not load analytics data: {e}")
    st.stop()

total = summary.get("total_queries", 0)

# ── KPI Row ────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Total Queries",    total)
c2.metric("Vector RAG",       summary.get("vector_queries", 0))
c3.metric("SQL Queries",      summary.get("sql_queries", 0))

avg_ms = summary.get("avg_response_ms", 0)
avg_s  = f"{avg_ms / 1000:.1f}s" if avg_ms >= 1000 else f"{avg_ms:.0f}ms"
c4.metric("Avg Response Time", avg_s)

thumbs_up   = summary.get("thumbs_up", 0)
thumbs_down = summary.get("thumbs_down", 0)
rated       = thumbs_up + thumbs_down
rate_pct    = f"{thumbs_up / rated * 100:.0f}%" if rated > 0 else "—"
c5.metric("👍 Rate", rate_pct, delta=f"{thumbs_up} up / {thumbs_down} down" if rated else None)

st.markdown("---")

if total == 0:
    st.info(
        "No queries logged yet. Use the **AI Chat** page to ask questions — "
        "every query is automatically tracked here."
    )
    st.stop()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_activity, tab_feedback, tab_questions = st.tabs([
    "📈 Activity",
    "👍 Feedback",
    "🔍 Top Questions",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Activity
# ═══════════════════════════════════════════════════════════════════════════════
with tab_activity:
    if not daily_raw:
        st.info("No queries in the last 14 days.")
    else:
        df_daily = pd.DataFrame(daily_raw)

        # ── Stacked bar: queries per day by type ──────────────────────────────
        fig_bar = px.bar(
            df_daily,
            x="day",
            y="count",
            color="query_type",
            barmode="stack",
            title="Daily Queries (last 14 days)",
            labels={"day": "Date", "count": "Queries", "query_type": "Type"},
            color_discrete_map={"vector": "#FF8400", "sql": "#388BFD"},
        )
        fig_bar.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E6EDF3",
            legend_title_text="",
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Line chart: avg response time per day (across all types) ─────────
        df_avg = (
            df_daily.groupby("day")
            .agg(avg_ms=("avg_ms", "mean"))
            .reset_index()
        )
        df_avg["avg_s"] = (df_avg["avg_ms"] / 1000).round(2)

        fig_line = px.line(
            df_avg,
            x="day",
            y="avg_s",
            title="Avg Response Time per Day (seconds)",
            labels={"day": "Date", "avg_s": "Avg (s)"},
            markers=True,
        )
        fig_line.update_traces(line_color="#3FB950", marker_color="#3FB950")
        fig_line.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E6EDF3",
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
        )
        st.plotly_chart(fig_line, use_container_width=True)

        # ── Raw table ─────────────────────────────────────────────────────────
        with st.expander("Raw daily data"):
            display = df_daily.copy()
            display["avg_ms"] = display["avg_ms"].round(0).astype(int)
            display.columns = ["Date", "Type", "Queries", "Avg ms"]
            st.dataframe(display, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Feedback
# ═══════════════════════════════════════════════════════════════════════════════
with tab_feedback:
    rated_total = thumbs_up + thumbs_down + summary.get("unrated", 0)

    col_pie, col_bar = st.columns(2)

    with col_pie:
        feedback_df = pd.DataFrame([
            {"Label": "👍 Helpful",   "Count": thumbs_up},
            {"Label": "👎 Not Helpful", "Count": thumbs_down},
            {"Label": "⬜ Unrated",  "Count": summary.get("unrated", 0)},
        ])
        fig_pie = px.pie(
            feedback_df,
            names="Label",
            values="Count",
            title="Feedback Distribution",
            color="Label",
            color_discrete_map={
                "👍 Helpful":     "#3FB950",
                "👎 Not Helpful": "#F85149",
                "⬜ Unrated":     "#484F58",
            },
            hole=0.45,
        )
        fig_pie.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E6EDF3",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        # Feedback by query type from top questions
        if top_questions:
            tq_df = pd.DataFrame(top_questions)
            total_up   = tq_df["thumbs_up"].sum()
            total_down = tq_df["thumbs_down"].sum()
            type_feedback = pd.DataFrame([
                {"Metric": "Thumbs Up",   "Count": int(total_up)},
                {"Metric": "Thumbs Down", "Count": int(total_down)},
            ])
            fig_feedback = px.bar(
                type_feedback,
                x="Metric",
                y="Count",
                title="Total Feedback Votes",
                color="Metric",
                color_discrete_map={
                    "Thumbs Up":   "#3FB950",
                    "Thumbs Down": "#F85149",
                },
            )
            fig_feedback.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E6EDF3",
                showlegend=False,
                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            )
            st.plotly_chart(fig_feedback, use_container_width=True)
        else:
            st.info("No feedback data yet.")

    if thumbs_down > 0 and top_questions:
        st.markdown("**Questions that received thumbs down:**")
        low_rated = [q for q in top_questions if q.get("thumbs_down", 0) > 0]
        if low_rated:
            for q in low_rated:
                st.markdown(
                    f'<span style="color:#F85149">👎</span> {q["question"]} '
                    f'<span style="color:#484F58; font-size:12px">({q["thumbs_down"]} thumbs down)</span>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No specific questions with thumbs down found in top 10.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Top Questions
# ═══════════════════════════════════════════════════════════════════════════════
with tab_questions:
    if not top_questions:
        st.info("No questions logged yet.")
    else:
        tq_df = pd.DataFrame(top_questions)

        # ── Horizontal bar chart ──────────────────────────────────────────────
        tq_sorted = tq_df.sort_values("count", ascending=True).tail(10)
        fig_q = px.bar(
            tq_sorted,
            x="count",
            y="question",
            orientation="h",
            title="Top 10 Questions by Frequency",
            labels={"count": "Times Asked", "question": ""},
            color="count",
            color_continuous_scale=[[0, "#1C2333"], [1, "#FF8400"]],
        )
        fig_q.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E6EDF3",
            coloraxis_showscale=False,
            yaxis=dict(tickfont=dict(size=12)),
            height=max(300, len(tq_sorted) * 45),
        )
        st.plotly_chart(fig_q, use_container_width=True)

        # ── Table ─────────────────────────────────────────────────────────────
        display_tq = tq_df.copy()
        display_tq["avg_ms"] = display_tq["avg_ms"].round(0).astype(int)
        display_tq["feedback"] = display_tq.apply(
            lambda r: f"👍 {int(r['thumbs_up'])}  👎 {int(r['thumbs_down'])}", axis=1
        )
        display_tq = display_tq[["question", "count", "avg_ms", "feedback"]]
        display_tq.columns = ["Question", "Times Asked", "Avg ms", "Feedback"]
        st.dataframe(display_tq, use_container_width=True, hide_index=True)
