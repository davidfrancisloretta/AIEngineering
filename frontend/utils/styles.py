"""
RAVE AI Design System — shared CSS module.

Usage in any page:
    from utils.styles import apply_rave_theme
    apply_rave_theme()

Design tokens:
  Primary:   #FF8400  (Vibrant Orange)
  BG:        #0D1117  (GitHub Dark)
  Card BG:   #161B22
  Elevated:  #1C2333
  Border:    rgba(255,255,255,0.08)
  Success:   #3FB950
  Warning:   #D29922
  Error:     #F85149
  Info:      #388BFD
  Fonts:     JetBrains Mono (headings) / Geist (body)
  Radius:    16px (cards), 999px (pills/buttons), 10px (inputs)
"""
import streamlit as st

_CSS = """
<style>
/* ── Google Fonts ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600&display=swap');

/* ── Design tokens ─────────────────────────────────────────────────────────── */
:root {
    --primary:        #FF8400;
    --primary-dim:    rgba(255, 132, 0, 0.12);
    --primary-glow:   rgba(255, 132, 0, 0.30);
    --primary-border: rgba(255, 132, 0, 0.35);
    --bg:             #0D1117;
    --bg-card:        #161B22;
    --bg-elevated:    #1C2333;
    --border:         rgba(255, 255, 255, 0.08);
    --text:           #E6EDF3;
    --text-muted:     #8B949E;
    --text-dim:       #484F58;
    --success:        #3FB950;
    --warning:        #D29922;
    --error:          #F85149;
    --info:           #388BFD;
    --r-card:         16px;
    --r-pill:         999px;
    --r-input:        10px;
}

/* ── Typography ────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Geist', system-ui, -apple-system, sans-serif !important;
}
h1, h2, h3, h4 {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: var(--text) !important;
}
h1 { font-size: 28px !important; line-height: 1.2 !important; }
h2 { font-size: 22px !important; }
h3 { font-size: 18px !important; }

/* ── Layout ────────────────────────────────────────────────────────────────── */
.main .block-container {
    padding: 32px 40px 48px 40px !important;
    max-width: 1400px !important;
}

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0A0E14 !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebarNav"] a {
    border-radius: 10px !important;
    margin: 2px 8px !important;
    padding: 8px 14px !important;
    font-family: 'Geist', sans-serif !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    color: var(--text-muted) !important;
    transition: all 0.15s ease !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: var(--primary-dim) !important;
    color: var(--primary) !important;
}
[data-testid="stSidebarNav"] a[aria-selected="true"],
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: var(--primary-dim) !important;
    border-left: 3px solid var(--primary) !important;
    color: var(--primary) !important;
    font-weight: 500 !important;
}
[data-testid="stSidebarNavSeparatorHeader"] {
    font-family: 'Geist', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.10em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
    padding: 12px 20px 4px 20px !important;
}

/* ── Buttons ───────────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: var(--r-pill) !important;
    font-family: 'Geist', sans-serif !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 8px 22px !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-elevated) !important;
    color: var(--text) !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover {
    border-color: var(--primary) !important;
    background: var(--primary-dim) !important;
    color: var(--primary) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"] {
    background: var(--primary) !important;
    border-color: var(--primary) !important;
    color: #0D1117 !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #FF9A20 !important;
    box-shadow: 0 4px 20px var(--primary-glow) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    border-color: var(--border) !important;
}

/* ── Form submit buttons ───────────────────────────────────────────────────── */
.stFormSubmitButton > button {
    border-radius: var(--r-pill) !important;
    font-family: 'Geist', sans-serif !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    background: var(--primary) !important;
    border-color: var(--primary) !important;
    color: #0D1117 !important;
    transition: all 0.15s ease !important;
}
.stFormSubmitButton > button:hover {
    background: #FF9A20 !important;
    box-shadow: 0 4px 20px var(--primary-glow) !important;
}

/* ── Inputs ────────────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-input) !important;
    color: var(--text) !important;
    font-family: 'Geist', sans-serif !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-dim) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label {
    font-family: 'Geist', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
    margin-bottom: 4px !important;
}

/* ── Chat input ────────────────────────────────────────────────────────────── */
[data-testid="stChatInput"] textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-pill) !important;
    color: var(--text) !important;
    font-family: 'Geist', sans-serif !important;
    font-size: 14px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-dim) !important;
}
[data-testid="stChatInput"] button {
    background: var(--primary) !important;
    border-radius: var(--r-pill) !important;
}

/* ── Metric cards ──────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-card) !important;
    padding: 20px 24px !important;
    transition: border-color 0.15s ease !important;
}
[data-testid="stMetric"]:hover {
    border-color: var(--primary-border) !important;
}
[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    color: var(--primary) !important;
    font-size: 26px !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Geist', sans-serif !important;
    color: var(--text-muted) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'Geist', sans-serif !important;
    font-size: 13px !important;
}

/* ── Expanders / Accordions ────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-card) !important;
    overflow: hidden !important;
    margin-bottom: 8px !important;
    transition: border-color 0.15s ease !important;
}
[data-testid="stExpander"]:hover {
    border-color: var(--primary-border) !important;
}
[data-testid="stExpander"] summary {
    padding: 14px 18px !important;
    font-family: 'Geist', sans-serif !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    color: var(--text) !important;
}
[data-testid="stExpander"] summary:hover {
    background: var(--primary-dim) !important;
    color: var(--primary) !important;
}
[data-testid="stExpanderDetails"] {
    padding: 16px 18px !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid var(--border) !important;
    gap: 4px !important;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'Geist', sans-serif !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 8px 18px !important;
    color: var(--text-muted) !important;
    transition: all 0.15s ease !important;
    border: none !important;
}
[data-testid="stTabs"] [role="tab"]:hover {
    color: var(--text) !important;
    background: var(--primary-dim) !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--primary) !important;
    border-bottom: 2px solid var(--primary) !important;
    font-weight: 600 !important;
}

/* ── Alert / info boxes ────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border-left-width: 4px !important;
    font-family: 'Geist', sans-serif !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
    background: var(--bg-card) !important;
}

/* ── Chat messages ─────────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-card) !important;
    padding: 14px 18px !important;
    margin-bottom: 10px !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: var(--primary-dim) !important;
    border-color: var(--primary-border) !important;
}

/* ── Code blocks ───────────────────────────────────────────────────────────── */
.stCodeBlock, pre {
    border-radius: 12px !important;
    border: 1px solid var(--border) !important;
    background: #010409 !important;
}
code {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 13px !important;
    background: var(--bg-elevated) !important;
    padding: 2px 6px !important;
    border-radius: 6px !important;
    color: var(--primary) !important;
}

/* ── DataFrames / Tables ───────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: var(--r-card) !important;
    overflow: hidden !important;
    border: 1px solid var(--border) !important;
}

/* ── Progress bar ──────────────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--primary), #FF9A20) !important;
    border-radius: var(--r-pill) !important;
}

/* ── Spinner ───────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div {
    border-top-color: var(--primary) !important;
}

/* ── Divider ───────────────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 24px 0 !important;
}

/* ── Scrollbar ─────────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: #30363D; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary); }

/* ── Streamlit chrome ──────────────────────────────────────────────────────── */
#MainMenu, footer, [data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] {
    background: rgba(13, 17, 23, 0.95) !important;
    border-bottom: 1px solid var(--border) !important;
    backdrop-filter: blur(12px) !important;
}

/* ── Utility classes (used in custom HTML blocks) ──────────────────────────── */
.rave-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--r-card);
    padding: 24px;
    margin-bottom: 16px;
}
.rave-card-hover:hover {
    border-color: var(--primary-border);
    box-shadow: 0 0 24px var(--primary-glow);
}
.rave-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: var(--r-pill);
    font-size: 12px;
    font-weight: 500;
    font-family: 'Geist', sans-serif;
    line-height: 1.5;
}
.rave-badge-primary { background: var(--primary-dim); color: var(--primary); border: 1px solid var(--primary-border); }
.rave-badge-success { background: rgba(63,185,80,0.10); color: #3FB950; border: 1px solid rgba(63,185,80,0.30); }
.rave-badge-warning { background: rgba(210,153,34,0.10); color: #D29922; border: 1px solid rgba(210,153,34,0.30); }
.rave-badge-error   { background: rgba(248,81,73,0.10);  color: #F85149; border: 1px solid rgba(248,81,73,0.30);  }
.rave-badge-info    { background: rgba(56,139,253,0.10); color: #388BFD; border: 1px solid rgba(56,139,253,0.30); }

.rave-page-header { margin-bottom: 24px; }
.rave-page-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 26px;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 4px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.rave-page-title span.accent { color: var(--primary); }
.rave-page-subtitle {
    font-family: 'Geist', sans-serif;
    font-size: 14px;
    color: var(--text-muted);
    margin: 0;
}
</style>
"""


def apply_rave_theme() -> None:
    """Inject the RAVE AI design system CSS into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(icon: str, title: str, accent: str, subtitle: str = "") -> None:
    """
    Render a styled page header using the RAVE AI design system.
    accent is the part of the title rendered in orange.
    """
    sub_html = f'<p class="rave-page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="rave-page-header">
            <h1 class="rave-page-title">
                {icon} {title} <span class="accent">{accent}</span>
            </h1>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, variant: str = "primary") -> str:
    """Return an HTML badge string. variant: primary | success | warning | error | info"""
    return f'<span class="rave-badge rave-badge-{variant}">{text}</span>'


def card(content_html: str, hover: bool = True) -> None:
    """Render a styled card block with optional hover effect."""
    hover_cls = "rave-card-hover" if hover else ""
    st.markdown(
        f'<div class="rave-card {hover_cls}">{content_html}</div>',
        unsafe_allow_html=True,
    )
