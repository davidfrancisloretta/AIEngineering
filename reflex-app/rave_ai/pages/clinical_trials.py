"""
Clinical Trials Page — Lunaris design system
"""
import reflex as rx
from rave_ai.layout import page_layout
from rave_ai.state import TrialDataState, OnboardingState
from rave_ai import theme as T


# ── Helpers ──────────────────────────────────────────────────────────────────

def kpi_card(label: str, value) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(label, font_family=T.FONT_MONO, font_size="10px",
                    font_weight="600", color=T.MUTED_FG, letter_spacing="0.08em"),
            rx.text(value, font_family=T.FONT_MONO, font_size="24px",
                    font_weight="700", color=T.PRIMARY),
            spacing="1",
            align="center",
        ),
        padding="18px 20px",
        background_color=T.CARD,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS_M,
        text_align="center",
        flex="1",
        style={"boxShadow": T.SHADOW_SM},
    )


def subject_row(s) -> rx.Component:
    status_color = rx.cond(
        s["status"] == "Enrolled", "green",
        rx.cond(s["status"] == "Completed", "blue", "red")
    )
    is_selected = TrialDataState.selected_subject_id == s["id"]
    return rx.table.row(
        rx.table.cell(rx.text(s["subject_key"], size="1",
                              font_family=T.FONT_MONO, color=T.PRIMARY, font_weight="500")),
        rx.table.cell(rx.text(s["site_name"], size="1", font_family=T.FONT_BODY)),
        rx.table.cell(rx.text(s["age"], size="1", font_family=T.FONT_BODY)),
        rx.table.cell(rx.text(s["sex"], size="1", font_family=T.FONT_BODY)),
        rx.table.cell(rx.text(s["race"], size="1", font_family=T.FONT_BODY)),
        rx.table.cell(rx.text(s["enrollment_date"], size="1", font_family=T.FONT_MONO)),
        rx.table.cell(
            rx.badge(s["status"], color_scheme=status_color, size="1"),
        ),
        rx.table.cell(
            rx.box(
                rx.text("View →", font_family=T.FONT_MONO, font_size="11px",
                        color=T.PRIMARY, font_weight="500"),
                padding="3px 10px",
                border=f"1px solid {T.PRIMARY}",
                border_radius=T.RADIUS_PILL,
                cursor="pointer",
            ),
        ),
        on_click=TrialDataState.select_subject(s["id"]),
        style={
            "_hover": {"background_color": f"{T.PRIMARY}08", "cursor": "pointer"},
            "background_color": rx.cond(is_selected, f"{T.PRIMARY}12", "transparent"),
        },
    )


def _info_row(label: str, value) -> rx.Component:
    return rx.hstack(
        rx.text(label, font_family=T.FONT_MONO, font_size="11px",
                font_weight="600", color=T.MUTED_FG, min_width="130px"),
        rx.text(value, font_family=T.FONT_BODY, font_size="13px", color=T.FG),
        spacing="3", width="100%",
    )


def _vs_row(vs) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(vs["visit"], size="1", font_family=T.FONT_MONO, color=T.PRIMARY)),
        rx.table.cell(rx.text(vs["date"], size="1", font_family=T.FONT_MONO, color=T.MUTED_FG)),
        rx.table.cell(rx.text(vs["hr"], size="1", font_family=T.FONT_BODY)),
        rx.table.cell(
            rx.hstack(
                rx.text(vs["sbp"], size="1", font_family=T.FONT_BODY),
                rx.text("/", size="1", color=T.MUTED_FG),
                rx.text(vs["dbp"], size="1", font_family=T.FONT_BODY),
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(vs["temp"], size="1", font_family=T.FONT_BODY),
                rx.text(" °C", size="1", font_family=T.FONT_BODY, color=T.MUTED_FG),
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(vs["weight"], size="1", font_family=T.FONT_BODY),
                rx.text(" kg", size="1", font_family=T.FONT_BODY, color=T.MUTED_FG),
                spacing="0",
            )
        ),
        style={"_hover": {"background_color": T.BACKGROUND}},
    )


def _ae_row(ae) -> rx.Component:
    severity_color = rx.cond(
        ae["severity"] == "Severe", "red",
        rx.cond(ae["severity"] == "Moderate", "orange", "green")
    )
    return rx.table.row(
        rx.table.cell(rx.text(ae["visit"], size="1", font_family=T.FONT_MONO, color=T.PRIMARY)),
        rx.table.cell(rx.text(ae["date"], size="1", font_family=T.FONT_MONO, color=T.MUTED_FG)),
        rx.table.cell(rx.text(ae["term"], size="1", font_family=T.FONT_BODY, font_weight="500")),
        rx.table.cell(rx.badge(ae["severity"], color_scheme=severity_color, size="1")),
        rx.table.cell(rx.text(ae["relationship"], size="1", font_family=T.FONT_BODY)),
        rx.table.cell(rx.text(ae["outcome"], size="1", font_family=T.FONT_BODY)),
        style={"_hover": {"background_color": T.BACKGROUND}},
    )


def _lab_row(lab) -> rx.Component:
    flag_color = rx.cond(
        lab["flag"] == "N", "gray",
        rx.cond(
            (lab["flag"] == "H") | (lab["flag"] == "HH"), "red", "orange"
        )
    )
    return rx.table.row(
        rx.table.cell(rx.text(lab["visit"], size="1", font_family=T.FONT_MONO, color=T.PRIMARY)),
        rx.table.cell(rx.text(lab["test"], size="1", font_family=T.FONT_MONO, font_weight="600")),
        rx.table.cell(rx.text(lab["name"], size="1", font_family=T.FONT_BODY)),
        rx.table.cell(rx.text(lab["value"], size="1", font_family=T.FONT_MONO)),
        rx.table.cell(rx.text(lab["unit"], size="1", font_family=T.FONT_BODY, color=T.MUTED_FG)),
        rx.table.cell(rx.badge(lab["flag"], color_scheme=flag_color, size="1")),
        style={"_hover": {"background_color": T.BACKGROUND}},
    )


def _no_subject_selected_callout() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("👆", font_size="32px"),
            rx.text("Select a subject from Study Overview",
                    font_family=T.FONT_MONO, font_size="15px",
                    font_weight="600", color=T.FG),
            rx.text(
                "Click any row in the Study Overview tab to load that subject's "
                "visit history, vital signs, adverse events, and lab results.",
                font_family=T.FONT_BODY, font_size="13px",
                color=T.MUTED_FG, text_align="center", max_width="400px",
                line_height="1.6",
            ),
            spacing="3", align="center",
        ),
        padding="48px 32px",
        background_color=T.CARD,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS_M,
        width="100%",
        text_align="center",
        style={"boxShadow": T.SHADOW_SM},
    )


# ── Subject Detail Tab ────────────────────────────────────────────────────────

def subject_detail_tab() -> rx.Component:
    return rx.box(
        rx.cond(
            TrialDataState.selected_subject_id == -1,
            _no_subject_selected_callout(),

            rx.cond(
                TrialDataState.subject_loading,
                rx.hstack(
                    rx.spinner(size="3", color=T.PRIMARY),
                    rx.vstack(
                        rx.text("Loading subject data…",
                                font_family=T.FONT_MONO, font_size="14px",
                                font_weight="500", color=T.FG),
                        rx.text("Fetching visits, vital signs and forms",
                                font_family=T.FONT_BODY, font_size="12px",
                                color=T.MUTED_FG),
                        spacing="0", align="start",
                    ),
                    spacing="3", align="center", padding="32px",
                ),

                rx.vstack(
                    # Subject header card
                    rx.box(
                        rx.hstack(
                            rx.box(
                                rx.text(TrialDataState.selected_subject_key[:2],
                                        font_family=T.FONT_MONO, font_size="18px",
                                        font_weight="700", color=T.PRIMARY_FG),
                                width="52px", height="52px",
                                border_radius=T.RADIUS_M,
                                background_color=T.PRIMARY,
                                display="flex", align_items="center",
                                justify_content="center",
                                flex_shrink="0",
                            ),
                            rx.vstack(
                                rx.text(TrialDataState.selected_subject_key,
                                        font_family=T.FONT_MONO, font_size="18px",
                                        font_weight="700", color=T.FG),
                                rx.hstack(
                                    rx.badge(TrialDataState.selected_subject_status,
                                             color_scheme=rx.cond(
                                                 TrialDataState.selected_subject_status == "Enrolled",
                                                 "green", rx.cond(
                                                     TrialDataState.selected_subject_status == "Completed",
                                                     "blue", "red"
                                                 )
                                             ), size="1"),
                                    rx.text("·", color=T.BORDER),
                                    rx.text(TrialDataState.selected_subject_site,
                                            font_family=T.FONT_BODY, font_size="13px",
                                            color=T.MUTED_FG),
                                    spacing="2", align="center",
                                ),
                                spacing="1", align="start",
                            ),
                            rx.spacer(),
                            rx.grid(
                                rx.vstack(
                                    rx.text("Age", font_family=T.FONT_MONO, font_size="9px",
                                            color=T.MUTED_FG, letter_spacing="0.08em"),
                                    rx.text(TrialDataState.selected_subject_age,
                                            font_family=T.FONT_MONO, font_size="20px",
                                            font_weight="700", color=T.FG),
                                    spacing="0", align="center",
                                ),
                                rx.vstack(
                                    rx.text("Sex", font_family=T.FONT_MONO, font_size="9px",
                                            color=T.MUTED_FG, letter_spacing="0.08em"),
                                    rx.text(TrialDataState.selected_subject_sex,
                                            font_family=T.FONT_MONO, font_size="20px",
                                            font_weight="700", color=T.FG),
                                    spacing="0", align="center",
                                ),
                                rx.vstack(
                                    rx.text("Enrolled", font_family=T.FONT_MONO, font_size="9px",
                                            color=T.MUTED_FG, letter_spacing="0.08em"),
                                    rx.text(TrialDataState.selected_subject_enrolled,
                                            font_family=T.FONT_MONO, font_size="13px",
                                            font_weight="600", color=T.FG),
                                    spacing="0", align="center",
                                ),
                                columns="3", spacing="6",
                            ),
                            spacing="4", width="100%", align="center",
                        ),
                        padding="20px 24px",
                        background_color=T.CARD,
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_M,
                        width="100%",
                        style={"boxShadow": T.SHADOW_SM},
                    ),

                    # Vital Signs table
                    rx.vstack(
                        rx.text("Vital Signs by Visit", font_family=T.FONT_MONO,
                                font_size="12px", font_weight="600",
                                color=T.MUTED_FG, letter_spacing="0.06em"),
                        rx.box(
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("Visit"),
                                        rx.table.column_header_cell("Date"),
                                        rx.table.column_header_cell("HR (bpm)"),
                                        rx.table.column_header_cell("BP (mmHg)"),
                                        rx.table.column_header_cell("Temp"),
                                        rx.table.column_header_cell("Weight"),
                                    ),
                                ),
                                rx.table.body(
                                    rx.foreach(TrialDataState.subject_vital_signs, _vs_row),
                                ),
                                width="100%", size="1",
                            ),
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_S,
                            overflow_x="auto",
                            background_color=T.CARD,
                            width="100%",
                        ),
                        spacing="2", width="100%", align="start",
                    ),

                    # Medications
                    rx.cond(
                        TrialDataState.has_meds,
                        rx.vstack(
                            rx.text("Concomitant Medications", font_family=T.FONT_MONO,
                                    font_size="12px", font_weight="600",
                                    color=T.MUTED_FG, letter_spacing="0.06em"),
                            rx.box(
                                rx.flex(
                                    rx.foreach(
                                        TrialDataState.subject_meds,
                                        lambda m: rx.box(
                                            rx.text(m, font_family=T.FONT_BODY,
                                                    font_size="12px", color=T.FG),
                                            padding="4px 12px",
                                            background_color=f"{T.PRIMARY}10",
                                            border=f"1px solid {T.PRIMARY}30",
                                            border_radius=T.RADIUS_PILL,
                                        ),
                                    ),
                                    wrap="wrap", spacing="2",
                                ),
                                padding="16px",
                                background_color=T.CARD,
                                border=f"1px solid {T.BORDER}",
                                border_radius=T.RADIUS_S,
                                width="100%",
                            ),
                            spacing="2", width="100%", align="start",
                        ),
                    ),

                    spacing="4", width="100%",
                ),
            ),
        ),
        overflow_y="auto",
        max_height="calc(100vh - 340px)",
        padding_right="4px",
    )


# ── Adverse Events Tab ────────────────────────────────────────────────────────

def adverse_events_tab() -> rx.Component:
    return rx.box(
        rx.cond(
            TrialDataState.selected_subject_id == -1,
            _no_subject_selected_callout(),
            rx.cond(
                TrialDataState.subject_loading,
                rx.hstack(
                    rx.spinner(size="3", color=T.PRIMARY),
                    rx.text("Loading adverse events…",
                            font_family=T.FONT_BODY, font_size="13px", color=T.MUTED_FG),
                    spacing="3", padding="32px",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Adverse Events", font_family=T.FONT_MONO,
                                font_size="14px", font_weight="600", color=T.FG),
                        rx.text("—", color=T.BORDER),
                        rx.text(TrialDataState.selected_subject_key,
                                font_family=T.FONT_MONO, font_size="13px",
                                color=T.PRIMARY),
                        rx.spacer(),
                        rx.badge(TrialDataState.ae_count, color_scheme="orange", size="1"),
                        width="100%", align="center",
                    ),
                    rx.cond(
                        TrialDataState.has_ae_entries,
                        rx.box(
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        rx.table.column_header_cell("Visit"),
                                        rx.table.column_header_cell("Date"),
                                        rx.table.column_header_cell("Term"),
                                        rx.table.column_header_cell("Severity"),
                                        rx.table.column_header_cell("Relationship"),
                                        rx.table.column_header_cell("Outcome"),
                                    ),
                                ),
                                rx.table.body(
                                    rx.foreach(TrialDataState.subject_ae_entries, _ae_row),
                                ),
                                width="100%", size="1",
                            ),
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_S,
                            overflow_x="auto",
                            background_color=T.CARD,
                            width="100%",
                        ),
                        rx.box(
                            rx.vstack(
                                rx.text("✅", font_size="28px"),
                                rx.text("No adverse events recorded",
                                        font_family=T.FONT_MONO, font_size="14px",
                                        font_weight="600", color=T.FG),
                                rx.text("This subject had no AEs across all visits.",
                                        font_family=T.FONT_BODY, font_size="13px",
                                        color=T.MUTED_FG),
                                spacing="2", align="center",
                            ),
                            padding="40px", text_align="center", width="100%",
                            background_color=T.CARD,
                            border=f"1px solid {T.BORDER}",
                            border_radius=T.RADIUS_M,
                        ),
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        overflow_y="auto",
        max_height="calc(100vh - 340px)",
        padding_right="4px",
    )


# ── Lab Results Tab ───────────────────────────────────────────────────────────

def lab_results_tab() -> rx.Component:
    return rx.box(
        rx.cond(
            TrialDataState.selected_subject_id == -1,
            _no_subject_selected_callout(),
            rx.cond(
                TrialDataState.subject_loading,
                rx.hstack(
                    rx.spinner(size="3", color=T.PRIMARY),
                    rx.text("Loading lab results…",
                            font_family=T.FONT_BODY, font_size="13px", color=T.MUTED_FG),
                    spacing="3", padding="32px",
                ),
                rx.vstack(
                    rx.hstack(
                        rx.text("Lab Results", font_family=T.FONT_MONO,
                                font_size="14px", font_weight="600", color=T.FG),
                        rx.text("—", color=T.BORDER),
                        rx.text(TrialDataState.selected_subject_key,
                                font_family=T.FONT_MONO, font_size="13px",
                                color=T.PRIMARY),
                        rx.spacer(),
                        rx.hstack(
                            rx.badge("N = Normal", color_scheme="gray", size="1"),
                            rx.badge("H/HH = High", color_scheme="red", size="1"),
                            rx.badge("L/LL = Low", color_scheme="orange", size="1"),
                            spacing="2",
                        ),
                        width="100%", align="center",
                    ),
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Visit"),
                                    rx.table.column_header_cell("Code"),
                                    rx.table.column_header_cell("Test Name"),
                                    rx.table.column_header_cell("Value"),
                                    rx.table.column_header_cell("Unit"),
                                    rx.table.column_header_cell("Flag"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(TrialDataState.subject_lab_entries, _lab_row),
                            ),
                            width="100%", size="1",
                        ),
                        border=f"1px solid {T.BORDER}",
                        border_radius=T.RADIUS_S,
                        overflow_x="auto",
                        background_color=T.CARD,
                        width="100%",
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        overflow_y="auto",
        max_height="calc(100vh - 340px)",
        padding_right="4px",
    )


# ── Page ─────────────────────────────────────────────────────────────────────

def clinical_trials_page() -> rx.Component:
    return page_layout(rx.box(
        # Page header
        rx.box(
            rx.hstack(
                rx.vstack(
                    rx.text("Clinical Trials", font_family=T.FONT_MONO,
                            font_size="24px", font_weight="700", color=T.FG),
                    rx.cond(
                        TrialDataState.has_subjects,
                        rx.hstack(
                            rx.text(TrialDataState.study_oid, font_family=T.FONT_MONO,
                                    font_size="13px", color=T.PRIMARY, font_weight="600"),
                            rx.text("—", color=T.BORDER),
                            rx.text(TrialDataState.study_protocol, font_family=T.FONT_BODY,
                                    font_size="13px", color=T.MUTED_FG),
                            spacing="2", align="center",
                        ),
                        rx.text("Load data to see study information",
                                font_family=T.FONT_BODY, font_size="13px", color=T.MUTED_FG),
                    ),
                    spacing="1", align="start",
                ),
                rx.spacer(),
                width="100%", align="center",
            ),
            padding="24px 32px 20px",
            border_bottom=f"1px solid {T.BORDER}",
            background_color=T.CARD,
            width="100%",
        ),

        rx.vstack(

            # ── Data Actions bar ──────────────────────────────────────
            rx.box(
                rx.hstack(
                    rx.hstack(
                        rx.button(
                            rx.cond(
                                TrialDataState.seed_loading,
                                rx.hstack(rx.spinner(size="2"),
                                          rx.text("Seeding…", font_family=T.FONT_MONO,
                                                  font_size="13px"), spacing="2"),
                                rx.text("🧬  Seed Demo Data", font_family=T.FONT_MONO,
                                        font_size="13px", font_weight="500"),
                            ),
                            on_click=TrialDataState.seed_data,
                            disabled=TrialDataState.seed_loading,
                            height="36px", padding="0 18px",
                            border_radius=T.RADIUS_PILL,
                            background_color=T.PRIMARY,
                            color=T.PRIMARY_FG,
                            cursor="pointer",
                            _hover={"background_color": T.PRIMARY_HOVER},
                        ),
                        rx.button(
                            rx.cond(
                                OnboardingState.ingest_running,
                                rx.hstack(rx.spinner(size="2"),
                                          rx.text("Ingesting…", font_family=T.FONT_MONO,
                                                  font_size="13px"), spacing="2"),
                                rx.text("🔍  Ingest for RAG", font_family=T.FONT_MONO,
                                        font_size="13px"),
                            ),
                            on_click=OnboardingState.start_ingest,
                            disabled=OnboardingState.ingest_running,
                            height="36px", padding="0 18px",
                            border_radius=T.RADIUS_PILL,
                            variant="outline",
                            border=f"1px solid {T.BORDER}",
                            color=T.FG,
                            cursor="pointer",
                            _hover={"border_color": T.PRIMARY, "color": T.PRIMARY},
                        ),
                        spacing="2",
                    ),
                    rx.spacer(),
                    rx.cond(
                        TrialDataState.seed_message != "",
                        rx.box(
                            rx.hstack(
                                rx.text("✅", font_size="13px"),
                                rx.text(TrialDataState.seed_message,
                                        font_family=T.FONT_BODY, font_size="12px",
                                        color="#004D1A"),
                                spacing="1",
                            ),
                            padding="6px 12px",
                            background_color="#DFE6E1",
                            border_radius=T.RADIUS_PILL,
                            border=f"1px solid #A0C4A0",
                        ),
                    ),
                    rx.cond(
                        OnboardingState.ingest_done,
                        rx.box(
                            rx.hstack(
                                rx.text("✅", font_size="13px"),
                                rx.text(OnboardingState.chunk_count,
                                        font_family=T.FONT_MONO, font_size="12px",
                                        font_weight="600", color="#004D1A"),
                                rx.text("chunks indexed", font_family=T.FONT_BODY,
                                        font_size="12px", color="#004D1A"),
                                spacing="1",
                            ),
                            padding="6px 12px",
                            background_color="#DFE6E1",
                            border_radius=T.RADIUS_PILL,
                            border=f"1px solid #A0C4A0",
                        ),
                    ),
                    align="center",
                    width="100%",
                ),
                padding="1rem",
                background_color=T.CARD,
                border=f"1px solid {T.BORDER}",
                border_radius=T.RADIUS_S,
                width="100%",
            ),

            # ── Loading / Error ───────────────────────────────────────
            rx.cond(
                TrialDataState.is_loading,
                rx.hstack(
                    rx.spinner(), rx.text("Loading clinical data…", color="gray"),
                    spacing="2", padding="1rem",
                ),
            ),
            rx.cond(
                TrialDataState.load_error != "",
                rx.callout(
                    TrialDataState.load_error,
                    icon="triangle_alert", color_scheme="red", width="100%",
                ),
            ),

            # ── KPI Cards ─────────────────────────────────────────────
            rx.cond(
                TrialDataState.has_subjects,
                rx.hstack(
                    kpi_card("SUBJECTS", TrialDataState.subject_count),
                    kpi_card("PHASE", TrialDataState.study_phase),
                    kpi_card("STATUS", TrialDataState.study_status_text),
                    kpi_card("SPONSOR", TrialDataState.study_sponsor),
                    spacing="3",
                    width="100%",
                ),
            ),

            # ── Study metadata ────────────────────────────────────────
            rx.cond(
                TrialDataState.has_subjects,
                rx.vstack(
                    rx.hstack(
                        rx.text("Therapeutic Area:", weight="bold", size="2"),
                        rx.text(TrialDataState.study_therapeutic_area, size="2"),
                        spacing="2",
                    ),
                    rx.hstack(
                        rx.text("Objective:", weight="bold", size="2"),
                        rx.text(TrialDataState.study_objective, size="2",
                                color="#475569"),
                        spacing="2",
                        align="start",
                    ),
                    spacing="2",
                    padding="1rem",
                    background_color=T.INFO_BG,
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_S,
                    width="100%",
                    align="start",
                ),
            ),

            # ── Tabs (controlled) ─────────────────────────────────────
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("📋 Study Overview", value="overview"),
                    rx.tabs.trigger("👤 Subject Detail", value="detail"),
                    rx.tabs.trigger("⚠️ Adverse Events", value="ae"),
                    rx.tabs.trigger("🔬 Lab Results", value="labs"),
                ),

                # TAB 1 — Study Overview
                rx.tabs.content(
                    rx.box(
                        rx.cond(
                            TrialDataState.has_subjects,
                            rx.vstack(
                                rx.hstack(
                                    rx.text("Enrolled Subjects", font_family=T.FONT_MONO,
                                            font_size="14px", font_weight="600", color=T.FG),
                                    rx.text("— click a row to view subject detail",
                                            font_family=T.FONT_BODY, font_size="12px",
                                            color=T.MUTED_FG),
                                    spacing="2", align="center",
                                ),

                                # Site filter + search + count
                                rx.hstack(
                                    rx.hstack(
                                        rx.text("Filter by Site:", size="2", weight="medium"),
                                        rx.select(
                                            TrialDataState.unique_sites,
                                            value=TrialDataState.site_filter,
                                            on_change=TrialDataState.set_site_filter,
                                            size="2",
                                        ),
                                        spacing="2", align="center",
                                    ),
                                    rx.spacer(),
                                    rx.input(
                                        placeholder="Search subjects…",
                                        value=TrialDataState.search_query,
                                        on_change=TrialDataState.set_search_query,
                                        size="2", width="200px",
                                    ),
                                    rx.badge(TrialDataState.filtered_count, color_scheme="blue"),
                                    width="100%", align="center",
                                ),

                                # Table
                                rx.box(
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell("Subject Key"),
                                                rx.table.column_header_cell("Site"),
                                                rx.table.column_header_cell("Age"),
                                                rx.table.column_header_cell("Sex"),
                                                rx.table.column_header_cell("Race"),
                                                rx.table.column_header_cell("Enrolled"),
                                                rx.table.column_header_cell("Status"),
                                                rx.table.column_header_cell(""),
                                            ),
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                TrialDataState.filtered_subjects,
                                                subject_row,
                                            ),
                                        ),
                                        width="100%", size="1",
                                    ),
                                    width="100%",
                                    overflow_x="auto",
                                    border=f"1px solid {T.BORDER}",
                                    border_radius=T.RADIUS_S,
                                    background_color=T.CARD,
                                ),

                                spacing="3", width="100%",
                            ),
                            # No data state
                            rx.box(
                                rx.vstack(
                                    rx.text("No subjects found", weight="bold",
                                            size="4", color="gray"),
                                    rx.text(
                                        "Click 'Seed Demo Data' above to load the CARDIO-2024 demo dataset.",
                                        color="gray", size="2",
                                    ),
                                    spacing="3", align="center",
                                ),
                                padding="3rem", width="100%", text_align="center",
                            ),
                        ),
                        overflow_y="auto",
                        max_height="calc(100vh - 340px)",
                        padding_right="4px",
                    ),
                    value="overview",
                    padding_top="0.75rem",
                ),

                # TAB 2 — Subject Detail
                rx.tabs.content(
                    subject_detail_tab(),
                    value="detail",
                    padding_top="0.75rem",
                ),

                # TAB 3 — Adverse Events
                rx.tabs.content(
                    adverse_events_tab(),
                    value="ae",
                    padding_top="0.75rem",
                ),

                # TAB 4 — Lab Results
                rx.tabs.content(
                    lab_results_tab(),
                    value="labs",
                    padding_top="0.75rem",
                ),

                value=TrialDataState.current_tab,
                on_change=TrialDataState.set_current_tab,
                width="100%",
            ),

            spacing="4",
            width="100%",
        ),
        padding="1.5rem",
        min_height="100vh",
    ))
