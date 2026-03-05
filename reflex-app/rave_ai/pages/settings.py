"""
Settings Page — Lunaris design system
"""
import reflex as rx
from rave_ai.layout import page_layout
from rave_ai.state import SettingsState, AppState
from rave_ai import theme as T


def _section_card(*children) -> rx.Component:
    return rx.box(
        *children,
        padding="24px 28px",
        background_color=T.CARD,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS_M,
        width="100%",
        style={"boxShadow": T.SHADOW_SM},
    )


def _row_label(label: str, value) -> rx.Component:
    return rx.hstack(
        rx.text(label, font_family=T.FONT_BODY, font_size="13px",
                font_weight="600", color=T.FG, min_width="160px"),
        rx.text(value, font_family=T.FONT_MONO, font_size="13px",
                color=T.MUTED_FG),
        width="100%", align="center",
    )


def settings_page() -> rx.Component:
    return page_layout(rx.box(

        # Page header
        rx.box(
            rx.vstack(
                rx.text("Settings", font_family=T.FONT_MONO,
                        font_size="24px", font_weight="700", color=T.FG),
                rx.text("Manage your account and preferences",
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

                # Account section
                rx.vstack(
                    rx.text("Account", font_family=T.FONT_MONO,
                            font_size="11px", font_weight="600",
                            color=T.MUTED_FG, letter_spacing="0.08em"),
                    _section_card(
                        rx.vstack(
                            _row_label("Email", AppState.user_email),
                            rx.box(height="1px", background_color=T.BORDER, width="100%"),
                            rx.button(
                                rx.hstack(
                                    rx.text("🚪", font_size="14px"),
                                    rx.text("Sign Out", font_family=T.FONT_MONO,
                                            font_size="13px", font_weight="500"),
                                    spacing="2",
                                ),
                                on_click=AppState.logout,
                                height="36px", padding="0 18px",
                                border_radius=T.RADIUS_PILL,
                                background_color=T.ERROR,
                                color="#FFFFFF",
                                cursor="pointer",
                                _hover={"background_color": "#DC2626"},
                            ),
                            spacing="4", width="100%", align="start",
                        ),
                    ),
                    spacing="2", width="100%", align="start",
                ),

                # Preferences section
                rx.vstack(
                    rx.text("Preferences", font_family=T.FONT_MONO,
                            font_size="11px", font_weight="600",
                            color=T.MUTED_FG, letter_spacing="0.08em"),
                    _section_card(
                        rx.vstack(
                            # Theme
                            rx.vstack(
                                rx.hstack(
                                    rx.text("Theme", font_family=T.FONT_BODY,
                                            font_size="13px", font_weight="600", color=T.FG),
                                    rx.text("— changes apply immediately across all pages",
                                            font_family=T.FONT_BODY, font_size="12px",
                                            color=T.MUTED_FG),
                                    spacing="2", align="center",
                                ),
                                rx.hstack(
                                    # Light mode button
                                    rx.box(
                                        rx.vstack(
                                            rx.text("☀️", font_size="22px"),
                                            rx.text("Light", font_family=T.FONT_MONO,
                                                    font_size="12px", font_weight="600",
                                                    color=rx.cond(
                                                        SettingsState.theme == "light",
                                                        T.PRIMARY, T.FG
                                                    )),
                                            spacing="1", align="center",
                                        ),
                                        padding="16px 24px",
                                        border_radius=T.RADIUS_M,
                                        border=rx.cond(
                                            SettingsState.theme == "light",
                                            f"2px solid {T.PRIMARY}",
                                            f"1px solid {T.BORDER}",
                                        ),
                                        background_color=rx.cond(
                                            SettingsState.theme == "light",
                                            f"{T.PRIMARY}10",
                                            T.BACKGROUND,
                                        ),
                                        cursor="pointer",
                                        on_click=SettingsState.set_theme("light"),
                                        _hover={"border_color": T.PRIMARY},
                                        transition="all 0.15s ease",
                                        text_align="center",
                                    ),
                                    # Dark mode button
                                    rx.box(
                                        rx.vstack(
                                            rx.text("🌙", font_size="22px"),
                                            rx.text("Dark", font_family=T.FONT_MONO,
                                                    font_size="12px", font_weight="600",
                                                    color=rx.cond(
                                                        SettingsState.theme == "dark",
                                                        T.PRIMARY, T.FG
                                                    )),
                                            spacing="1", align="center",
                                        ),
                                        padding="16px 24px",
                                        border_radius=T.RADIUS_M,
                                        border=rx.cond(
                                            SettingsState.theme == "dark",
                                            f"2px solid {T.PRIMARY}",
                                            f"1px solid {T.BORDER}",
                                        ),
                                        background_color=rx.cond(
                                            SettingsState.theme == "dark",
                                            f"{T.PRIMARY}10",
                                            T.BACKGROUND,
                                        ),
                                        cursor="pointer",
                                        on_click=SettingsState.set_theme("dark"),
                                        _hover={"border_color": T.PRIMARY},
                                        transition="all 0.15s ease",
                                        text_align="center",
                                    ),
                                    spacing="3",
                                ),
                                spacing="3", align="start",
                            ),

                            rx.box(height="1px", background_color=T.BORDER, width="100%"),

                            # Auto-scale
                            rx.hstack(
                                rx.vstack(
                                    rx.text("Auto-scale Ollama", font_family=T.FONT_BODY,
                                            font_size="13px", font_weight="600", color=T.FG),
                                    rx.text(
                                        "Automatically adjust LLM threads based on system load",
                                        font_family=T.FONT_BODY, font_size="12px",
                                        color=T.MUTED_FG,
                                    ),
                                    spacing="1", align="start",
                                ),
                                rx.spacer(),
                                rx.checkbox(
                                    checked=SettingsState.auto_scale_enabled,
                                    on_change=SettingsState.toggle_auto_scale,
                                ),
                                width="100%", align="center",
                            ),

                            spacing="4", width="100%",
                        ),
                    ),
                    spacing="2", width="100%", align="start",
                ),

                # System info section
                rx.vstack(
                    rx.text("System Information", font_family=T.FONT_MONO,
                            font_size="11px", font_weight="600",
                            color=T.MUTED_FG, letter_spacing="0.08em"),
                    _section_card(
                        rx.vstack(
                            _row_label("RAVE AI Version", "1.0.0"),
                            rx.box(height="1px", background_color=T.BORDER, width="100%"),
                            _row_label("Frontend", "Reflex 0.8.27"),
                            rx.box(height="1px", background_color=T.BORDER, width="100%"),
                            rx.hstack(
                                rx.text("Build", font_family=T.FONT_BODY, font_size="13px",
                                        font_weight="600", color=T.FG, min_width="160px"),
                                rx.box(
                                    rx.text("Production", font_family=T.FONT_MONO,
                                            font_size="12px", color="#004D1A", font_weight="500"),
                                    padding="3px 10px",
                                    background_color="#DFE6E1",
                                    border_radius=T.RADIUS_PILL,
                                    border="1px solid #A0C4A0",
                                ),
                                width="100%", align="center",
                            ),
                            spacing="4", width="100%",
                        ),
                    ),
                    spacing="2", width="100%", align="start",
                ),

                # Info note
                rx.box(
                    rx.hstack(
                        rx.text("ℹ️", font_size="14px"),
                        rx.text(
                            "Enable Auto-scale to improve system performance during peak usage. "
                            "The system will automatically adjust CPU thread allocation based on load.",
                            font_family=T.FONT_BODY, font_size="13px", color=T.FG,
                        ),
                        spacing="2", align="start",
                    ),
                    padding="14px 18px",
                    background_color=T.INFO_BG,
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_S,
                    width="100%",
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
