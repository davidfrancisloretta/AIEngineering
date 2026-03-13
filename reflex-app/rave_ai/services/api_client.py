"""
Async API Client for RAVE AI Backend (FastAPI)
"""
import json
import httpx
from typing import Optional, Dict, List, Any
from rave_ai.config import API_BASE, API_TIMEOUT


class ApiError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    """Async HTTP client for FastAPI backend"""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = API_BASE
        self.timeout = API_TIMEOUT
        self._headers = self._build_headers()

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with auth token if present"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make async HTTP request"""
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.timeout

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=self._headers)
                elif method == "POST":
                    response = await client.post(url, json=data, headers=self._headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=self._headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if not response.is_success:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except Exception:
                        error_detail = response.text
                    raise ApiError(error_detail, response.status_code)

                return response.json()
            except httpx.RequestError as e:
                raise ApiError(f"Connection error: {str(e)}")

    async def _stream_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ):
        """Make streaming async HTTP request"""
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    method,
                    url,
                    json=data,
                    headers=self._headers
                ) as response:
                    if not response.is_success:
                        error_detail = (await response.aread()).decode()
                        raise ApiError(error_detail, response.status_code)

                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                yield json.loads(line)
                            except json.JSONDecodeError:
                                pass
            except httpx.RequestError as e:
                raise ApiError(f"Connection error: {str(e)}")

    # ────────────────────────────────────────────────────────────
    # Auth Endpoints
    # ────────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> Dict:
        """Login and get JWT token"""
        return await self._request("POST", "/auth/login", {
            "email": email,
            "password": password
        })

    async def register(self, email: str, password: str) -> Dict:
        """Register new user"""
        return await self._request("POST", "/auth/register", {
            "email": email,
            "password": password
        })

    async def me(self) -> Dict:
        """Get current user info"""
        return await self._request("GET", "/auth/me")

    # ────────────────────────────────────────────────────────────
    # Clinical Trial Endpoints
    # ────────────────────────────────────────────────────────────

    async def get_subjects(self) -> List[Dict]:
        """Get all subjects — returns a list directly"""
        response = await self._request("GET", "/clinical/subjects")
        return response if isinstance(response, list) else response.get("subjects", [])

    async def get_studies(self) -> List[Dict]:
        """Get all studies"""
        response = await self._request("GET", "/clinical/studies")
        return response.get("studies", []) if isinstance(response, dict) else response

    async def seed_clinical_data(self) -> Dict:
        """Seed demo clinical data"""
        return await self._request("POST", "/clinical/seed")

    async def upload_odm(self, file_bytes: bytes, filename: str) -> Dict:
        """Upload an ODM XML file to the backend for parsing and ingestion."""
        url = f"{self.base_url}/clinical/upload-odm"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                files={"file": (filename, file_bytes, "application/xml")},
                headers=headers,
            )
            if not response.is_success:
                try:
                    detail = response.json().get("detail", response.text)
                except Exception:
                    detail = response.text
                raise ApiError(f"ODM upload failed: {detail}")
            return response.json()

    async def get_visits(self, subject_id: int) -> List[Dict]:
        """Get visits for a subject"""
        response = await self._request("GET", f"/clinical/visits?subject_id={subject_id}")
        return response.get("visits", []) if isinstance(response, dict) else response

    async def get_forms(self, visit_id: int) -> List[Dict]:
        """Get forms for a visit"""
        response = await self._request("GET", f"/clinical/forms/{visit_id}")
        return response if isinstance(response, list) else response.get("forms", [])

    # ────────────────────────────────────────────────────────────
    # RAG Endpoints
    # ────────────────────────────────────────────────────────────

    async def rag_status(self) -> Dict:
        """Get RAG system status"""
        return await self._request("GET", "/rag/status")

    async def rag_ingest(self) -> Dict:
        """Start background RAG ingestion"""
        return await self._request("POST", "/rag/ingest")

    async def rag_ingest_status(self) -> Dict:
        """Get RAG ingestion progress"""
        return await self._request("GET", "/rag/ingest-status")

    async def rag_chat(self, question: str, top_k: int = 5) -> Dict:
        """Non-streaming RAG chat. Extended timeout for first call (model download)."""
        return await self._request("POST", "/rag/chat", {
            "question": question,
            "top_k": top_k
        }, timeout=300)

    async def rag_chat_stream(self, question: str, top_k: int = 5):
        """Streaming RAG chat (yields tokens)"""
        async for chunk in self._stream_request("POST", "/rag/chat-stream", {
            "question": question,
            "top_k": top_k
        }):
            yield chunk

    async def rag_feedback(self, log_id: int, rating: int) -> Dict:
        """Submit thumbs up (1) or thumbs down (-1) feedback for a query"""
        return await self._request("POST", f"/rag/feedback/{log_id}", {
            "feedback": rating
        })

    # ────────────────────────────────────────────────────────────
    # Analytics Endpoints
    # ────────────────────────────────────────────────────────────

    async def get_rag_analytics_summary(self) -> Dict:
        """Get RAG analytics summary"""
        return await self._request("GET", "/rag/analytics/summary")

    async def get_rag_analytics_daily(self) -> List[Dict]:
        """Get daily RAG analytics"""
        response = await self._request("GET", "/rag/analytics/daily")
        return response if isinstance(response, list) else response.get("data", [])

    async def get_rag_analytics_top_questions(self) -> List[Dict]:
        """Get top questions"""
        response = await self._request("GET", "/rag/analytics/top-questions")
        return response if isinstance(response, list) else response.get("data", [])
