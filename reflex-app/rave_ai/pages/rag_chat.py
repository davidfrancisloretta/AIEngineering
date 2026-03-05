"""
RAG Chat Page — Lunaris design system
"""
import reflex as rx
from rave_ai.layout import page_layout
from rave_ai.state import ChatState
from rave_ai import theme as T


# ── Sub-components ─────────────────────────────────────────────────────────

def _bot_avatar(size: int = 32) -> rx.Component:
    return rx.box(
        rx.text("🤖", font_size=f"{size // 2}px"),
        width=f"{size}px", height=f"{size}px",
        border_radius=T.RADIUS_PILL,
        background_color=T.PRIMARY,
        display="flex", align_items="center", justify_content="center",
        flex_shrink="0",
    )


def _ai_message(message) -> rx.Component:
    return rx.box(
        rx.hstack(
            _bot_avatar(32),
            rx.vstack(
                rx.box(
                    rx.text(
                        message["content"],
                        font_family=T.FONT_BODY, font_size="13px",
                        line_height="1.6", color=T.FG, white_space="pre-wrap",
                    ),
                    padding="12px 16px",
                    background_color=T.CARD,
                    border=f"1px solid {T.BORDER}",
                    border_radius="16px 16px 16px 4px",
                    max_width="520px",
                    style={"boxShadow": T.SHADOW_SM},
                ),
                rx.hstack(
                    rx.text("Helpful?", font_family=T.FONT_BODY, font_size="11px", color=T.MUTED_FG),
                    rx.button(
                        "👍", size="1", variant="ghost", cursor="pointer",
                        on_click=ChatState.submit_feedback(message["log_id"], 1),
                        _hover={"background_color": T.MUTED_BG}, padding="2px 6px",
                    ),
                    rx.button(
                        "👎", size="1", variant="ghost", cursor="pointer",
                        on_click=ChatState.submit_feedback(message["log_id"], -1),
                        _hover={"background_color": T.MUTED_BG}, padding="2px 6px",
                    ),
                    spacing="1", align="center", padding_left="4px", padding_top="2px",
                ),
                spacing="1", align_items="start",
            ),
            spacing="2", align="end", width="100%",
        ),
        width="100%", padding_y="6px",
    )


def _user_message(message) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.text(
                    message["content"],
                    font_family=T.FONT_BODY, font_size="13px",
                    line_height="1.6", color=T.PRIMARY_FG, white_space="pre-wrap",
                ),
                padding="10px 16px",
                background_color=T.PRIMARY,
                border_radius="16px 16px 4px 16px",
                max_width="520px",
                style={"boxShadow": f"0 1px 4px {T.PRIMARY}33"},
            ),
            justify="end", width="100%",
        ),
        width="100%", padding_y="6px",
    )


def chat_message(message) -> rx.Component:
    return rx.cond(
        message["role"] == "user",
        _user_message(message),
        _ai_message(message),
    )


def typing_indicator() -> rx.Component:
    return rx.box(
        rx.hstack(
            _bot_avatar(32),
            rx.vstack(
                rx.hstack(
                    rx.box(
                        width="7px", height="7px", border_radius="50%",
                        background_color=T.PRIMARY, class_name="rave-dot rave-dot-1",
                    ),
                    rx.box(
                        width="7px", height="7px", border_radius="50%",
                        background_color=T.PRIMARY, class_name="rave-dot rave-dot-2",
                    ),
                    rx.box(
                        width="7px", height="7px", border_radius="50%",
                        background_color=T.PRIMARY, class_name="rave-dot rave-dot-3",
                    ),
                    rx.text(
                        "RAVE is thinking…",
                        font_family=T.FONT_MONO, font_size="13px",
                        font_weight="500", color=T.FG,
                    ),
                    spacing="2", align="center",
                    padding="10px 16px",
                    background_color=T.CARD,
                    border=f"1px solid {T.BORDER}",
                    border_radius="16px 16px 16px 4px",
                    style={"boxShadow": T.SHADOW_SM},
                ),
                # Animated progress sweep bar
                rx.box(
                    rx.box(
                        height="100%",
                        background_color=T.PRIMARY,
                        border_radius="2px",
                        class_name="rave-progress-fill",
                    ),
                    height="3px",
                    border_radius="2px",
                    background_color=f"{T.PRIMARY}20",
                    overflow="hidden",
                    width="260px",
                    margin_left="4px",
                ),
                spacing="1", align="start",
            ),
            spacing="2", align="start",
        ),
        width="100%", padding_y="6px",
    )


def _chip(label: str, question: str) -> rx.Component:
    return rx.button(
        label,
        on_click=[
            ChatState.set_pending_question(question),
            ChatState.send_pending_question,
        ],
        variant="ghost", size="1",
        font_family=T.FONT_BODY, font_size="11px",
        border_radius=T.RADIUS_PILL,
        border=f"1px solid {T.BORDER}",
        color=T.MUTED_FG,
        _hover={"border_color": T.PRIMARY, "color": T.PRIMARY, "background_color": f"{T.PRIMARY}0D"},
        cursor="pointer",
        padding="0 10px", height="26px",
        white_space="nowrap",
        flex_shrink="0",
    )


def _suggested_btn(label: str, question: str) -> rx.Component:
    return rx.button(
        label,
        on_click=[
            ChatState.set_pending_question(question),
            ChatState.send_pending_question,
        ],
        variant="outline", size="2",
        font_family=T.FONT_BODY, font_size="12px",
        border_radius=T.RADIUS_PILL,
        border=f"1px solid {T.BORDER}",
        color=T.FG, background_color=T.CARD,
        _hover={"border_color": T.PRIMARY, "color": T.PRIMARY},
        cursor="pointer", width="100%",
    )


# ── Page ───────────────────────────────────────────────────────────────────

def rag_chat_page() -> rx.Component:
    return page_layout(
        rx.box(
            rx.vstack(

                # ── Header ──────────────────────────────────────────
                rx.box(
                    rx.hstack(
                        rx.hstack(
                            rx.box(
                                rx.text("🤖", font_size="18px"),
                                width="36px", height="36px",
                                border_radius=T.RADIUS_PILL,
                                background_color=T.PRIMARY,
                                display="flex", align_items="center", justify_content="center",
                            ),
                            rx.vstack(
                                rx.text("AI Chat", font_family=T.FONT_MONO, font_size="16px",
                                        font_weight="600", color=T.FG),
                                rx.text("Ask questions about clinical trial data",
                                        font_family=T.FONT_BODY, font_size="12px", color=T.MUTED_FG),
                                spacing="0", align="start",
                            ),
                            spacing="3", align="center",
                        ),
                        rx.spacer(),
                        rx.button(
                            "🗑️  Clear",
                            on_click=ChatState.clear_chat,
                            variant="outline", size="2",
                            font_family=T.FONT_BODY,
                            border_radius=T.RADIUS_PILL,
                            border=f"1px solid {T.BORDER}",
                            color=T.FG,
                            _hover={"border_color": "#E5534B", "color": "#E5534B"},
                            cursor="pointer",
                        ),
                        width="100%", align="center",
                    ),
                    padding="0 24px", height="64px",
                    background_color=T.CARD,
                    border_bottom=f"1px solid {T.BORDER}",
                    display="flex", align_items="center",
                    width="100%", flex_shrink="0",
                ),

                # ── Messages area ────────────────────────────────────
                rx.box(
                    rx.vstack(
                        # Empty state — suggested questions grid
                        rx.cond(
                            ChatState.no_messages,
                            rx.box(
                                rx.vstack(
                                    rx.text(
                                        "💡 Try a suggested question or type your own below:",
                                        font_family=T.FONT_BODY, font_size="13px",
                                        font_weight="500", color=T.MUTED_FG,
                                    ),
                                    rx.grid(
                                        _suggested_btn("Which subjects had severe adverse events?",
                                                       "Which subjects had severe adverse events?"),
                                        _suggested_btn("What were the abnormal lab results at Week 12?",
                                                       "What were the abnormal lab results at Week 12?"),
                                        _suggested_btn("How many subjects are enrolled at the London site?",
                                                       "How many subjects are enrolled at the London site?"),
                                        _suggested_btn("What is the protocol objective of CARDIO-2024?",
                                                       "What is the protocol objective of CARDIO-2024?"),
                                        _suggested_btn("List all subjects who have completed the trial.",
                                                       "List all subjects who have completed the trial."),
                                        columns="2", spacing="2", width="100%",
                                    ),
                                    spacing="3", width="100%", align="start",
                                ),
                                padding="20px",
                                background_color=T.CARD,
                                border=f"1px solid {T.BORDER}",
                                border_radius=T.RADIUS_M,
                                width="100%",
                            ),
                        ),
                        rx.foreach(ChatState.messages, chat_message),
                        rx.cond(ChatState.is_loading, typing_indicator()),
                        spacing="0", width="100%", align_items="stretch", padding="20px",
                    ),
                    flex="1", width="100%", overflow_y="auto",
                    background_color=T.BACKGROUND, min_height="0",
                ),

                # ── Error callout ────────────────────────────────────
                rx.cond(
                    ChatState.chat_error != "",
                    rx.callout(ChatState.chat_error, icon="triangle_alert",
                               color_scheme="red", width="100%", flex_shrink="0"),
                ),

                # ── Input section ────────────────────────────────────
                rx.box(
                    rx.vstack(
                        # Quick chips
                        rx.hstack(
                            _chip("Severe AEs?",
                                  "Which subjects had severe adverse events?"),
                            _chip("Abnormal labs?",
                                  "What were the abnormal lab results at Week 12?"),
                            _chip("London subjects?",
                                  "How many subjects are enrolled at the London site?"),
                            _chip("CARDIO-2024 objective?",
                                  "What is the protocol objective of CARDIO-2024?"),
                            spacing="2", width="100%", overflow_x="auto",
                        ),
                        # Input + send
                        rx.hstack(
                            rx.input(
                                placeholder="Ask about the clinical trial… (Enter to send)",
                                value=ChatState.input_value,
                                on_change=ChatState.set_input_value,
                                on_key_down=ChatState.handle_key_down,
                                disabled=ChatState.is_loading,
                                width="100%", height="44px",
                                border_radius=T.RADIUS_PILL,
                                border=f"1px solid {T.BORDER}",
                                background_color=T.BACKGROUND,
                                font_family=T.FONT_BODY, font_size="14px",
                                padding="0 18px",
                                _focus={"border_color": T.PRIMARY, "outline": "none",
                                        "box_shadow": f"0 0 0 3px {T.PRIMARY}22"},
                                _placeholder={"color": T.MUTED_FG},
                            ),
                            rx.button(
                                rx.cond(
                                    ChatState.is_loading,
                                    rx.hstack(rx.spinner(size="2"), rx.text("Wait…"), spacing="2"),
                                    rx.text("Send  ➤", font_family=T.FONT_MONO,
                                            font_size="14px", font_weight="500"),
                                ),
                                on_click=ChatState.send_message,
                                disabled=ChatState.is_loading,
                                height="44px", padding="0 20px",
                                border_radius=T.RADIUS_PILL,
                                background_color=T.PRIMARY,
                                color=T.PRIMARY_FG,
                                cursor="pointer",
                                _hover={"background_color": T.PRIMARY_HOVER},
                                flex_shrink="0",
                                style={"boxShadow": T.SHADOW_PRIMARY},
                            ),
                            spacing="2", width="100%", align="center",
                        ),
                        spacing="2", width="100%",
                    ),
                    padding="12px 16px",
                    background_color=T.CARD,
                    border_top=f"1px solid {T.BORDER}",
                    flex_shrink="0",
                ),

                # ── Status bar ───────────────────────────────────────
                rx.box(
                    rx.hstack(
                        rx.hstack(
                            rx.box(
                                width="8px", height="8px", border_radius="50%",
                                background_color=rx.cond(ChatState.ollama_ready, T.SUCCESS, T.ERROR),
                            ),
                            rx.text(
                                rx.cond(
                                    ChatState.ollama_ready,
                                    rx.cond(ChatState.is_loading, "RAVE is generating a response…", "Ollama  ·  Ready"),
                                    "Ollama  ·  Offline",
                                ),
                                font_family=T.FONT_BODY, font_size="12px", color=T.MUTED_FG,
                            ),
                            spacing="2", align="center",
                        ),
                        rx.spacer(),
                        rx.hstack(
                            rx.hstack(
                                rx.text(ChatState.chunk_count, font_family=T.FONT_MONO,
                                        font_size="13px", font_weight="600", color=T.FG),
                                rx.text("chunks", font_family=T.FONT_BODY,
                                        font_size="12px", color=T.MUTED_FG),
                                spacing="1", align="baseline",
                            ),
                            rx.box(width="1px", height="12px", background_color=T.BORDER),
                            rx.text(ChatState.embed_model_short, font_family=T.FONT_MONO,
                                    font_size="12px", font_weight="500", color=T.PRIMARY),
                            rx.text("·", color=T.MUTED_FG, font_size="12px"),
                            rx.text(ChatState.llm_model_short, font_family=T.FONT_MONO,
                                    font_size="12px", font_weight="500", color="#E07B39"),
                            spacing="2", align="center",
                        ),
                        width="100%", align="center",
                    ),
                    padding="0 16px", height="44px",
                    background_color=T.CARD,
                    border_top=f"1px solid {T.BORDER}",
                    display="flex", align_items="center", flex_shrink="0",
                ),

                spacing="0", width="100%", height="100%", align_items="stretch",
            ),
            width="100%",
            height="calc(100vh - 60px)",
            display="flex",
            flex_direction="column",
            overflow="hidden",
        )
    )
