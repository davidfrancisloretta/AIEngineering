import os

import requests

API_BASE = os.getenv("API_URL", "http://localhost:8000")


class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


def _raise(resp: requests.Response):
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    raise ApiError(detail, resp.status_code)


class ApiClient:
    def __init__(self, token: str | None = None):
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    # --------------------------------------------------
    # Auth
    # --------------------------------------------------
    def login(self, email: str, password: str) -> dict:
        resp = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def register(self, email: str, password: str) -> dict:
        resp = requests.post(f"{API_BASE}/auth/register", json={"email": email, "password": password})
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def me(self) -> dict:
        resp = requests.get(f"{API_BASE}/auth/me", headers=self._headers)
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # Rave API config
    # --------------------------------------------------
    def save_api_key(self, public_key: str, secret_key: str) -> dict:
        resp = requests.post(
            f"{API_BASE}/config/api-key",
            json={"rave_public_key": public_key, "rave_secret_key": secret_key},
            headers=self._headers,
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def get_api_key(self) -> dict | None:
        resp = requests.get(f"{API_BASE}/config/api-key", headers=self._headers)
        if resp.status_code == 404:
            return None
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # Rave data
    # --------------------------------------------------
    def fetch_rave_data(self) -> dict:
        resp = requests.post(f"{API_BASE}/rave/fetch", headers=self._headers, timeout=30)
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def get_transactions(self) -> list:
        resp = requests.get(f"{API_BASE}/rave/transactions", headers=self._headers)
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # Excel upload
    # --------------------------------------------------
    def upload_excel(self, file_bytes: bytes, filename: str) -> dict:
        resp = requests.post(
            f"{API_BASE}/upload/excel",
            files={"file": (filename, file_bytes, "application/octet-stream")},
            headers=self._headers,
            timeout=30,
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # Demo
    # --------------------------------------------------
    def seed_demo_data(self) -> dict:
        resp = requests.post(f"{API_BASE}/demo/seed", headers=self._headers, timeout=15)
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def export_yaml(self) -> str:
        resp = requests.get(f"{API_BASE}/demo/export/yaml", headers=self._headers, timeout=15)
        if not resp.ok:
            _raise(resp)
        return resp.text

    # --------------------------------------------------
    # Campaign metrics (public)
    # --------------------------------------------------
    def get_metrics(self) -> list:
        resp = requests.get(f"{API_BASE}/metrics")
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # Clinical trial data
    # --------------------------------------------------
    def seed_clinical_data(self) -> dict:
        resp = requests.post(
            f"{API_BASE}/clinical/seed", headers=self._headers, timeout=30
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def clear_clinical_data(self) -> None:
        resp = requests.delete(
            f"{API_BASE}/clinical/seed", headers=self._headers, timeout=15
        )
        if not resp.ok:
            _raise(resp)

    def get_studies(self) -> list:
        resp = requests.get(f"{API_BASE}/clinical/studies", headers=self._headers)
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def get_subjects(
        self,
        study_id: int | None = None,
        site_id: str | None = None,
    ) -> list:
        params: dict = {}
        if study_id:
            params["study_id"] = study_id
        if site_id:
            params["site_id"] = site_id
        resp = requests.get(
            f"{API_BASE}/clinical/subjects",
            headers=self._headers,
            params=params,
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def get_visits(self, subject_id: int) -> list:
        resp = requests.get(
            f"{API_BASE}/clinical/visits",
            headers=self._headers,
            params={"subject_id": subject_id},
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def get_forms(self, visit_id: int) -> list:
        resp = requests.get(
            f"{API_BASE}/clinical/forms/{visit_id}", headers=self._headers
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # RAG
    # --------------------------------------------------
    def rag_status(self) -> dict:
        resp = requests.get(
            f"{API_BASE}/rag/status", headers=self._headers, timeout=10
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def rag_ingest(self) -> dict:
        resp = requests.post(
            f"{API_BASE}/rag/ingest", headers=self._headers, timeout=300
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    def rag_chat(self, question: str, top_k: int = 5) -> dict:
        resp = requests.post(
            f"{API_BASE}/rag/chat",
            json={"question": question, "top_k": top_k},
            headers=self._headers,
            timeout=180,
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # Text-to-SQL
    # --------------------------------------------------
    def rag_sql_query(self, question: str) -> dict:
        resp = requests.post(
            f"{API_BASE}/rag/sql-query",
            json={"question": question},
            headers=self._headers,
            timeout=180,
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()

    # --------------------------------------------------
    # ODM XML upload
    # --------------------------------------------------
    def upload_odm(self, file_bytes: bytes, filename: str) -> dict:
        resp = requests.post(
            f"{API_BASE}/clinical/upload-odm",
            files={"file": (filename, file_bytes, "application/xml")},
            headers=self._headers,
            timeout=120,
        )
        if not resp.ok:
            _raise(resp)
        return resp.json()
