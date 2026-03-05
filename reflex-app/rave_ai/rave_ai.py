"""
RAVE AI - Main App Entry Point
Reflex Framework
"""
import reflex as rx
from rave_ai.state import AppState, DashboardState, ChatState, TrialDataState, OnboardingState, OdmUploadState
from rave_ai.pages import (
    login,
    dashboard,
    settings,
    clinical_trials,
    onboarding,
    rag_chat,
    rag_analytics,
    fetch_data,
    signed_out,
)


def index() -> rx.Component:
    """Root: spinner shown briefly while on_load fires the redirect"""
    return rx.center(rx.spinner(), min_height="100vh")


# In Reflex 0.8.x, App() takes no config argument — config lives in rxconfig.py
app = rx.App()

# Register pages — on_load handlers passed here, not in page components
app.add_page(index, route="/", title="RAVE AI",
             on_load=AppState.index_redirect)
app.add_page(login.login_page, route="/login", title="Login - RAVE AI")
app.add_page(signed_out.signed_out_page, route="/signed-out", title="Signed Out - RAVE AI")
app.add_page(dashboard.dashboard_page, route="/dashboard", title="Dashboard - RAVE AI",
             on_load=[AppState.check_auth, DashboardState.load_data])
app.add_page(onboarding.onboarding_page, route="/onboarding", title="Getting Started - RAVE AI",
             on_load=[AppState.check_auth, OnboardingState.load_status])
app.add_page(clinical_trials.clinical_trials_page, route="/trials", title="Trial Data - RAVE AI",
             on_load=[AppState.check_auth, TrialDataState.load_data])
app.add_page(settings.settings_page, route="/settings", title="Settings - RAVE AI",
             on_load=AppState.check_auth)
app.add_page(rag_chat.rag_chat_page, route="/chat", title="AI Chat - RAVE AI",
             on_load=[AppState.check_auth, ChatState.load_status])
app.add_page(rag_analytics.rag_analytics_page, route="/analytics", title="Analytics - RAVE AI",
             on_load=[AppState.check_auth, DashboardState.load_data])
app.add_page(fetch_data.fetch_data_page, route="/fetch-data", title="Fetch Data - RAVE AI",
             on_load=[AppState.check_auth])
