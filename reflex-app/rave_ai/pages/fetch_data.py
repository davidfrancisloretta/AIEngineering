"""
Fetch Data Page — Lunaris design system
ODM XML import + quick action links
"""
import reflex as rx
from rave_ai.layout import page_layout
from rave_ai.state import OdmUploadState
from rave_ai import theme as T


def _action_card(icon: str, title: str, subtitle: str, href: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.text(icon, font_size="20px"),
                width="40px", height="40px",
                border_radius=T.RADIUS_S,
                background_color=f"{T.PRIMARY}15",
                border=f"1px solid {T.PRIMARY}30",
                display="flex", align_items="center", justify_content="center",
            ),
            rx.vstack(
                rx.text(title, font_family=T.FONT_MONO, font_size="13px",
                        font_weight="600", color=T.FG),
                rx.text(subtitle, font_family=T.FONT_BODY, font_size="12px",
                        color=T.MUTED_FG),
                spacing="1", align="start",
            ),
            rx.link(
                rx.box(
                    rx.text("Go →", font_family=T.FONT_MONO, font_size="12px",
                            font_weight="500", color=T.PRIMARY),
                    padding="4px 14px",
                    border=f"1px solid {T.PRIMARY}",
                    border_radius=T.RADIUS_PILL,
                    cursor="pointer",
                    _hover={"background_color": T.PRIMARY, "color": T.PRIMARY_FG},
                ),
                href=href,
                text_decoration="none",
            ),
            spacing="3", align="start",
        ),
        padding="20px 22px",
        background_color=T.CARD,
        border=f"1px solid {T.BORDER}",
        border_radius=T.RADIUS_M,
        width="100%",
        style={"boxShadow": T.SHADOW_SM},
        _hover={"border_color": T.PRIMARY},
        transition="border-color 0.15s ease",
    )


def fetch_data_page() -> rx.Component:
    return page_layout(rx.box(

        # Page header
        rx.box(
            rx.vstack(
                rx.text("Fetch Data", font_family=T.FONT_MONO,
                        font_size="24px", font_weight="700", color=T.FG),
                rx.text("Configure your Medidata API key and import clinical trial data",
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

                # ── Medidata API Key Card ──────────────────────────────
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.box(
                                rx.text("🔑", font_size="18px"),
                                width="36px", height="36px",
                                border_radius=T.RADIUS_S,
                                background_color=f"{T.PRIMARY}15",
                                border=f"1px solid {T.PRIMARY}30",
                                display="flex", align_items="center",
                                justify_content="center",
                            ),
                            rx.vstack(
                                rx.text("Medidata Rave API Key",
                                        font_family=T.FONT_MONO, font_size="16px",
                                        font_weight="600", color=T.FG),
                                rx.text(
                                    "Connect to your Medidata Rave environment to fetch clinical data "
                                    "directly via ODM or YAML export",
                                    font_family=T.FONT_BODY, font_size="13px",
                                    color=T.MUTED_FG,
                                ),
                                spacing="1", align="start",
                            ),
                            spacing="3", align="center", width="100%",
                        ),

                        rx.box(height="1px", background_color=T.BORDER, width="100%"),

                        # API Key input row
                        rx.vstack(
                            rx.text("API Key", font_family=T.FONT_MONO,
                                    font_size="12px", font_weight="600",
                                    color=T.MUTED_FG, letter_spacing="0.05em"),
                            rx.hstack(
                                rx.input(
                                    placeholder="Enter your Medidata API key…",
                                    value=OdmUploadState.medi_api_key,
                                    on_change=OdmUploadState.set_medi_api_key,
                                    type=rx.cond(OdmUploadState.medi_show_key, "text", "password"),
                                    font_family=T.FONT_MONO,
                                    font_size="13px",
                                    height="42px",
                                    width="100%",
                                    padding="0 14px",
                                    border_radius=T.RADIUS_S,
                                    border=f"1px solid {T.BORDER}",
                                    background_color=T.BACKGROUND,
                                    _focus={"border_color": T.PRIMARY,
                                            "outline": "none",
                                            "box_shadow": f"0 0 0 3px {T.PRIMARY}22"},
                                    _placeholder={"color": T.MUTED_FG},
                                ),
                                rx.button(
                                    rx.cond(OdmUploadState.medi_show_key,
                                            rx.text("Hide", font_family=T.FONT_MONO, font_size="12px"),
                                            rx.text("Show", font_family=T.FONT_MONO, font_size="12px")),
                                    on_click=OdmUploadState.toggle_medi_show_key,
                                    height="42px", padding="0 16px",
                                    border_radius=T.RADIUS_S,
                                    variant="outline",
                                    border=f"1px solid {T.BORDER}",
                                    color=T.MUTED_FG,
                                    cursor="pointer",
                                    _hover={"border_color": T.PRIMARY, "color": T.PRIMARY},
                                ),
                                width="100%", spacing="2",
                            ),
                            spacing="2", width="100%",
                        ),

                        # Environment info row
                        rx.hstack(
                            rx.hstack(
                                rx.box(width="6px", height="6px", border_radius="50%",
                                       background_color=rx.cond(
                                           OdmUploadState.medi_api_key_saved,
                                           T.SUCCESS, T.MUTED_FG),
                                       flex_shrink="0"),
                                rx.text(
                                    rx.cond(OdmUploadState.medi_api_key_saved,
                                            "Connected", "Not connected"),
                                    font_family=T.FONT_MONO, font_size="12px",
                                    color=rx.cond(OdmUploadState.medi_api_key_saved,
                                                  "#004D1A", T.MUTED_FG)),
                                spacing="2", align="center",
                            ),
                            rx.spacer(),
                            rx.hstack(
                                rx.button(
                                    rx.text("Clear", font_family=T.FONT_MONO,
                                            font_size="13px"),
                                    on_click=OdmUploadState.clear_medi_api_key,
                                    height="36px", padding="0 18px",
                                    border_radius=T.RADIUS_PILL,
                                    variant="outline",
                                    border=f"1px solid {T.BORDER}",
                                    color=T.MUTED_FG,
                                    cursor="pointer",
                                    _hover={"border_color": T.PRIMARY, "color": T.PRIMARY},
                                ),
                                rx.button(
                                    rx.text("Save & Connect", font_family=T.FONT_MONO,
                                            font_size="13px"),
                                    on_click=OdmUploadState.save_medi_api_key,
                                    height="36px", padding="0 22px",
                                    border_radius=T.RADIUS_PILL,
                                    background_color=T.PRIMARY,
                                    color=T.PRIMARY_FG,
                                    cursor="pointer",
                                    _hover={"background_color": T.PRIMARY_HOVER},
                                    style={"boxShadow": T.SHADOW_PRIMARY},
                                ),
                                spacing="2",
                            ),
                            width="100%", align="center",
                        ),

                        # Success
                        rx.cond(
                            OdmUploadState.medi_api_key_saved,
                            rx.box(
                                rx.hstack(
                                    rx.text("✅", font_size="14px"),
                                    rx.text("API key saved — Medidata Rave connection active. "
                                            "You can now import ODM/YAML files below.",
                                            font_family=T.FONT_BODY, font_size="13px",
                                            color="#004D1A", font_weight="500"),
                                    spacing="2", align="center",
                                ),
                                padding="12px 16px",
                                background_color="#DFE6E1",
                                border_radius=T.RADIUS_S,
                                border="1px solid #A0C4A0",
                                width="100%",
                            ),
                        ),

                        # Error
                        rx.cond(
                            OdmUploadState.medi_api_key_error != "",
                            rx.box(
                                rx.hstack(
                                    rx.text("⚠️", font_size="14px"),
                                    rx.text(OdmUploadState.medi_api_key_error,
                                            font_family=T.FONT_BODY, font_size="13px",
                                            color=T.ERROR_FG),
                                    spacing="2", align="center",
                                ),
                                padding="12px 16px",
                                background_color=T.ERROR_BG,
                                border_radius=T.RADIUS_S,
                                border="1px solid #D4A0A0",
                                width="100%",
                            ),
                        ),

                        spacing="4", width="100%", align="start",
                    ),
                    padding="24px 28px",
                    background_color=T.CARD,
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_M,
                    width="100%",
                    style={"boxShadow": T.SHADOW_SM},
                ),

                # ── ODM Import Card ─────────────────────────────────────
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.box(
                                rx.text("📂", font_size="18px"),
                                width="36px", height="36px",
                                border_radius=T.RADIUS_S,
                                background_color=f"{T.PRIMARY}15",
                                border=f"1px solid {T.PRIMARY}30",
                                display="flex", align_items="center",
                                justify_content="center",
                            ),
                            rx.vstack(
                                rx.text("Import Rave ODM File",
                                        font_family=T.FONT_MONO, font_size="16px",
                                        font_weight="600", color=T.FG),
                                rx.text(
                                    "Upload a CDISC ODM XML file exported from Medidata Rave "
                                    "(ClinicalAuditRecords.odm / .xml)",
                                    font_family=T.FONT_BODY, font_size="13px",
                                    color=T.MUTED_FG,
                                ),
                                spacing="1", align="start",
                            ),
                            spacing="3", align="center", width="100%",
                        ),

                        rx.box(height="1px", background_color=T.BORDER, width="100%"),

                        # Upload dropzone
                        rx.upload(
                            rx.vstack(
                                rx.text("📄", font_size="32px"),
                                rx.text(
                                    "Drag & drop your .xml or .odm file here",
                                    font_family=T.FONT_BODY, font_size="14px",
                                    color=T.FG, font_weight="500",
                                ),
                                rx.text(
                                    "or click to browse",
                                    font_family=T.FONT_BODY, font_size="13px",
                                    color=T.MUTED_FG,
                                ),
                                rx.cond(
                                    OdmUploadState.selected_filename != "",
                                    rx.box(
                                        rx.hstack(
                                            rx.text("📎", font_size="13px"),
                                            rx.text(OdmUploadState.selected_filename,
                                                    font_family=T.FONT_MONO, font_size="12px",
                                                    color=T.PRIMARY, font_weight="500"),
                                            spacing="1", align="center",
                                        ),
                                        padding="6px 12px",
                                        background_color=f"{T.PRIMARY}10",
                                        border=f"1px solid {T.PRIMARY}40",
                                        border_radius=T.RADIUS_PILL,
                                    ),
                                ),
                                spacing="2", align="center",
                            ),
                            id="odm_upload",
                            accept={".xml": ["application/xml", "text/xml"],
                                    ".odm": ["application/xml"]},
                            max_files=1,
                            border=f"2px dashed {T.BORDER}",
                            border_radius=T.RADIUS_M,
                            padding="32px",
                            width="100%",
                            background_color=T.BACKGROUND,
                            cursor="pointer",
                            _hover={"border_color": T.PRIMARY,
                                    "background_color": f"{T.PRIMARY}05"},
                            transition="all 0.15s ease",
                            on_drop=OdmUploadState.handle_upload(
                                rx.upload_files(upload_id="odm_upload")
                            ),
                        ),

                        # Upload button + status
                        rx.hstack(
                            rx.cond(
                                OdmUploadState.is_uploading,
                                rx.hstack(
                                    rx.spinner(size="2", color=T.PRIMARY),
                                    rx.text("Parsing and importing…",
                                            font_family=T.FONT_MONO, font_size="13px",
                                            color=T.MUTED_FG),
                                    spacing="2", align="center",
                                ),
                            ),
                            rx.spacer(),
                            rx.button(
                                rx.text("Clear", font_family=T.FONT_MONO,
                                        font_size="13px"),
                                on_click=OdmUploadState.clear_upload,
                                height="36px", padding="0 18px",
                                border_radius=T.RADIUS_PILL,
                                variant="outline",
                                border=f"1px solid {T.BORDER}",
                                color=T.MUTED_FG,
                                cursor="pointer",
                                _hover={"border_color": T.PRIMARY, "color": T.PRIMARY},
                            ),
                            width="100%", align="center",
                        ),

                        # Success
                        rx.cond(
                            OdmUploadState.upload_done,
                            rx.box(
                                rx.hstack(
                                    rx.text("✅", font_size="14px"),
                                    rx.text(OdmUploadState.upload_result,
                                            font_family=T.FONT_BODY, font_size="13px",
                                            color="#004D1A", font_weight="500"),
                                    spacing="2", align="center",
                                ),
                                padding="12px 16px",
                                background_color="#DFE6E1",
                                border_radius=T.RADIUS_S,
                                border="1px solid #A0C4A0",
                                width="100%",
                            ),
                        ),

                        # Error
                        rx.cond(
                            OdmUploadState.upload_error != "",
                            rx.box(
                                rx.hstack(
                                    rx.text("⚠️", font_size="14px"),
                                    rx.text(OdmUploadState.upload_error,
                                            font_family=T.FONT_BODY, font_size="13px",
                                            color=T.ERROR_FG),
                                    spacing="2", align="center",
                                ),
                                padding="12px 16px",
                                background_color=T.ERROR_BG,
                                border_radius=T.RADIUS_S,
                                border="1px solid #D4A0A0",
                                width="100%",
                            ),
                        ),

                        spacing="4", width="100%", align="start",
                    ),
                    padding="24px 28px",
                    background_color=T.CARD,
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_M,
                    width="100%",
                    style={"boxShadow": T.SHADOW_SM},
                ),

                # ── Quick Actions ────────────────────────────────────────
                rx.text("Quick Actions", font_family=T.FONT_MONO,
                        font_size="11px", font_weight="600",
                        color=T.MUTED_FG, letter_spacing="0.08em"),

                rx.grid(
                    _action_card("🧬", "Seed Demo Data",
                                 "Load CARDIO-2024 synthetic dataset", "/onboarding"),
                    _action_card("🔍", "Index for RAG",
                                 "Embed data for AI vector search", "/onboarding"),
                    _action_card("📊", "View Trial Data",
                                 "Browse enrolled subjects", "/trials"),
                    columns="3", spacing="4", width="100%",
                ),

                # ── Workflow info ────────────────────────────────────────
                rx.box(
                    rx.hstack(
                        rx.text("ℹ️", font_size="14px"),
                        rx.vstack(
                            rx.text("Data Workflow", font_family=T.FONT_MONO,
                                    font_size="12px", font_weight="600", color=T.FG),
                            rx.vstack(
                                *[rx.hstack(
                                    rx.box(width="5px", height="5px", border_radius="50%",
                                           background_color=T.PRIMARY, flex_shrink="0",
                                           margin_top="5px"),
                                    rx.text(step, font_family=T.FONT_BODY,
                                            font_size="13px", color=T.FG),
                                    spacing="2", align="start",
                                ) for step in [
                                    "Enter your Medidata Rave API key to connect, then import an ODM/YAML file — or use Seed Demo Data",
                                    "Then Ingest for RAG to enable AI vector search",
                                    "Browse subjects in Trial Data",
                                    "Ask questions in AI Chat",
                                ]],
                                spacing="2",
                            ),
                            spacing="2", align="start",
                        ),
                        spacing="3", align="start",
                    ),
                    padding="16px 20px",
                    background_color=T.INFO_BG,
                    border=f"1px solid {T.BORDER}",
                    border_radius=T.RADIUS_S,
                    width="100%",
                ),

                spacing="4", width="100%",
            ),
            padding="24px 32px",
            width="100%",
        ),

        width="100%",
        min_height="100vh",
        background_color=T.BACKGROUND,
    ))
