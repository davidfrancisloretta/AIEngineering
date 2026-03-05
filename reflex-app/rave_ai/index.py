"""
RAVE AI - Main App Entry Point
Reflex Framework
"""
import reflex as rx
from rave_ai.state import AppState
from rave_ai.pages import (
    login,
    dashboard,
    settings,
    clinical_trials,
    onboarding,
    rag_chat,
    rag_analytics,
    fetch_data
)


def index() -> rx.Component:
    """Root redirect — send authenticated users to dashboard, others to login"""
    return rx.cond(
        AppState.is_authenticated,
        rx.box(
            rx.script("window.location.href='/dashboard'"),
            rx.text("Redirecting to dashboard...")
        ),
        rx.box(
            rx.script("window.location.href='/login'"),
            rx.text("Redirecting to login...")
        )
    )


# ════════════════════════════════════════════════════════════════════════════
# APP CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

config = rx.Config(
    app_name="rave_ai",
    db_url="sqlite:///reflex.db",
)

app = rx.App(config=config)

# Register main layout
app.add_page(index, route="/", title="RAVE AI")

# Auth Pages
app.add_page(login.login_page, route="/login", title="Login - RAVE AI")

# Analytics Pages
app.add_page(dashboard.dashboard_page, route="/dashboard", title="Dashboard - RAVE AI")

# Clinical Trials Pages
app.add_page(onboarding.onboarding_page, route="/onboarding", title="Getting Started - RAVE AI")
app.add_page(clinical_trials.clinical_trials_page, route="/trials", title="Trial Data - RAVE AI")

# Account Pages
app.add_page(settings.settings_page, route="/settings", title="Settings - RAVE AI")

# RAG Chat Pages
app.add_page(rag_chat.rag_chat_page, route="/chat", title="AI Chat - RAVE AI")
app.add_page(rag_analytics.rag_analytics_page, route="/analytics", title="Analytics - RAVE AI")
app.add_page(fetch_data.fetch_data_page, route="/fetch-data", title="Fetch Data - RAVE AI")
