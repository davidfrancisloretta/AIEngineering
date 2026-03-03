import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.api import ApiClient, ApiError

DEMO_EMAIL    = "demo@raveanalytics.com"
DEMO_PASSWORD = "Demo1234!"

# ── Centred 3-column layout ───────────────────────────────────────────────────
col_l, col_m, col_r = st.columns([1, 1.6, 1])

with col_m:

    # ── Brand header ─────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; padding: 32px 0 24px 0;">
            <div style="
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 64px; height: 64px;
                background: rgba(255,132,0,0.12);
                border: 1px solid rgba(255,132,0,0.35);
                border-radius: 18px;
                font-size: 32px;
                margin-bottom: 16px;
            ">🧬</div>
            <h1 style="
                font-family: 'JetBrains Mono', monospace;
                font-size: 28px;
                font-weight: 700;
                color: #E6EDF3;
                margin: 0 0 6px 0;
                letter-spacing: -0.02em;
            ">RAVE <span style='color:#FF8400;'>AI</span></h1>
            <p style="
                font-family: 'Geist', sans-serif;
                font-size: 14px;
                color: #8B949E;
                margin: 0;
            ">Clinical Trial Intelligence Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Demo quick-access card ────────────────────────────────────────────────
    st.markdown(
        """
        <div style="
            background: rgba(255,132,0,0.08);
            border: 1px solid rgba(255,132,0,0.25);
            border-radius: 16px;
            padding: 16px 20px;
            margin-bottom: 20px;
        ">
            <div style="
                font-family: 'Geist', sans-serif;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #FF8400;
                margin-bottom: 8px;
            ">⚡ Live Demo Access</div>
            <div style="
                font-family: 'JetBrains Mono', monospace;
                font-size: 13px;
                color: #E6EDF3;
                line-height: 1.8;
            ">
                <span style="color:#8B949E;">email</span> &nbsp;demo@raveanalytics.com<br>
                <span style="color:#8B949E;">pass &nbsp;</span> Demo1234!
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⚡  One-Click Demo Login", use_container_width=True, type="primary"):
        try:
            data = ApiClient().login(DEMO_EMAIL, DEMO_PASSWORD)
            st.session_state["token"]   = data["access_token"]
            st.session_state["email"]   = DEMO_EMAIL
            st.session_state["is_demo"] = True
            st.rerun()
        except ApiError as e:
            st.error(f"Demo login failed: {e}")

    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin:16px 0;">'
        '<div style="flex:1;height:1px;background:rgba(255,255,255,0.08);"></div>'
        '<span style="font-size:12px;color:#484F58;font-family:Geist,sans-serif;">or sign in manually</span>'
        '<div style="flex:1;height:1px;background:rgba(255,255,255,0.08);"></div>'
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Login / Register tabs ────────────────────────────────────────────────
    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            email    = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button(
                "Sign In", use_container_width=True, type="primary"
            )

        if submitted:
            if not email or not password:
                st.error("Please fill in both fields.")
            else:
                try:
                    data = ApiClient().login(email, password)
                    st.session_state["token"]   = data["access_token"]
                    st.session_state["email"]   = email
                    st.session_state["is_demo"] = False
                    st.rerun()
                except ApiError as e:
                    st.error(f"Login failed: {e}")

    with tab_register:
        with st.form("register_form"):
            reg_email    = st.text_input("Email address", placeholder="you@example.com", key="reg_email")
            reg_password = st.text_input("Password", type="password", placeholder="••••••••", key="reg_pass")
            reg_confirm  = st.text_input("Confirm password", type="password", placeholder="••••••••", key="reg_confirm")
            reg_submitted = st.form_submit_button(
                "Create Account", use_container_width=True, type="primary"
            )

        if reg_submitted:
            if not reg_email or not reg_password:
                st.error("Please fill in all fields.")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    ApiClient().register(reg_email, reg_password)
                    st.success("Account created! Please sign in.")
                except ApiError as e:
                    st.error(f"Registration failed: {e}")

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown(
        '<p style="text-align:center;font-size:12px;color:#484F58;'
        'font-family:Geist,sans-serif;margin-top:32px;">'
        "RAVE AI · Clinical Trial Intelligence · v1.0"
        "</p>",
        unsafe_allow_html=True,
    )
