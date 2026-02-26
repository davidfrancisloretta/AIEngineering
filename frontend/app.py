import streamlit as st

st.set_page_config(
    page_title="Rave Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "token" not in st.session_state:
    # Only show the login page — hide navigation
    pg = st.navigation(
        [st.Page("pages/Login.py", title="Login", icon="🔐")],
        position="hidden",
    )
else:
    pg = st.navigation(
        {
            "Analytics": [
                st.Page("pages/Dashboard.py", title="Dashboard", icon="📊"),
                st.Page("pages/Fetch_Data.py", title="Fetch Data", icon="🔄"),
            ],
            "Account": [
                st.Page("pages/Settings.py", title="Settings", icon="⚙️"),
            ],
        }
    )

pg.run()
