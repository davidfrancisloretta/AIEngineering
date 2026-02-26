import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from utils.api import ApiClient, ApiError

DEMO_EMAIL = "demo@raveanalytics.com"
DEMO_PASSWORD = "Demo1234!"

col_l, col_m, col_r = st.columns([1, 2, 1])

with col_m:
    st.markdown(
        "<h1 style='text-align:center;'>📊 Rave Analytics</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center; color:#555;'>Campaign & payment intelligence platform</p>",
        unsafe_allow_html=True,
    )

    # ── Demo banner ──────────────────────────────────────
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%);
            border-radius: 10px;
            padding: 16px 20px;
            margin: 12px 0;
            color: white;
        ">
            <div style="font-size:15px; font-weight:700; margin-bottom:6px;">
                🚀 Try the Live Demo
            </div>
            <div style="font-size:13px; opacity:0.92; line-height:1.6;">
                <b>Email:</b> demo@raveanalytics.com<br>
                <b>Password:</b> Demo1234!
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⚡ One-Click Demo Login", use_container_width=True, type="primary"):
        try:
            data = ApiClient().login(DEMO_EMAIL, DEMO_PASSWORD)
            st.session_state["token"] = data["access_token"]
            st.session_state["email"] = DEMO_EMAIL
            st.session_state["is_demo"] = True
            st.rerun()
        except ApiError as e:
            st.error(f"Demo login failed: {e}")

    st.markdown("---")
    tab_login, tab_register = st.tabs(["Login", "Create Account"])

    # ── Login tab ────────────────────────────────────────
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("Please fill in both fields.")
            else:
                try:
                    data = ApiClient().login(email, password)
                    st.session_state["token"] = data["access_token"]
                    st.session_state["email"] = email
                    st.session_state["is_demo"] = False
                    st.rerun()
                except ApiError as e:
                    st.error(f"Login failed: {e}")

    # ── Register tab ──────────────────────────────────────
    with tab_register:
        with st.form("register_form"):
            reg_email = st.text_input("Email address", placeholder="you@example.com", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_pass")
            reg_confirm = st.text_input("Confirm password", type="password", key="reg_confirm")
            reg_submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

        if reg_submitted:
            if not reg_email or not reg_password:
                st.error("Please fill in all fields.")
            elif reg_password != reg_confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    ApiClient().register(reg_email, reg_password)
                    st.success("Account created! Please log in.")
                except ApiError as e:
                    st.error(f"Registration failed: {e}")
