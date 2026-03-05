"""
Signed Out Page — Lunaris design system
Shown after the user logs out.
"""
import reflex as rx
from rave_ai import theme as T


def signed_out_page() -> rx.Component:
    return rx.box(
        rx.center(
            rx.vstack(

                # Brand mark
                rx.box(
                    rx.text("🧬", font_size="32px"),
                    width="64px", height="64px",
                    border_radius=T.RADIUS_M,
                    background_color=T.PRIMARY,
                    display="flex", align_items="center", justify_content="center",
                    style={"boxShadow": T.SHADOW_PRIMARY},
                ),

                # Status icon
                rx.box(
                    rx.text("✓", font_size="22px", font_weight="700",
                            color="#004D1A"),
                    width="48px", height="48px",
                    border_radius=T.RADIUS_PILL,
                    background_color="#DFE6E1",
                    border="1px solid #A0C4A0",
                    display="flex", align_items="center", justify_content="center",
                ),

                # Title
                rx.text(
                    "You've been signed out",
                    font_family=T.FONT_MONO,
                    font_size="22px",
                    font_weight="700",
                    color=T.FG,
                    text_align="center",
                ),

                # Subtitle
                rx.text(
                    "Your session has ended securely. Thank you for using RAVE AI.",
                    font_family=T.FONT_BODY,
                    font_size="14px",
                    color=T.MUTED_FG,
                    text_align="center",
                    max_width="320px",
                    line_height="1.6",
                ),

                # Sign back in button
                rx.link(
                    rx.box(
                        rx.text("Sign In Again →",
                                font_family=T.FONT_MONO, font_size="14px",
                                font_weight="500", color=T.PRIMARY_FG),
                        height="44px",
                        padding="0 28px",
                        border_radius=T.RADIUS_PILL,
                        background_color=T.PRIMARY,
                        display="flex", align_items="center", justify_content="center",
                        cursor="pointer",
                        _hover={"background_color": T.PRIMARY_HOVER},
                        style={"boxShadow": T.SHADOW_PRIMARY},
                    ),
                    href="/login",
                    text_decoration="none",
                ),

                # Footer
                rx.text(
                    "RAVE AI  ·  Clinical Trial RAG Analytics Platform",
                    font_family=T.FONT_MONO,
                    font_size="11px",
                    color=T.MUTED_FG,
                    letter_spacing="0.04em",
                ),

                spacing="5",
                align="center",
                max_width="420px",
            ),
            min_height="100vh",
            background_color=T.BACKGROUND,
        ),
        width="100%",
    )
