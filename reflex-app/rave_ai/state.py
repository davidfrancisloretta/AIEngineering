"""
Reflex State Management for RAVE AI
All state is centralized here
"""
import reflex as rx
from typing import List, Dict, Any, Optional
from rave_ai.services.api_client import ApiClient, ApiError


# ════════════════════════════════════════════════════════════════════════════
# GLOBAL APP STATE
# ════════════════════════════════════════════════════════════════════════════

class AppState(rx.State):
    """Global application state"""

    # Auth
    token: str = ""
    user_email: str = ""
    is_authenticated: bool = False
    login_error: str = ""

    # UI
    sidebar_open: bool = True
    current_page: str = ""

    @property
    def api_client(self) -> ApiClient:
        """Get API client with current token"""
        return ApiClient(token=self.token if self.is_authenticated else None)

    async def login(self, email: str, password: str) -> bool:
        """Login with email and password"""
        if not email or not password:
            self.login_error = "Email and password required"
            return False

        try:
            result = await self.api_client.login(email, password)
            self.token = result.get("access_token", "")
            self.user_email = email
            self.is_authenticated = True
            self.login_error = ""
            return True
        except ApiError as e:
            self.login_error = str(e)
            self.is_authenticated = False
            return False

    def logout(self):
        """Logout and reset state"""
        self.token = ""
        self.user_email = ""
        self.is_authenticated = False
        self.login_error = ""
        return rx.redirect("/signed-out")

    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        self.sidebar_open = not self.sidebar_open

    def index_redirect(self):
        """Root page: send to dashboard if authed, else login"""
        if self.is_authenticated:
            return rx.redirect("/dashboard")
        return rx.redirect("/login")

    def check_auth(self):
        """Redirect unauthenticated users to login"""
        if not self.is_authenticated:
            return rx.redirect("/login")


# ════════════════════════════════════════════════════════════════════════════
# LOGIN STATE
# ════════════════════════════════════════════════════════════════════════════

class LoginState(AppState):
    """Login page state"""
    email: str = ""
    password: str = ""
    is_loading: bool = False
    show_password: bool = False

    def set_email(self, email: str):
        self.email = email

    def set_password(self, password: str):
        self.password = password

    def toggle_show_password(self):
        self.show_password = not self.show_password

    async def handle_login(self):
        """Handle login button click"""
        self.is_loading = True
        try:
            success = await self.login(self.email, self.password)
            if success:
                return rx.redirect("/")
        finally:
            self.is_loading = False


# ════════════════════════════════════════════════════════════════════════════
# ONBOARDING STATE
# ════════════════════════════════════════════════════════════════════════════

class OnboardingState(AppState):
    """Onboarding wizard state"""

    # Step tracking
    step: int = 0  # 0: seed, 1: ingest, 2: chat

    # Seed state
    seed_done: bool = False
    seed_loading: bool = False
    seed_error: str = ""

    # Ingest state
    ingest_running: bool = False
    ingest_done: bool = False
    ingest_progress: int = 0
    ingest_error: str = ""
    chunk_count: int = 0

    async def load_status(self):
        """Auto-detect progress from existing data"""
        try:
            # Check for chunks
            rag_st = await self.api_client.rag_status()
            self.chunk_count = rag_st.get("chunk_count", 0)

            # Check for subjects
            subjects = await self.api_client.get_subjects()
            if len(subjects) > 0:
                self.seed_done = True
                if self.step == 0:
                    self.step = 1

            # Check for embeddings
            if self.chunk_count > 0:
                self.ingest_done = True
                if self.step <= 1:
                    self.step = 2
        except ApiError:
            pass  # Silently fail - backend might not be ready

    async def seed_demo_data(self):
        """Seed demo clinical data"""
        self.seed_loading = True
        self.seed_error = ""
        try:
            result = await self.api_client.seed_clinical_data()
            self.seed_done = True
            self.step = 1  # Auto-advance
            self.seed_error = ""
        except ApiError as e:
            self.seed_error = str(e)
        finally:
            self.seed_loading = False

    def go_to_step(self, step: int):
        """Navigate to a specific step"""
        self.step = step

    async def start_ingest(self):
        """Start RAG ingestion process"""
        self.ingest_running = True
        self.ingest_error = ""
        self.ingest_progress = 0

        try:
            # Kick off ingestion
            await self.api_client.rag_ingest()

            # Poll for progress
            import asyncio
            while self.ingest_running:
                try:
                    status = await self.api_client.rag_ingest_status()
                    s = status.get("status", "idle")
                    done = status.get("done", 0)
                    total = max(status.get("total", 1), 1)

                    # Update progress
                    self.ingest_progress = int(100 * done / total)

                    if s == "done":
                        self.ingest_done = True
                        self.ingest_running = False
                        self.chunk_count = status.get("chunks_created", 0)
                        self.step = 2  # Auto-advance
                        break
                    elif s == "error":
                        self.ingest_error = status.get("error", "Unknown error")
                        self.ingest_running = False
                        break

                    # Poll every 2 seconds
                    await asyncio.sleep(2)
                except ApiError as e:
                    self.ingest_error = str(e)
                    self.ingest_running = False
                    break
        except ApiError as e:
            self.ingest_error = str(e)
            self.ingest_running = False


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATE
# ════════════════════════════════════════════════════════════════════════════

class DashboardState(AppState):
    """Dashboard analytics state — flat vars required by Reflex reactive system"""

    # Flat summary vars (no nested dict — Reflex can't call .get() on state vars)
    total_queries: int = 0
    vector_queries: int = 0
    sql_queries: int = 0
    avg_response_ms: float = 0.0
    thumbs_up: int = 0
    thumbs_down: int = 0
    unrated: int = 0

    daily_stats: List[Dict[str, Any]] = []
    top_questions: List[Dict[str, Any]] = []
    is_loading: bool = False
    load_error: str = ""

    async def load_data(self):
        """Load all dashboard data"""
        self.is_loading = True
        self.load_error = ""
        try:
            summary = await self.api_client.get_rag_analytics_summary()
            daily = await self.api_client.get_rag_analytics_daily()
            top = await self.api_client.get_rag_analytics_top_questions()

            s = summary or {}
            self.total_queries = s.get("total_queries", 0)
            self.vector_queries = s.get("vector_queries", 0)
            self.sql_queries = s.get("sql_queries", 0)
            self.avg_response_ms = s.get("avg_response_ms", 0.0)
            self.thumbs_up = s.get("thumbs_up", 0)
            self.thumbs_down = s.get("thumbs_down", 0)
            self.unrated = s.get("unrated", 0)
            self.daily_stats = daily or []
            self.top_questions = top or []
        except ApiError as e:
            self.load_error = str(e)
        finally:
            self.is_loading = False

    @rx.var
    def avg_response_s(self) -> str:
        """Average response time in seconds, formatted to 2dp."""
        if self.avg_response_ms <= 0:
            return "—"
        return f"{self.avg_response_ms / 1000:.2f}s"

    @rx.var
    def has_daily_stats(self) -> bool:
        return len(self.daily_stats) > 0

    @rx.var
    def has_top_questions(self) -> bool:
        return len(self.top_questions) > 0


# ════════════════════════════════════════════════════════════════════════════
# CLINICAL TRIALS STATE
# ════════════════════════════════════════════════════════════════════════════

class TrialDataState(AppState):
    """Clinical trials data state"""

    studies: List[Dict[str, Any]] = []
    subjects: List[Dict[str, Any]] = []
    search_query: str = ""
    site_filter: str = "All"
    is_loading: bool = False
    load_error: str = ""

    # Flat study fields (avoids nested dict access in Reflex vars)
    study_oid: str = ""
    study_phase: str = ""
    study_status_text: str = ""
    study_sponsor: str = ""
    study_protocol: str = ""
    study_therapeutic_area: str = ""
    study_objective: str = ""

    # Seed action
    seed_loading: bool = False
    seed_message: str = ""

    # Selected subject details
    selected_subject_id: int = -1
    selected_subject_key: str = ""
    selected_subject_age: str = ""
    selected_subject_sex: str = ""
    selected_subject_race: str = ""
    selected_subject_site: str = ""
    selected_subject_status: str = ""
    selected_subject_enrolled: str = ""

    # Subject visit/form data
    subject_visits: List[Dict[str, Any]] = []
    subject_vital_signs: List[Dict[str, Any]] = []
    subject_ae_entries: List[Dict[str, Any]] = []
    subject_lab_entries: List[Dict[str, Any]] = []
    subject_meds: List[str] = []
    subject_loading: bool = False

    # Controlled tab
    current_tab: str = "overview"

    def set_current_tab(self, tab: str):
        self.current_tab = tab

    @rx.var
    def ae_count(self) -> int:
        return len(self.subject_ae_entries)

    @rx.var
    def lab_count(self) -> int:
        return len(self.subject_lab_entries)

    @rx.var
    def has_vital_signs(self) -> bool:
        return len(self.subject_vital_signs) > 0

    @rx.var
    def has_ae_entries(self) -> bool:
        return len(self.subject_ae_entries) > 0

    @rx.var
    def has_meds(self) -> bool:
        return len(self.subject_meds) > 0

    def set_search_query(self, query: str):
        self.search_query = query

    def set_site_filter(self, site: str):
        self.site_filter = site

    @rx.var(cache=False)
    def filtered_subjects(self) -> List[Dict[str, Any]]:
        result = self.subjects
        if self.site_filter and self.site_filter != "All":
            result = [s for s in result if s.get("site_name", "") == self.site_filter]
        if self.search_query:
            q = self.search_query.lower()
            result = [s for s in result if any(q in str(v).lower() for v in s.values())]
        return result

    @rx.var
    def has_subjects(self) -> bool:
        return len(self.subjects) > 0

    @rx.var
    def filtered_count(self) -> int:
        return len(self.filtered_subjects)

    @rx.var
    def subject_count(self) -> int:
        return len(self.subjects)

    @rx.var
    def unique_sites(self) -> List[str]:
        sites = sorted({s.get("site_name", "") for s in self.subjects if s.get("site_name")})
        return ["All"] + sites

    async def load_data(self):
        """Load trials data"""
        self.is_loading = True
        self.load_error = ""
        try:
            studies = await self.api_client.get_studies()
            subjects = await self.api_client.get_subjects()
            self.studies = studies or []
            self.subjects = subjects or []
            if self.studies:
                s = self.studies[0]
                self.study_oid = s.get("study_oid", "")
                self.study_phase = s.get("phase", "")
                self.study_status_text = s.get("status", "")
                self.study_sponsor = s.get("sponsor", "")
                self.study_protocol = s.get("protocol_name", "")
                self.study_therapeutic_area = s.get("therapeutic_area", "")
                self.study_objective = s.get("objective", "")
        except ApiError as e:
            self.load_error = str(e)
        finally:
            self.is_loading = False

    async def seed_data(self):
        """Seed demo data then reload"""
        self.seed_loading = True
        self.seed_message = ""
        self.load_error = ""
        yield
        try:
            result = await self.api_client.seed_clinical_data()
            n = result.get("subjects", 0)
            v = result.get("visits", 0)
            self.seed_message = f"✅ Loaded {n} subjects, {v} visits"
            # Reload data
            studies = await self.api_client.get_studies()
            subjects = await self.api_client.get_subjects()
            self.studies = studies or []
            self.subjects = subjects or []
            if self.studies:
                s = self.studies[0]
                self.study_oid = s.get("study_oid", "")
                self.study_phase = s.get("phase", "")
                self.study_status_text = s.get("status", "")
                self.study_sponsor = s.get("sponsor", "")
                self.study_protocol = s.get("protocol_name", "")
                self.study_therapeutic_area = s.get("therapeutic_area", "")
                self.study_objective = s.get("objective", "")
        except ApiError as e:
            self.load_error = str(e)
        finally:
            self.seed_loading = False

    async def select_subject(self, subject_id: int):
        """Click a subject row → load their visits/forms and switch to detail tab."""
        import json as _json

        # Pull subject info from already-loaded list
        self.selected_subject_id = subject_id
        for s in self.subjects:
            if s.get("id") == subject_id:
                self.selected_subject_key = s.get("subject_key", "")
                self.selected_subject_age = str(s.get("age", ""))
                self.selected_subject_sex = s.get("sex", "")
                self.selected_subject_race = s.get("race", "")
                self.selected_subject_site = s.get("site_name", "")
                self.selected_subject_status = s.get("status", "")
                self.selected_subject_enrolled = str(s.get("enrollment_date", ""))
                break

        # Reset and show loading while switching tabs
        self.subject_loading = True
        self.subject_visits = []
        self.subject_vital_signs = []
        self.subject_ae_entries = []
        self.subject_lab_entries = []
        self.subject_meds = []
        self.current_tab = "detail"
        yield  # flush → switch tab + show spinner

        try:
            visits = await self.api_client.get_visits(subject_id)
            self.subject_visits = visits

            ae_list: List[Dict[str, Any]] = []
            lab_list: List[Dict[str, Any]] = []
            vs_list: List[Dict[str, Any]] = []
            meds_set: set = set()

            for visit in visits:
                vid = visit.get("id", 0)
                vname = visit.get("visit_name", "")
                vdate = str(visit.get("visit_date", ""))
                forms = await self.api_client.get_forms(vid)
                for form in forms:
                    fname = form.get("form_name", "")
                    try:
                        raw = form.get("data_json", "{}")
                        data = _json.loads(raw) if isinstance(raw, str) else (raw or {})
                    except Exception:
                        data = {}

                    if fname == "VS":
                        vs_list.append({
                            "visit": vname, "date": vdate,
                            "hr": str(data.get("heart_rate", "")),
                            "sbp": str(data.get("systolic_bp", "")),
                            "dbp": str(data.get("diastolic_bp", "")),
                            "temp": str(data.get("temperature", "")),
                            "weight": str(data.get("weight", "")),
                        })
                    elif fname == "AE":
                        for ev in data.get("events", []):
                            ae_list.append({
                                "visit": vname, "date": vdate,
                                "term": ev.get("term", ""),
                                "severity": ev.get("severity", ""),
                                "relationship": ev.get("relationship", ""),
                                "outcome": ev.get("outcome", ""),
                            })
                    elif fname == "LB":
                        for r in data.get("results", []):
                            lab_list.append({
                                "visit": vname, "date": vdate,
                                "test": r.get("test", ""),
                                "name": r.get("name", ""),
                                "value": str(r.get("value", "")),
                                "unit": r.get("unit", ""),
                                "flag": r.get("flag", "N"),
                            })
                    elif fname == "CM":
                        meds_set.update(data.get("medications", []))

            self.subject_vital_signs = vs_list
            self.subject_ae_entries = ae_list
            self.subject_lab_entries = lab_list
            self.subject_meds = sorted(meds_set)
        except Exception:
            pass
        finally:
            self.subject_loading = False


# ════════════════════════════════════════════════════════════════════════════
# RAG CHAT STATE
# ════════════════════════════════════════════════════════════════════════════

class ChatState(AppState):
    """RAG Chat state"""

    messages: List[Dict[str, Any]] = []
    input_value: str = ""
    pending_question: str = ""
    is_loading: bool = False
    chat_error: str = ""

    # Status
    ollama_ready: bool = False
    chunk_count: int = 0
    embed_model: str = "unknown"
    llm_model: str = "unknown"

    @rx.var
    def has_messages(self) -> bool:
        return len(self.messages) > 0

    @rx.var
    def no_messages(self) -> bool:
        return len(self.messages) == 0

    @rx.var
    def embed_model_short(self) -> str:
        if ":" in self.embed_model:
            return self.embed_model.split(":")[0]
        return self.embed_model

    @rx.var
    def llm_model_short(self) -> str:
        if ":" in self.llm_model:
            return self.llm_model.split(":")[0]
        return self.llm_model

    def set_input_value(self, value: str):
        """Update chat input"""
        self.input_value = value

    def clear_chat(self):
        """Clear all messages"""
        self.messages = []
        self.input_value = ""
        self.chat_error = ""

    async def load_status(self):
        """Load RAG system status"""
        try:
            status = await self.api_client.rag_status()
            self.ollama_ready = status.get("ollama_ready", False)
            self.chunk_count = status.get("chunk_count", 0)
            self.embed_model = status.get("embed_model", "unknown")
            self.llm_model = status.get("llm_model", "unknown")
        except ApiError as e:
            self.chat_error = f"Status error: {str(e)}"

    async def _call_rag(self, question: str):
        """Private helper — NOT a Reflex event handler (prefixed _).
        Calls the API and appends the assistant reply. Caller must set
        is_loading and yield before calling this."""
        try:
            result = await self.api_client.rag_chat(question, top_k=5)
            self.messages.append({
                "role": "assistant",
                "content": result.get("answer", "No response"),
                "sources": result.get("sources", []),
                "log_id": result.get("log_id", -1),
            })
        except ApiError as e:
            self.messages.append({
                "role": "assistant",
                "content": f"❌ Error: {str(e)}",
                "sources": [],
                "log_id": -1,
            })
            self.chat_error = str(e)
        finally:
            self.is_loading = False

    async def send_message(self):
        """Send chat message from input box (Enter or Send button)"""
        if not self.input_value.strip() or self.is_loading:
            return
        question = self.input_value.strip()
        self.input_value = ""
        self.messages.append({"role": "user", "content": question,
                               "sources": [], "log_id": -1})
        self.is_loading = True
        self.chat_error = ""
        yield  # flush loading state to frontend before awaiting API
        await self._call_rag(question)

    def set_pending_question(self, question: str):
        """Store a suggested question to send (sync, no yield needed)"""
        self.pending_question = question

    async def send_pending_question(self):
        """Send the stored pending_question. No-arg handler avoids partial/generator conflict."""
        question = self.pending_question
        self.pending_question = ""
        if not question or self.is_loading:
            return
        self.messages.append({"role": "user", "content": question,
                               "sources": [], "log_id": -1})
        self.is_loading = True
        self.chat_error = ""
        yield  # flush loading state to frontend before awaiting API
        await self._call_rag(question)

    async def handle_key_down(self, key: str):
        """Send on Enter key press in the input box"""
        if key != "Enter" or not self.input_value.strip() or self.is_loading:
            return
        question = self.input_value.strip()
        self.input_value = ""
        self.messages.append({"role": "user", "content": question,
                               "sources": [], "log_id": -1})
        self.is_loading = True
        self.chat_error = ""
        yield  # flush loading state to frontend before awaiting API
        await self._call_rag(question)

    async def submit_feedback(self, log_id: int, rating: int):
        """Submit thumbs up (1) or thumbs down (-1) feedback"""
        try:
            await self.api_client.rag_feedback(log_id, rating)
        except ApiError:
            pass


# ════════════════════════════════════════════════════════════════════════════
# SETTINGS STATE
# ════════════════════════════════════════════════════════════════════════════

class SettingsState(AppState):
    """Settings page state"""

    auto_scale_enabled: bool = False
    theme: str = "dark"

    def toggle_auto_scale(self, value: bool):
        self.auto_scale_enabled = value

    def set_theme(self, theme: str):
        self.theme = theme
        return rx.set_color_mode(theme)


# ════════════════════════════════════════════════════════════════════════════
# ODM UPLOAD STATE
# ════════════════════════════════════════════════════════════════════════════

class OdmUploadState(AppState):
    """ODM XML file upload state"""
    is_uploading: bool = False
    upload_done: bool = False
    upload_error: str = ""
    upload_result: str = ""
    selected_filename: str = ""

    # Medidata API Key
    medi_api_key: str = ""
    medi_api_key_saved: bool = False
    medi_api_key_error: str = ""
    medi_show_key: bool = False

    def set_medi_api_key(self, value: str):
        self.medi_api_key = value
        self.medi_api_key_saved = False
        self.medi_api_key_error = ""

    def toggle_medi_show_key(self):
        self.medi_show_key = not self.medi_show_key

    def save_medi_api_key(self):
        """Validate and save the Medidata API key"""
        key = self.medi_api_key.strip()
        if not key:
            self.medi_api_key_error = "API key cannot be empty"
            self.medi_api_key_saved = False
            return
        if len(key) < 8:
            self.medi_api_key_error = "API key seems too short — please check your key"
            self.medi_api_key_saved = False
            return
        self.medi_api_key = key
        self.medi_api_key_saved = True
        self.medi_api_key_error = ""

    def clear_medi_api_key(self):
        self.medi_api_key = ""
        self.medi_api_key_saved = False
        self.medi_api_key_error = ""

    async def handle_upload(self, files: list[rx.UploadFile]):
        if not files:
            return
        self.is_uploading = True
        self.upload_done = False
        self.upload_error = ""
        self.upload_result = ""
        yield
        try:
            f = files[0]
            self.selected_filename = f.filename
            data = await f.read()
            result = await self.api_client.upload_odm(data, f.filename)
            subjects = result.get("subjects_created", 0)
            studies = result.get("studies_created", 0)
            self.upload_result = (
                f"Imported {studies} study, {subjects} subjects from {f.filename}"
            )
            self.upload_done = True
        except ApiError as e:
            self.upload_error = str(e)
        except Exception as e:
            self.upload_error = f"Unexpected error: {e}"
        finally:
            self.is_uploading = False

    def clear_upload(self):
        self.upload_done = False
        self.upload_error = ""
        self.upload_result = ""
        self.selected_filename = ""
