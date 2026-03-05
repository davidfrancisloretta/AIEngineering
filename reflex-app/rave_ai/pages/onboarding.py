"""
Onboarding Wizard — Lunaris design system
"""
import reflex as rx
from rave_ai.layout import page_layout
from rave_ai.state import OnboardingState
from rave_ai import theme as T


def _step_pill(num: str, label: str, is_active, is_done) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.cond(is_done, rx.text("✓", font_size="14px", font_weight="700"),
                    rx.text(num, font_size="13px", font_weight="700")),
            width="32px", height="32px",
            border_radius=T.RADIUS_PILL,
            background_color=rx.cond(is_active | is_done, T.PRIMARY, T.BORDER),
            color=rx.cond(is_active | is_done, T.PRIMARY_FG, T.MUTED_FG),
            display="flex", align_items="center", justify_content="center",
        ),
        rx.text(label, font_family=T.FONT_BODY, font_size="13px",
                font_weight=rx.cond(is_active, "600", "400"),
                color=rx.cond(is_active | is_done, T.FG, T.MUTED_FG)),
        spacing="2", align="center",
    )


def _info_box(items: list) -> rx.Component:
    return rx.box(
        rx.vstack(
            *[rx.hstack(
                rx.box(width="6px", height="6px", border_radius="50%",
                       background_color=T.PRIMARY, flex_shrink="0", margin_top="6px"),
                rx.text(item, font_family=T.FONT_BODY, font_size="13px", color=T.FG),
                spacing="2", align="start",
            ) for item in items],
            spacing="2", align="start",
        ),
        padding="16px 20px",
        background_color=T.INFO_BG,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS_S,
    )


def onboarding_page() -> rx.Component:
    return page_layout(rx.box(

        # Page header
        rx.box(
            rx.vstack(
                rx.text("Getting Started", font_family=T.FONT_MONO,
                        font_size="24px", font_weight="700", color=T.FG),
                rx.text("3 steps to your first AI-powered clinical data query",
                        font_family=T.FONT_BODY, font_size="14px", color=T.MUTED_FG),
                spacing="1", align="start",
            ),
            padding="24px 32px 20px",
            border_bottom=f"1px solid {T.BORDER}",
            background_color=T.CARD,
            width="100%",
        ),

        rx.box(
            rx.vstack(

                # Step progress bar
                rx.box(
                    rx.hstack(
                        _step_pill("1", "Seed Data",
                                   OnboardingState.step == 0,
                                   OnboardingState.step > 0),
                        rx.box(height="1px", width="60px", background_color=T.BORDER),
                        _step_pill("2", "Ingest for RAG",
                                   OnboardingState.step == 1,
                                   OnboardingState.step > 1),
                        rx.box(height="1px", width="60px", background_color=T.BORDER),
                        _step_pill("3", "Ask a Question",
                                   OnboardingState.step == 2,
                                   OnboardingState.step > 2),
                        spacing="3", align="center", justify="center",
                    ),
                    padding="20px 24px",
                    background_color=T.CARD,
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_M,
                    width="100%",
                    display="flex",
                    justify_content="center",
                ),

                # ── STEP 0: Seed Data ───────────────────────────────
                rx.cond(
                    OnboardingState.step == 0,
                    rx.box(
                        rx.vstack(
                            rx.text("Step 1 — Seed Demo Data",
                                    font_family=T.FONT_MONO, font_size="18px",
                                    font_weight="600", color=T.FG),
                            rx.text(
                                "Load the CARDIO-2024 Phase III demo dataset. This creates 20 synthetic "
                                "subjects across 5 clinical sites with visits, adverse events, lab results.",
                                font_family=T.FONT_BODY, font_size="14px", color=T.MUTED_FG,
                                line_height="1.6",
                            ),
                            rx.hstack(
                                rx.button(
                                    rx.cond(
                                        OnboardingState.seed_loading,
                                        rx.hstack(rx.spinner(size="2"),
                                                  rx.text("Seeding…", font_family=T.FONT_MONO,
                                                          font_size="14px"), spacing="2"),
                                        rx.text("🧬  Seed Demo Data", font_family=T.FONT_MONO,
                                                font_size="14px", font_weight="500"),
                                    ),
                                    on_click=OnboardingState.seed_demo_data,
                                    disabled=OnboardingState.seed_loading,
                                    height="44px", padding="0 24px",
                                    border_radius=T.RADIUS_PILL,
                                    background_color=T.PRIMARY,
                                    color=T.PRIMARY_FG,
                                    cursor="pointer",
                                    _hover={"background_color": T.PRIMARY_HOVER},
                                    style={"boxShadow": T.SHADOW_PRIMARY},
                                ),
                                rx.button(
                                    "Skip →", variant="outline", size="2",
                                    font_family=T.FONT_BODY,
                                    border_radius=T.RADIUS_PILL,
                                    border=f"1px solid {T.BORDER}",
                                    color=T.MUTED_FG,
                                    on_click=OnboardingState.go_to_step(1),
                                    cursor="pointer",
                                ),
                                spacing="3", align="center",
                            ),
                            _info_box([
                                "1 clinical study (CARDIO-2024, Phase III)",
                                "20 subjects across 5 sites",
                                "5 visits per subject",
                                "Vital signs, adverse events, lab results",
                            ]),
                            rx.cond(
                                OnboardingState.seed_error != "",
                                rx.box(
                                    rx.hstack(
                                        rx.text("⚠️"),
                                        rx.text(OnboardingState.seed_error,
                                                font_family=T.FONT_BODY, font_size="13px",
                                                color=T.ERROR_FG),
                                        spacing="2",
                                    ),
                                    padding="12px 16px",
                                    background_color=T.ERROR_BG,
                                    border_radius=T.RADIUS_S,
                                    border=f"1px solid #D4A0A0",
                                ),
                            ),
                            rx.cond(
                                OnboardingState.seed_done,
                                rx.box(
                                    rx.hstack(
                                        rx.text("✅", font_size="16px"),
                                        rx.text("Demo data loaded successfully!",
                                                font_family=T.FONT_BODY, font_size="14px",
                                                color="#004D1A", font_weight="500"),
                                        spacing="2",
                                    ),
                                    padding="12px 16px",
                                    background_color="#DFE6E1",
                                    border_radius=T.RADIUS_S,
                                    border=f"1px solid #A0C4A0",
                                ),
                            ),
                            spacing="4", width="100%", align="start",
                        ),
                        padding="28px",
                        background_color=T.CARD,
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_M,
                        width="100%",
                        style={"boxShadow": T.SHADOW_SM},
                    ),
                ),

                # ── STEP 1: Ingest ──────────────────────────────────
                rx.cond(
                    OnboardingState.step == 1,
                    rx.box(
                        rx.vstack(
                            rx.text("Step 2 — Ingest Data for AI Chat",
                                    font_family=T.FONT_MONO, font_size="18px",
                                    font_weight="600", color=T.FG),
                            rx.text(
                                "Convert all clinical records into vector embeddings so the AI can "
                                "retrieve relevant context when you ask questions.",
                                font_family=T.FONT_BODY, font_size="14px", color=T.MUTED_FG,
                                line_height="1.6",
                            ),
                            rx.cond(
                                OnboardingState.ingest_running,
                                rx.vstack(
                                    rx.progress(value=OnboardingState.ingest_progress,
                                                max=100, width="100%",
                                                color_scheme="orange"),
                                    rx.hstack(
                                        rx.spinner(size="2", color=T.PRIMARY),
                                        rx.text(
                                            "Embedding in progress… ",
                                            OnboardingState.ingest_progress, "%",
                                            font_family=T.FONT_BODY, font_size="13px",
                                            color=T.MUTED_FG,
                                        ),
                                        spacing="2", align="center",
                                    ),
                                    spacing="2", width="100%",
                                ),
                            ),
                            rx.cond(
                                ~OnboardingState.ingest_running,
                                rx.hstack(
                                    rx.button(
                                        "🔍  Ingest for RAG",
                                        on_click=OnboardingState.start_ingest,
                                        disabled=OnboardingState.ingest_done,
                                        height="44px", padding="0 24px",
                                        border_radius=T.RADIUS_PILL,
                                        background_color=T.PRIMARY,
                                        color=T.PRIMARY_FG,
                                        cursor="pointer",
                                        _hover={"background_color": T.PRIMARY_HOVER},
                                        style={"boxShadow": T.SHADOW_PRIMARY},
                                        font_family=T.FONT_MONO, font_size="14px",
                                        font_weight="500",
                                    ),
                                    rx.box(
                                        rx.hstack(
                                            rx.text(OnboardingState.chunk_count,
                                                    font_family=T.FONT_MONO, font_size="20px",
                                                    font_weight="700", color=T.PRIMARY),
                                            rx.text("chunks indexed",
                                                    font_family=T.FONT_BODY, font_size="13px",
                                                    color=T.MUTED_FG),
                                            spacing="2", align="baseline",
                                        ),
                                        padding="10px 18px",
                                        background_color=f"{T.PRIMARY}0F",
                                        border=f"1px solid {T.PRIMARY}30",
                                        border_radius=T.RADIUS_S,
                                    ),
                                    spacing="3", align="center", wrap="wrap",
                                ),
                            ),
                            rx.cond(
                                OnboardingState.ingest_done,
                                rx.box(
                                    rx.hstack(
                                        rx.text("✅"),
                                        rx.text(OnboardingState.chunk_count),
                                        rx.text("chunks embedded — AI Chat is ready!",
                                                font_family=T.FONT_BODY, font_size="14px",
                                                color="#004D1A", font_weight="500"),
                                        spacing="1",
                                    ),
                                    padding="12px 16px",
                                    background_color="#DFE6E1",
                                    border_radius=T.RADIUS_S,
                                    border=f"1px solid #A0C4A0",
                                ),
                            ),
                            rx.cond(
                                OnboardingState.ingest_error != "",
                                rx.box(
                                    rx.hstack(
                                        rx.text("⚠️"),
                                        rx.text(OnboardingState.ingest_error,
                                                font_family=T.FONT_BODY, font_size="13px",
                                                color=T.ERROR_FG),
                                        spacing="2",
                                    ),
                                    padding="12px 16px",
                                    background_color=T.ERROR_BG,
                                    border_radius=T.RADIUS_S,
                                    border=f"1px solid #D4A0A0",
                                ),
                            ),
                            rx.button(
                                "Skip →", variant="outline", size="2",
                                font_family=T.FONT_BODY,
                                border_radius=T.RADIUS_PILL,
                                border=f"1px solid {T.BORDER}",
                                color=T.MUTED_FG,
                                on_click=OnboardingState.go_to_step(2),
                                cursor="pointer",
                            ),
                            spacing="4", width="100%", align="start",
                        ),
                        padding="28px",
                        background_color=T.CARD,
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_M,
                        width="100%",
                        style={"boxShadow": T.SHADOW_SM},
                    ),
                ),

                # ── STEP 2: Ask a Question ──────────────────────────
                rx.cond(
                    OnboardingState.step == 2,
                    rx.box(
                        rx.vstack(
                            rx.text("Step 3 — Ask Your First Question",
                                    font_family=T.FONT_MONO, font_size="18px",
                                    font_weight="600", color=T.FG),
                            rx.hstack(
                                rx.text("🎉", font_size="24px"),
                                rx.vstack(
                                    rx.text("You're all set!",
                                            font_family=T.FONT_BODY, font_size="15px",
                                            font_weight="600", color=T.FG),
                                    rx.hstack(
                                        rx.text(OnboardingState.chunk_count,
                                                font_family=T.FONT_MONO, font_weight="700",
                                                color=T.PRIMARY),
                                        rx.text("chunks indexed and ready.",
                                                font_family=T.FONT_BODY, color=T.MUTED_FG,
                                                font_size="14px"),
                                        spacing="1", align="baseline",
                                    ),
                                    spacing="1", align="start",
                                ),
                                spacing="3", align="center",
                            ),
                            rx.text("Try these questions:", font_family=T.FONT_BODY,
                                    font_size="13px", font_weight="600", color=T.FG),
                            rx.vstack(
                                *[rx.box(
                                    rx.hstack(
                                        rx.text("→", color=T.PRIMARY, font_weight="600",
                                                font_family=T.FONT_MONO, font_size="13px"),
                                        rx.text(q, font_family=T.FONT_BODY, font_size="13px",
                                                color=T.FG),
                                        spacing="2", align="center",
                                    ),
                                    padding="10px 14px",
                                    background_color=T.BACKGROUND,
                                    border=f"1px solid {T.BORDER}",
                                    border_radius=T.RADIUS_S,
                                    width="100%",
                                ) for q in [
                                    "Which subjects had severe adverse events?",
                                    "What were the abnormal lab results at Week 12?",
                                    "How many subjects are enrolled at the London site?",
                                    "What is the protocol objective of CARDIO-2024?",
                                    "List all subjects who have completed the trial.",
                                ]],
                                spacing="2", width="100%",
                            ),
                            rx.link(
                                rx.button(
                                    "🤖  Go to AI Chat →",
                                    height="44px", padding="0 24px",
                                    border_radius=T.RADIUS_PILL,
                                    background_color=T.PRIMARY,
                                    color=T.PRIMARY_FG,
                                    cursor="pointer",
                                    _hover={"background_color": T.PRIMARY_HOVER},
                                    style={"boxShadow": T.SHADOW_PRIMARY},
                                    font_family=T.FONT_MONO, font_size="14px",
                                    font_weight="500",
                                ),
                                href="/chat",
                            ),
                            rx.text(
                                "You can always return here from the sidebar to reseed or re-ingest.",
                                font_family=T.FONT_BODY, font_size="12px", color=T.MUTED_FG,
                            ),
                            spacing="4", width="100%", align="start",
                        ),
                        padding="28px",
                        background_color=T.CARD,
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_M,
                        width="100%",
                        style={"boxShadow": T.SHADOW_SM},
                    ),
                ),

                spacing="5", width="100%",
            ),
            padding="28px 32px",
            width="100%",
        ),

        width="100%",
        min_height="100vh",
        background_color=T.BACKGROUND,
    ))
