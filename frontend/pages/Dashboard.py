import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api import ApiClient, ApiError

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

st.title("📊 Dashboard")
st.markdown(f"Logged in as **{st.session_state.get('email', '')}**")
st.markdown("---")

tab_rave, tab_campaign = st.tabs(["Rave Transactions", "Campaign Metrics"])

# ======================================================
# TAB 1 — Rave Transactions
# ======================================================
with tab_rave:
    try:
        transactions = client.get_transactions()
    except ApiError:
        transactions = []

    if not transactions:
        st.info(
            "No Rave transaction data yet. "
            "Go to **Fetch Data** to pull transactions from the Rave API."
        )
    else:
        df = pd.DataFrame(transactions)
        df["fetched_at"] = pd.to_datetime(df["fetched_at"])
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        # ── KPI row ──────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        total = len(df)
        revenue = df["amount"].sum()
        success = (df["status"] == "successful").sum()
        rate = f"{success / total * 100:.1f}%" if total else "—"
        top_cur = df["currency"].mode()[0] if total else "—"

        k1.metric("Total Transactions", total)
        k2.metric("Total Revenue", f"{revenue:,.2f}")
        k3.metric("Success Rate", rate)
        k4.metric("Top Currency", top_cur)

        st.markdown("---")

        # ── Charts row 1 ─────────────────────────────────
        c1, c2 = st.columns(2)

        with c1:
            daily = (
                df.groupby(df["fetched_at"].dt.date)["amount"]
                .sum()
                .reset_index()
                .rename(columns={"fetched_at": "Date", "amount": "Revenue"})
            )
            fig = px.line(daily, x="Date", y="Revenue", title="Revenue Over Time", markers=True)
            fig.update_layout(margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            status_df = df["status"].value_counts().reset_index()
            status_df.columns = ["Status", "Count"]
            fig = px.pie(
                status_df, values="Count", names="Status",
                title="Transaction Status", hole=0.35,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        # ── Charts row 2 ─────────────────────────────────
        c3, c4 = st.columns(2)

        with c3:
            pay_df = df["payment_type"].value_counts().reset_index()
            pay_df.columns = ["Payment Method", "Count"]
            fig = px.bar(
                pay_df, x="Payment Method", y="Count",
                title="Payment Methods",
                color="Payment Method",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(showlegend=False, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with c4:
            cur_df = df.groupby("currency")["amount"].sum().reset_index()
            cur_df.columns = ["Currency", "Revenue"]
            fig = px.bar(
                cur_df, x="Currency", y="Revenue",
                title="Revenue by Currency",
                color="Currency",
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig.update_layout(showlegend=False, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        # ── Recent transactions table ─────────────────────
        st.markdown("---")
        st.subheader("Recent Transactions")
        show_cols = ["transaction_ref", "amount", "currency", "status", "payment_type", "customer_email", "fetched_at"]
        display = df[show_cols].copy()
        display.columns = ["Ref", "Amount", "Currency", "Status", "Payment", "Customer", "Fetched At"]
        st.dataframe(display.head(25), use_container_width=True)

# ======================================================
# TAB 2 — Campaign Metrics
# ======================================================
with tab_campaign:
    try:
        metrics = client.get_metrics()
    except ApiError:
        metrics = []

    if not metrics:
        st.info("No campaign metrics yet. Use the API to create some.")
    else:
        mdf = pd.DataFrame(metrics)

        mk1, mk2, mk3 = st.columns(3)
        mk1.metric("Total Campaigns", len(mdf))
        mk2.metric("Avg CTR", f"{mdf['ttr'].mean():.2%}")
        mk3.metric("Avg CVR", f"{mdf['cvr'].mean():.2%}")

        st.markdown("---")

        mc1, mc2 = st.columns(2)

        with mc1:
            fig = px.bar(
                mdf, x="campaign_name", y=["ttr", "vtr", "cvr"],
                barmode="group", title="Rates by Campaign",
                labels={"value": "Rate", "variable": "Metric"},
                color_discrete_sequence=px.colors.qualitative.Set1,
            )
            fig.update_layout(margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with mc2:
            fig = px.scatter(
                mdf, x="impressions", y="conversions",
                size="clicks", color="campaign_name",
                title="Impressions vs Conversions",
                hover_data=["campaign_name"],
            )
            fig.update_layout(margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("All Campaigns")
        st.dataframe(mdf, use_container_width=True)
