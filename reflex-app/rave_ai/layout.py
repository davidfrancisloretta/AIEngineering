"""
Shared page layout — Lunaris design system
Navbar + Sidebar wrapper imported by each page.
"""
import reflex as rx
from rave_ai.state import AppState
from rave_ai import theme as T


# ── Sidebar nav item helpers ───────────────────────────────────────────────

def _nav_section_title(label: str) -> rx.Component:
    return rx.text(
        label.upper(),
        font_family=T.FONT_MONO,
        font_size="10px",
        font_weight="600",
        color=T.MUTED_FG,
        letter_spacing="0.08em",
        padding="16px 16px 4px 16px",
    )


def _nav_item(icon: str, label: str, href: str) -> rx.Component:
    return rx.link(
        rx.hstack(
            rx.text(icon, font_size="15px"),
            rx.text(label, font_family=T.FONT_BODY, font_size="14px", color=T.FG),
            spacing="3", align="center",
        ),
        href=href,
        padding="9px 16px",
        border_radius=T.RADIUS_S,
        display="block",
        width="100%",
        text_decoration="none",
        _hover={
            "background_color": T.SIDEBAR_ACCENT,
            "text_decoration": "none",
        },
        transition="background-color 0.15s ease",
    )


# ── Navbar ─────────────────────────────────────────────────────────────────

def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Brand
            rx.hstack(
                rx.box(
                    rx.text("🧬", font_size="16px"),
                    width="32px", height="32px",
                    border_radius=T.RADIUS_S,
                    background_color=T.PRIMARY,
                    display="flex", align_items="center", justify_content="center",
                ),
                rx.text(
                    "RAVE AI",
                    font_family=T.FONT_MONO,
                    font_size="16px",
                    font_weight="700",
                    color=T.FG,
                ),
                spacing="2", align="center",
            ),
            rx.spacer(),
            # User menu
            rx.dropdown_menu.root(
                rx.dropdown_menu.trigger(
                    rx.hstack(
                        rx.box(
                            rx.text(
                                AppState.user_email[:1].upper(),
                                font_family=T.FONT_MONO,
                                font_size="13px",
                                font_weight="600",
                                color=T.PRIMARY_FG,
                            ),
                            width="32px", height="32px",
                            border_radius=T.RADIUS_PILL,
                            background_color=T.PRIMARY,
                            display="flex", align_items="center", justify_content="center",
                        ),
                        rx.text(AppState.user_email, font_family=T.FONT_BODY,
                                font_size="13px", color=T.FG),
                        rx.text("▾", font_size="11px", color=T.MUTED_FG),
                        spacing="2", align="center", cursor="pointer",
                    ),
                ),
                rx.dropdown_menu.content(
                    rx.dropdown_menu.item(
                        rx.link("⚙️  Settings", href="/settings",
                                text_decoration="none", color=T.FG,
                                font_family=T.FONT_BODY, font_size="13px"),
                    ),
                    rx.dropdown_menu.separator(),
                    rx.dropdown_menu.item(
                        "🚪  Logout",
                        on_click=AppState.logout,
                        color=T.ERROR,
                        font_family=T.FONT_BODY,
                        font_size="13px",
                        cursor="pointer",
                    ),
                ),
            ),
            width="100%", align="center", padding="0 20px",
        ),
        height="60px",
        background_color=T.CARD,
        border_bottom=f"1px solid {T.BORDER}",
        display="flex",
        align_items="center",
        width="100%",
        style={"boxShadow": T.SHADOW_SM},
        position="sticky",
        top="0",
        z_index="100",
    )


# ── Sidebar ────────────────────────────────────────────────────────────────

def sidebar_nav() -> rx.Component:
    return rx.box(
        rx.vstack(

            # top spacer to align first section title
            rx.box(height="8px"),

            # Analytics section
            _nav_section_title("Analytics"),
            _nav_item("📊", "Dashboard", "/dashboard"),
            _nav_item("🤖", "AI Chat", "/chat"),
            _nav_item("📈", "AI Analytics", "/analytics"),

            rx.box(height="1px", width="calc(100% - 32px)", background_color=T.BORDER,
                   margin="8px 16px"),

            # Clinical Trials section
            _nav_section_title("Clinical Trials"),
            _nav_item("🏥", "Trial Data", "/trials"),
            _nav_item("📥", "Fetch Data", "/fetch-data"),

            rx.box(height="1px", width="calc(100% - 32px)", background_color=T.BORDER,
                   margin="8px 16px"),

            # Account section
            _nav_section_title("Account"),
            _nav_item("⚙️", "Settings", "/settings"),

            rx.spacer(),

            # Bottom user card
            rx.box(
                rx.hstack(
                    rx.box(
                        rx.text(AppState.user_email[:1].upper(),
                                font_family=T.FONT_MONO, font_size="12px",
                                font_weight="600", color=T.PRIMARY_FG),
                        width="28px", height="28px",
                        border_radius=T.RADIUS_PILL,
                        background_color=T.PRIMARY,
                        display="flex", align_items="center", justify_content="center",
                        flex_shrink="0",
                    ),
                    rx.vstack(
                        rx.text(AppState.user_email, font_family=T.FONT_BODY,
                                font_size="12px", color=T.FG,
                                overflow="hidden", text_overflow="ellipsis",
                                white_space="nowrap", max_width="140px"),
                        rx.text("Signed in", font_family=T.FONT_BODY,
                                font_size="11px", color=T.MUTED_FG),
                        spacing="0", align="start",
                    ),
                    spacing="2", align="center",
                ),
                padding="12px 16px",
                margin="8px",
                background_color=T.SIDEBAR_ACCENT,
                border_radius=T.RADIUS_S,
                border=f"1px solid {T.BORDER}",
            ),

            spacing="0",
            width="100%",
            height="100%",
            align_items="start",
        ),
        width="240px",
        min_height="calc(100vh - 60px)",
        background_color=T.SIDEBAR_BG,
        border_right=f"1px solid {T.BORDER}",
        overflow_y="auto",
        flex_shrink="0",
    )


# ── Page wrapper ───────────────────────────────────────────────────────────

def page_layout(content: rx.Component) -> rx.Component:
    """Wraps content with Lunaris navbar + sidebar. Redirects if unauthenticated."""
    return rx.cond(
        AppState.is_authenticated,
        rx.vstack(
            navbar(),
            rx.hstack(
                sidebar_nav(),
                rx.box(
                    content,
                    width="100%",
                    overflow_y="auto",
                    background_color=T.BACKGROUND,
                ),
                spacing="0",
                width="100%",
                height="calc(100vh - 60px)",
                overflow="hidden",
            ),
            spacing="0",
            width="100%",
            height="100vh",
            overflow="hidden",
        ),
        rx.center(
            rx.vstack(
                rx.box(
                    rx.text("🧬", font_size="24px"),
                    width="52px", height="52px",
                    border_radius=T.RADIUS_M,
                    background_color=T.PRIMARY,
                    display="flex", align_items="center", justify_content="center",
                ),
                rx.spinner(size="3", color=T.PRIMARY),
                spacing="4", align="center",
            ),
            min_height="100vh",
            background_color=T.BACKGROUND,
        ),
    )
