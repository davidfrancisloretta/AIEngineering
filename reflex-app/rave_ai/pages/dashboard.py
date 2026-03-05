"""
Dashboard Page — Lunaris design system
"""
import reflex as rx
from rave_ai.state import DashboardState
from rave_ai.layout import page_layout
from rave_ai import theme as T


def kpi_card(label: str, value, icon: str = "📊") -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(label.upper(), font_family=T.FONT_MONO, font_size="9px",
                        font_weight="600", color=T.MUTED_FG, letter_spacing="0.08em",
                        overflow="hidden", text_overflow="ellipsis", white_space="nowrap"),
                rx.spacer(),
                rx.text(icon, font_size="13px"),
                width="100%", align="center",
            ),
            rx.text(value, font_family=T.FONT_MONO, font_size="20px",
                    font_weight="700", color=T.FG,
                    overflow="hidden", text_overflow="ellipsis", white_space="nowrap",
                    width="100%"),
            spacing="1", width="100%", align="start",
        ),
        padding="12px 14px",
        background_color=T.CARD,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS_S,
        width="100%",
        style={"boxShadow": T.SHADOW_SM},
    )


def question_row(q) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(q["question"], font_family=T.FONT_BODY, font_size="14px",
                    color=T.FG, font_weight="500",
                    text_overflow="ellipsis", overflow="hidden", white_space="nowrap"),
            rx.hstack(
                rx.box(
                    rx.text(q["count"], font_family=T.FONT_MONO, font_size="12px",
                            color=T.PRIMARY, font_weight="600"),
                    padding="2px 10px",
                    background_color=f"{T.PRIMARY}15",
                    border_radius=T.RADIUS_PILL,
                    border=f"1px solid {T.PRIMARY}40",
                ),
                rx.box(
                    rx.text(q["avg_ms"], font_family=T.FONT_MONO, font_size="12px",
                            color=T.MUTED_FG),
                    padding="2px 10px",
                    background_color=T.MUTED_BG,
                    border_radius=T.RADIUS_PILL,
                ),
                rx.box(
                    rx.text(q["thumbs_up"], font_family=T.FONT_MONO, font_size="12px",
                            color=T.SUCCESS),
                    padding="2px 10px",
                    background_color="#22C55E15",
                    border_radius=T.RADIUS_PILL,
                ),
                rx.box(
                    rx.text(q["thumbs_down"], font_family=T.FONT_MONO, font_size="12px",
                            color=T.ERROR),
                    padding="2px 10px",
                    background_color="#EF444415",
                    border_radius=T.RADIUS_PILL,
                ),
                spacing="2", align="center",
            ),
            spacing="1", width="100%", align="start",
        ),
        padding="14px 18px",
        background_color=T.CARD,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS_S,
        width="100%",
        _hover={"border_color": T.PRIMARY, "style": {"boxShadow": T.SHADOW_SM}},
        transition="border-color 0.15s ease",
    )


def dashboard_page() -> rx.Component:
    return page_layout(rx.box(
        rx.vstack(

            # ── Page header ──────────────────────────────────────────
            rx.box(
                rx.vstack(
                    rx.text("Analytics Dashboard", font_family=T.FONT_MONO,
                            font_size="24px", font_weight="700", color=T.FG),
                    rx.text("RAG system performance and query metrics",
                            font_family=T.FONT_BODY, font_size="14px", color=T.MUTED_FG),
                    spacing="1", align="start",
                ),
                padding="24px 32px 20px",
                border_bottom=f"1px solid {T.BORDER}",
                background_color=T.CARD,
                width="100%",
            ),

            # ── Body ────────────────────────────────────────────────
            rx.box(
                rx.vstack(

                    # Loading
                    rx.cond(
                        DashboardState.is_loading,
                        rx.hstack(
                            rx.spinner(color=T.PRIMARY),
                            rx.text("Loading analytics…", font_family=T.FONT_BODY,
                                    color=T.MUTED_FG),
                            spacing="3", padding="2rem",
                        ),
                    ),

                    # Error
                    rx.cond(
                        DashboardState.load_error != "",
                        rx.box(
                            rx.hstack(
                                rx.text("⚠️"),
                                rx.text(DashboardState.load_error, font_family=T.FONT_BODY,
                                        color=T.ERROR_FG, font_size="14px"),
                                spacing="2",
                            ),
                            padding="14px 18px",
                            background_color=T.ERROR_BG,
                            border_radius=T.RADIUS_S,
                            border=f"1px solid #D4A0A0",
                            width="100%",
                        ),
                    ),

                    # KPI cards — single row of 6
                    rx.cond(
                        ~DashboardState.is_loading,
                        rx.grid(
                            kpi_card("Total Queries",   DashboardState.total_queries,   "🔍"),
                            kpi_card("Vector",          DashboardState.vector_queries,  "🧠"),
                            kpi_card("SQL",             DashboardState.sql_queries,     "🗄️"),
                            kpi_card("Avg Response s",  DashboardState.avg_response_s,  "⚡"),
                            kpi_card("👍 Up",           DashboardState.thumbs_up,       "✅"),
                            kpi_card("👎 Down",         DashboardState.thumbs_down,     "❌"),
                            columns="6", spacing="3", width="100%",
                        ),
                    ),

                    # Tabs
                    rx.tabs.root(
                        rx.box(
                            rx.tabs.list(
                                rx.tabs.trigger(
                                    "Daily Activity", value="daily",
                                    font_family=T.FONT_BODY, font_size="13px",
                                ),
                                rx.tabs.trigger(
                                    "Top Questions", value="questions",
                                    font_family=T.FONT_BODY, font_size="13px",
                                ),
                                rx.tabs.trigger(
                                    "Query Breakdown", value="breakdown",
                                    font_family=T.FONT_BODY, font_size="13px",
                                ),
                            ),
                            padding_bottom="0",
                        ),

                        # Tab 1 — Daily Activity
                        rx.tabs.content(
                            rx.box(
                                rx.vstack(
                                    rx.text("Daily Query Activity", font_family=T.FONT_MONO,
                                            font_size="15px", font_weight="600", color=T.FG),
                                    rx.cond(
                                        DashboardState.has_daily_stats,
                                        rx.box(
                                            rx.data_table(
                                                data=DashboardState.daily_stats,
                                                columns=["day", "query_type", "count", "avg_ms"],
                                                pagination=True, search=True, sort=True,
                                            ),
                                            background_color=T.CARD,
                                            border=f"1px solid {T.BORDER}",
                                            border_radius=T.RADIUS_M,
                                            overflow="hidden",
                                        ),
                                        rx.box(
                                            rx.text("No daily data yet — run some queries in AI Chat.",
                                                    font_family=T.FONT_BODY, color=T.MUTED_FG,
                                                    font_size="14px"),
                                            padding="32px", text_align="center", width="100%",
                                        ),
                                    ),
                                    spacing="3", width="100%", padding_top="12px",
                                ),
                                overflow_y="auto",
                                max_height="calc(100vh - 320px)",
                                padding_right="4px",
                            ),
                            value="daily",
                        ),

                        # Tab 2 — Top Questions
                        rx.tabs.content(
                            rx.box(
                                rx.vstack(
                                    rx.text("Top Questions", font_family=T.FONT_MONO,
                                            font_size="15px", font_weight="600", color=T.FG),
                                    rx.cond(
                                        DashboardState.has_top_questions,
                                        rx.vstack(
                                            rx.foreach(DashboardState.top_questions, question_row),
                                            spacing="2", width="100%",
                                        ),
                                        rx.box(
                                            rx.text("No questions tracked yet.",
                                                    font_family=T.FONT_BODY, color=T.MUTED_FG,
                                                    font_size="14px"),
                                            padding="32px", text_align="center", width="100%",
                                        ),
                                    ),
                                    spacing="3", width="100%", padding_top="12px",
                                ),
                                overflow_y="auto",
                                max_height="calc(100vh - 320px)",
                                padding_right="4px",
                            ),
                            value="questions",
                        ),

                        # Tab 3 — Query Breakdown
                        rx.tabs.content(
                            rx.vstack(
                                rx.text("Query Type Breakdown", font_family=T.FONT_MONO,
                                        font_size="16px", font_weight="600", color=T.FG),
                                rx.grid(
                                    rx.box(
                                        rx.vstack(
                                            rx.text("Vector Queries", font_family=T.FONT_BODY,
                                                    font_size="13px", color=T.MUTED_FG,
                                                    font_weight="500"),
                                            rx.text(DashboardState.vector_queries,
                                                    font_family=T.FONT_MONO, font_size="36px",
                                                    font_weight="700", color=T.PRIMARY),
                                            rx.text("Semantic search", font_family=T.FONT_BODY,
                                                    font_size="12px", color=T.MUTED_FG),
                                            spacing="1", align="start",
                                        ),
                                        padding="24px",
                                        background_color=f"{T.PRIMARY}0A",
                                        border=f"1px solid {T.PRIMARY}30",
                                        border_radius=T.RADIUS_M,
                                    ),
                                    rx.box(
                                        rx.vstack(
                                            rx.text("SQL Queries", font_family=T.FONT_BODY,
                                                    font_size="13px", color=T.MUTED_FG,
                                                    font_weight="500"),
                                            rx.text(DashboardState.sql_queries,
                                                    font_family=T.FONT_MONO, font_size="36px",
                                                    font_weight="700", color="#E07B39"),
                                            rx.text("Structured database", font_family=T.FONT_BODY,
                                                    font_size="12px", color=T.MUTED_FG),
                                            spacing="1", align="start",
                                        ),
                                        padding="24px",
                                        background_color="#E07B390A",
                                        border=f"1px solid #E07B3930",
                                        border_radius=T.RADIUS_M,
                                    ),
                                    columns="2", spacing="4", width="100%",
                                ),
                                spacing="4", width="100%", padding_top="16px",
                            ),
                            value="breakdown",
                        ),

                        default_value="daily",
                        width="100%",
                    ),

                    spacing="3", width="100%",
                ),
                padding="16px 24px",
                width="100%",
            ),

            spacing="0", width="100%",
        ),
        width="100%",
        min_height="100vh",
        background_color=T.BACKGROUND,
    ))
