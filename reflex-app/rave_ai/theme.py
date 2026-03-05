"""
Lunaris Design System Tokens — shared across all RAVE AI pages.
Primary: #FF8400 (orange)  |  Fonts: JetBrains Mono + Geist
"""

# ── Colors ──────────────────────────────────────────────────────────────────
PRIMARY        = "#FF8400"
PRIMARY_FG     = "#111111"
PRIMARY_HOVER  = "#e67600"
PRIMARY_GLOW   = "#FF840044"

BACKGROUND     = "#F2F3F0"
CARD           = "#FFFFFF"
BORDER         = "#CBCCC9"

FG             = "#111111"
MUTED_FG       = "#666666"
MUTED_BG       = "#E7E8E5"

SUCCESS        = "#22C55E"
ERROR          = "#EF4444"
ERROR_BG       = "#E5DCDA"
ERROR_FG       = "#8C1C00"
INFO_BG        = "#DFDFE6"
INFO_FG        = "#000066"
WARNING_BG     = "#E9E3D8"
WARNING_FG     = "#804200"

SIDEBAR_BG     = "#E7E8E5"
SIDEBAR_ACCENT = "#CBCCC9"
SIDEBAR_ACTIVE = "#111111"

# ── Typography ───────────────────────────────────────────────────────────────
FONT_MONO      = "JetBrains Mono, monospace"
FONT_BODY      = "Geist, Inter, sans-serif"

# ── Radii ────────────────────────────────────────────────────────────────────
RADIUS_PILL    = "999px"
RADIUS_M       = "16px"
RADIUS_S       = "8px"

# ── Shadows ──────────────────────────────────────────────────────────────────
SHADOW_SM      = "0 1px 3px rgba(0,0,0,0.06)"
SHADOW_MD      = "0 2px 8px rgba(0,0,0,0.10)"
SHADOW_PRIMARY = f"0 2px 8px {PRIMARY}44"

# ── Common Style Helpers ─────────────────────────────────────────────────────

def card_style(**extra) -> dict:
    """White card with border and soft shadow."""
    return {
        "background_color": CARD,
        "border": f"1px solid {BORDER}",
        "border_radius": RADIUS_M,
        "style": {"boxShadow": SHADOW_SM},
        **extra,
    }


def pill_input_style(**extra) -> dict:
    """Pill-shaped input field."""
    return {
        "border_radius": RADIUS_PILL,
        "border": f"1px solid {BORDER}",
        "background_color": BACKGROUND,
        "font_family": FONT_BODY,
        "font_size": "14px",
        "height": "44px",
        "_focus": {
            "border_color": PRIMARY,
            "outline": "none",
            "box_shadow": f"0 0 0 3px {PRIMARY}22",
        },
        "_placeholder": {"color": MUTED_FG},
        **extra,
    }


def primary_btn_style(**extra) -> dict:
    """Orange pill primary button."""
    return {
        "background_color": PRIMARY,
        "color": PRIMARY_FG,
        "border_radius": RADIUS_PILL,
        "font_family": FONT_MONO,
        "font_weight": "500",
        "cursor": "pointer",
        "_hover": {"background_color": PRIMARY_HOVER},
        "style": {"boxShadow": SHADOW_PRIMARY},
        **extra,
    }


def outline_btn_style(**extra) -> dict:
    """Pill outline button."""
    return {
        "variant": "outline",
        "border_radius": RADIUS_PILL,
        "border": f"1px solid {BORDER}",
        "color": FG,
        "background_color": CARD,
        "font_family": FONT_BODY,
        "cursor": "pointer",
        "_hover": {"border_color": PRIMARY, "color": PRIMARY},
        **extra,
    }


def section_heading(text: str, size: str = "5") -> object:
    """Page section heading in monospace."""
    import reflex as rx
    return rx.heading(
        text,
        size=size,
        font_family=FONT_MONO,
        color=FG,
        font_weight="600",
    )


def muted_text(text, size: str = "2") -> object:
    """Muted body text."""
    import reflex as rx
    return rx.text(text, size=size, color=MUTED_FG, font_family=FONT_BODY)
