"""
Stub client for live Medidata Rave Web Services (RWS) connection via rwslib.

Currently raises NotImplementedError — demo data is used instead.
This module documents the rwslib API surface so the live connection
can be implemented in a future sprint when Rave credentials are available.

Future implementation pattern:
    pip install rwslib

    from rwslib import RWSConnection
    from rwslib.rws_requests import (
        MetadataStudiesRequest,
        StudySubjectsRequest,
        FormDataRequest,
    )

    conn = RWSConnection(base_url, username, password)

    # List all studies accessible to this user
    studies = conn.send_request(MetadataStudiesRequest())

    # Get subjects for a study
    subjects = conn.send_request(StudySubjectsRequest(study_oid, environment))

    # Get clinical data for a form
    data = conn.send_request(
        FormDataRequest(study_oid, environment, dataset_type="regular", form_oid="VS")
    )

Authentication options:
    Basic Auth:  RWSConnection(url, username, password)
    MAuth:       RWSConnection(url, auth=MAuth(app_uuid, private_key))

Reference documentation:
    - RWS Inbound v1.0.2 User Guide (CDISC ODM XML over HTTP)
    - rwslib Python library documentation (Release 1.2.3)
    - https://github.com/mdsol/rwslib
"""
from typing import Optional


class RaveClientConfig:
    """Configuration for a live Medidata Rave connection."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        virtual_directory: str = "RaveWebServices",
    ):
        self.base_url          = base_url
        self.username          = username
        self.password          = password
        self.virtual_directory = virtual_directory


def fetch_study_list(config: RaveClientConfig) -> list[dict]:
    """Fetch list of studies accessible to the configured user."""
    raise NotImplementedError(
        "Live Rave connection not yet configured. "
        "Use the Clinical Trials page to load demo data instead."
    )


def fetch_subjects(
    config: RaveClientConfig,
    study_oid: str,
    environment: str = "Prod",
) -> list[dict]:
    """Fetch subjects enrolled in a study from Rave."""
    raise NotImplementedError(
        "Live Rave connection not yet configured. "
        "Use the Clinical Trials page to load demo data instead."
    )


def fetch_clinical_data(
    config: RaveClientConfig,
    study_oid: str,
    subject_key: Optional[str] = None,
    form_oid: Optional[str] = None,
) -> dict:
    """
    Fetch full ODM clinical data for a study (or specific subject/form).
    Returns CDISC ODM XML parsed into a Python dict.
    """
    raise NotImplementedError(
        "Live Rave connection not yet configured. "
        "Use the Clinical Trials page to load demo data instead."
    )


def fetch_global_library(
    config: RaveClientConfig,
    library_name: str,
) -> dict:
    """Fetch a Global Library volume (shared study design components)."""
    raise NotImplementedError(
        "Live Rave connection not yet configured. "
        "Use the Clinical Trials page to load demo data instead."
    )
