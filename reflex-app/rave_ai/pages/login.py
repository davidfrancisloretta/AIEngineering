"""
Login Page — Lunaris design system
"""
import reflex as rx
from rave_ai.state import LoginState
from rave_ai import theme as T


def login_page() -> rx.Component:
    return rx.box(
        # Full-page split: left brand panel + right form
        rx.hstack(

            # ── Left brand panel ─────────────────────────────────────
            rx.box(
                rx.vstack(
                    # Logo mark
                    rx.box(
                        rx.text("🧬", font_size="48px"),
                        width="80px", height="80px",
                        border_radius=T.RADIUS_M,
                        background_color=T.PRIMARY,
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        style={"boxShadow": T.SHADOW_PRIMARY},
                    ),
                    rx.text(
                        "RAVE AI",
                        font_family=T.FONT_MONO,
                        font_size="36px",
                        font_weight="700",
                        color=T.CARD,
                        letter_spacing="-0.5px",
                    ),
                    rx.text(
                        "Clinical Trial RAG\nAnalytics Platform",
                        font_family=T.FONT_BODY,
                        font_size="16px",
                        color=f"{T.CARD}AA",
                        text_align="center",
                        line_height="1.6",
                        white_space="pre-line",
                    ),
                    rx.box(
                        rx.hstack(
                            rx.box(width="6px", height="6px", border_radius="50%",
                                   background_color=T.CARD),
                            rx.text("RAG-powered Q&A", font_family=T.FONT_BODY,
                                    font_size="13px", color=f"{T.CARD}CC"),
                            spacing="2", align="center",
                        ),
                        rx.hstack(
                            rx.box(width="6px", height="6px", border_radius="50%",
                                   background_color=T.CARD),
                            rx.text("Hybrid semantic + SQL search", font_family=T.FONT_BODY,
                                    font_size="13px", color=f"{T.CARD}CC"),
                            spacing="2", align="center",
                        ),
                        rx.hstack(
                            rx.box(width="6px", height="6px", border_radius="50%",
                                   background_color=T.CARD),
                            rx.text("Opik observability & feedback", font_family=T.FONT_BODY,
                                    font_size="13px", color=f"{T.CARD}CC"),
                            spacing="2", align="center",
                        ),
                        display="flex",
                        flex_direction="column",
                        gap="10px",
                        margin_top="1rem",
                    ),
                    spacing="4",
                    align="center",
                    justify_content="center",
                    height="100%",
                ),
                width="45%",
                height="100vh",
                background_color=T.PRIMARY,
                display="flex",
                align_items="center",
                justify_content="center",
                padding="40px",
            ),

            # ── Right form panel ─────────────────────────────────────
            rx.box(
                rx.vstack(
                    # Greeting
                    rx.vstack(
                        rx.text(
                            "Welcome back",
                            font_family=T.FONT_MONO,
                            font_size="28px",
                            font_weight="700",
                            color=T.FG,
                        ),
                        rx.text(
                            "Sign in to your account to continue",
                            font_family=T.FONT_BODY,
                            font_size="14px",
                            color=T.MUTED_FG,
                        ),
                        spacing="1", align="start",
                    ),

                    # Form card
                    rx.box(
                        rx.vstack(
                            # Email field
                            rx.vstack(
                                rx.text("Email", font_family=T.FONT_BODY, font_size="13px",
                                        font_weight="500", color=T.FG),
                                rx.input(
                                    placeholder="user@example.com",
                                    value=LoginState.email,
                                    on_change=LoginState.set_email,
                                    type="email",
                                    width="100%",
                                    height="44px",
                                    border_radius=T.RADIUS_PILL,
                                    border=f"1px solid {T.BORDER}",
                                    background_color=T.BACKGROUND,
                                    font_family=T.FONT_BODY,
                                    font_size="14px",
                                    padding="0 18px",
                                    _focus={"border_color": T.PRIMARY, "outline": "none",
                                            "box_shadow": f"0 0 0 3px {T.PRIMARY}22"},
                                    _placeholder={"color": T.MUTED_FG},
                                ),
                                spacing="1", width="100%",
                            ),

                            # Password field with eye toggle
                            rx.vstack(
                                rx.text("Password", font_family=T.FONT_BODY, font_size="13px",
                                        font_weight="500", color=T.FG),
                                rx.box(
                                    rx.input(
                                        placeholder="••••••••",
                                        value=LoginState.password,
                                        on_change=LoginState.set_password,
                                        type=rx.cond(LoginState.show_password, "text", "password"),
                                        width="100%",
                                        height="44px",
                                        border_radius=T.RADIUS_PILL,
                                        border=f"1px solid {T.BORDER}",
                                        background_color=T.BACKGROUND,
                                        font_family=T.FONT_BODY,
                                        font_size="14px",
                                        padding="0 50px 0 18px",
                                        _focus={"border_color": T.PRIMARY, "outline": "none",
                                                "box_shadow": f"0 0 0 3px {T.PRIMARY}22"},
                                        _placeholder={"color": T.MUTED_FG},
                                    ),
                                    rx.box(
                                        rx.cond(
                                            LoginState.show_password,
                                            rx.text("🙈", font_size="16px"),
                                            rx.text("👁", font_size="16px"),
                                        ),
                                        position="absolute",
                                        right="14px",
                                        top="50%",
                                        transform="translateY(-50%)",
                                        cursor="pointer",
                                        on_click=LoginState.toggle_show_password,
                                        user_select="none",
                                    ),
                                    position="relative",
                                    width="100%",
                                ),
                                spacing="1", width="100%",
                            ),

                            # Error
                            rx.cond(
                                LoginState.login_error != "",
                                rx.box(
                                    rx.hstack(
                                        rx.text("⚠️", font_size="14px"),
                                        rx.text(LoginState.login_error,
                                                font_family=T.FONT_BODY, font_size="13px",
                                                color=T.ERROR_FG),
                                        spacing="2", align="center",
                                    ),
                                    padding="10px 14px",
                                    background_color=T.ERROR_BG,
                                    border_radius=T.RADIUS_S,
                                    border=f"1px solid #D4A0A0",
                                    width="100%",
                                ),
                            ),

                            # Login button
                            rx.button(
                                rx.cond(
                                    LoginState.is_loading,
                                    rx.hstack(
                                        rx.spinner(size="2"),
                                        rx.text("Signing in…", font_family=T.FONT_MONO,
                                                font_size="14px", font_weight="500"),
                                        spacing="2",
                                    ),
                                    rx.text("Sign In →", font_family=T.FONT_MONO,
                                            font_size="14px", font_weight="500"),
                                ),
                                on_click=LoginState.handle_login,
                                disabled=LoginState.is_loading,
                                width="100%",
                                height="44px",
                                border_radius=T.RADIUS_PILL,
                                background_color=T.PRIMARY,
                                color=T.PRIMARY_FG,
                                cursor="pointer",
                                _hover={"background_color": T.PRIMARY_HOVER},
                                style={"boxShadow": T.SHADOW_PRIMARY},
                            ),

                            spacing="4", width="100%",
                        ),
                        padding="28px",
                        background_color=T.CARD,
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_M,
                        width="100%",
                        style={"boxShadow": T.SHADOW_SM},
                    ),

                    # Demo credentials
                    rx.box(
                        rx.vstack(
                            rx.text("Demo credentials", font_family=T.FONT_MONO,
                                    font_size="12px", font_weight="600", color=T.FG),
                            rx.hstack(
                                rx.text("demo@example.com", font_family=T.FONT_MONO,
                                        font_size="12px", color=T.MUTED_FG),
                                rx.text("·", color=T.BORDER),
                                rx.text("demo123", font_family=T.FONT_MONO,
                                        font_size="12px", color=T.MUTED_FG),
                                spacing="2", align="center",
                            ),
                            spacing="1", align="start",
                        ),
                        padding="12px 16px",
                        background_color=T.MUTED_BG,
                        border_radius=T.RADIUS_S,
                        border=f"1px solid {T.BORDER}",
                        width="100%",
                    ),

                    # Footer
                    rx.text(
                        "© 2026 RAVE AI. All rights reserved.",
                        font_family=T.FONT_BODY,
                        font_size="12px",
                        color=T.MUTED_FG,
                        text_align="center",
                    ),

                    spacing="5", width="100%", max_width="400px", align="start",
                ),
                width="55%",
                height="100vh",
                background_color=T.BACKGROUND,
                display="flex",
                align_items="center",
                justify_content="center",
                padding="60px 40px",
            ),

            spacing="0", width="100%",
        ),
        width="100%",
        overflow="hidden",
    )
