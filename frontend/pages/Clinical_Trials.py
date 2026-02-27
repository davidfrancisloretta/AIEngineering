import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.api import ApiClient, ApiError

if "token" not in st.session_state:
    st.error("Please log in first.")
    st.stop()

client = ApiClient(token=st.session_state["token"])

st.title("🏥 Clinical Trials")
st.markdown("**CARDIO-2024** — Phase III Cardiovascular Study | CardioPharm International")
st.markdown("---")

# ── Sidebar: actions ──────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Data Actions")

    # ── ODM XML Upload ─────────────────────────────────────────────────────
    st.markdown("**Upload Rave ODM File**")
    odm_file = st.file_uploader(
        "Choose .xml or .odm file",
        type=["xml", "odm"],
        help="Export from Medidata Rave → Datasets → ClinicalAuditRecords.odm or any standard ODM export",
    )
    if odm_file is not None:
        if st.button("📤 Import ODM Data", use_container_width=True, type="primary"):
            with st.spinner(f"Parsing {odm_file.name} and importing…"):
                try:
                    r = client.upload_odm(odm_file.read(), odm_file.name)
                    st.success(f"✅ {r['message']}")
                    if r.get("warnings"):
                        for w in r["warnings"]:
                            st.warning(f"⚠️ {w}")
                    st.rerun()
                except ApiError as e:
                    st.error(f"❌ {e}")

    st.markdown("---")

    # ── Demo data ──────────────────────────────────────────────────────────
    st.markdown("**Demo Dataset**")
    if st.button("🧬 Seed Demo Data", use_container_width=True):
        with st.spinner("Generating CARDIO-2024 demo dataset…"):
            try:
                r = client.seed_clinical_data()
                st.success(
                    f"✅ Loaded: {r['subjects']} subjects, "
                    f"{r['visits']} visits, {r['forms']} forms"
                )
                st.rerun()
            except ApiError as e:
                st.error(f"❌ {e}")

    if st.button("🔍 Ingest for RAG", use_container_width=True, type="secondary"):
        with st.spinner("Embedding clinical data for AI chat (~200 chunks)…"):
            try:
                r = client.rag_ingest()
                st.success(f"✅ {r['message']}")
            except ApiError as e:
                st.error(f"❌ {e}")

    st.markdown("---")
    if st.button("🗑️ Clear All Data", use_container_width=True):
        with st.spinner("Clearing data…"):
            try:
                client.clear_clinical_data()
                st.success("✅ Clinical data cleared.")
                st.rerun()
            except ApiError as e:
                st.error(f"❌ {e}")

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    studies  = client.get_studies()
    subjects = client.get_subjects()
except ApiError as e:
    st.error(f"Could not load data: {e}")
    st.stop()

if not studies:
    st.info("No clinical data found. Click **Seed Demo Data** in the sidebar to get started.")
    st.stop()

study = studies[0]

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["📋 Study Overview", "👤 Subject Detail", "⚠️ Adverse Events", "🔬 Lab Results"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Study Overview
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(study["study_oid"])
    st.caption(study["protocol_name"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Subjects",   len(subjects))
    c2.metric("Phase",      study.get("phase", "—"))
    c3.metric("Status",     study.get("status", "—"))
    c4.metric("Sponsor",    study.get("sponsor", "—"))

    st.markdown(f"**Therapeutic Area:** {study.get('therapeutic_area', '—')}")
    st.markdown(f"**Objective:** {study.get('objective', '—')}")
    st.markdown("---")

    # Subjects table
    st.subheader("Enrolled Subjects")
    df_subj = pd.DataFrame(subjects)
    if not df_subj.empty:
        # Site filter
        sites = ["All"] + sorted(df_subj["site_name"].dropna().unique().tolist())
        selected_site = st.selectbox("Filter by Site", sites)
        if selected_site != "All":
            df_subj = df_subj[df_subj["site_name"] == selected_site]

        # Status colour map
        status_map = {"Enrolled": "🟢", "Completed": "✅", "Withdrawn": "🔴"}
        df_display = df_subj[
            ["subject_key", "site_name", "age", "sex", "race", "enrollment_date", "status"]
        ].copy()
        df_display["status"] = df_display["status"].map(
            lambda s: f"{status_map.get(s, '')} {s}"
        )
        df_display.columns = [
            "Subject Key", "Site", "Age", "Sex", "Race", "Enrolled", "Status"
        ]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Site distribution chart
        site_counts = df_subj["site_name"].value_counts().reset_index()
        site_counts.columns = ["Site", "Subjects"]
        fig = px.bar(
            site_counts, x="Site", y="Subjects",
            title="Subjects by Site", color="Site",
        )
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Subject Detail
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Subject Detail")
    if not subjects:
        st.info("No subjects loaded.")
    else:
        subj_options = {s["subject_key"]: s for s in subjects}
        selected_key = st.selectbox("Select Subject", list(subj_options.keys()))
        subj = subj_options[selected_key]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Age",    subj.get("age", "—"))
        c2.metric("Sex",    subj.get("sex", "—"))
        c3.metric("Site",   subj.get("site_name", "—"))
        c4.metric("Status", subj.get("status", "—"))

        try:
            visits = client.get_visits(subj["id"])
        except ApiError as e:
            st.error(f"Could not load visits: {e}")
            visits = []

        if visits:
            st.markdown(f"**{len(visits)} visit(s) recorded**")
            for v in visits:
                with st.expander(
                    f"📅 {v['visit_name']} — {v.get('visit_date', 'N/A')}  ·  {v.get('status', '')}",
                    expanded=False,
                ):
                    try:
                        forms = client.get_forms(v["id"])
                    except ApiError:
                        forms = []

                    form_map = {f["form_oid"]: json.loads(f["data_json"] or "{}") for f in forms}

                    # Vital Signs
                    vs = form_map.get("VS", {})
                    if vs:
                        st.markdown("**Vital Signs**")
                        vc1, vc2, vc3, vc4 = st.columns(4)
                        vc1.metric("Heart Rate",   f"{vs.get('heart_rate', '—')} bpm")
                        vc2.metric("BP",           f"{vs.get('systolic_bp', '—')}/{vs.get('diastolic_bp', '—')} mmHg")
                        vc3.metric("Temp",         f"{vs.get('temperature', '—')} °C")
                        vc4.metric("Weight",       f"{vs.get('weight', '—')} kg")

                    # Adverse Events
                    ae_events = form_map.get("AE", {}).get("events", [])
                    if ae_events:
                        st.markdown("**Adverse Events**")
                        ae_df = pd.DataFrame(ae_events)
                        ae_df.columns = [c.replace("_", " ").title() for c in ae_df.columns]
                        st.dataframe(ae_df, use_container_width=True, hide_index=True)

                    # Concomitant Medications
                    meds = form_map.get("CM", {}).get("medications", [])
                    if meds:
                        st.markdown("**Concomitant Medications**")
                        st.markdown(", ".join(meds))
        else:
            st.info("No visits found for this subject.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Adverse Events
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Adverse Events — All Subjects")
    all_ae = []

    for subj in subjects:
        try:
            visits = client.get_visits(subj["id"])
            for v in visits:
                forms = client.get_forms(v["id"])
                form_map = {f["form_oid"]: json.loads(f["data_json"] or "{}") for f in forms}
                for ae in form_map.get("AE", {}).get("events", []):
                    all_ae.append({
                        "Subject":      subj["subject_key"],
                        "Site":         subj["site_name"],
                        "Visit":        v["visit_name"],
                        "Term":         ae.get("term"),
                        "Severity":     ae.get("severity"),
                        "Relationship": ae.get("relationship"),
                        "Outcome":      ae.get("outcome"),
                    })
        except ApiError:
            pass

    if all_ae:
        ae_df = pd.DataFrame(all_ae)
        st.metric("Total AEs Reported", len(ae_df))

        c1, c2 = st.columns(2)
        with c1:
            sev_counts = ae_df["Severity"].value_counts().reset_index()
            sev_counts.columns = ["Severity", "Count"]
            fig_sev = px.bar(
                sev_counts, x="Severity", y="Count",
                color="Severity",
                title="AEs by Severity",
                color_discrete_map={"Mild": "#4CAF50", "Moderate": "#FF9800", "Severe": "#F44336"},
            )
            st.plotly_chart(fig_sev, use_container_width=True)
        with c2:
            rel_counts = ae_df["Relationship"].value_counts().reset_index()
            rel_counts.columns = ["Relationship", "Count"]
            fig_rel = px.pie(
                rel_counts, names="Relationship", values="Count",
                title="Drug Relationship Distribution",
            )
            st.plotly_chart(fig_rel, use_container_width=True)

        term_counts = ae_df["Term"].value_counts().reset_index()
        term_counts.columns = ["Term", "Count"]
        fig_terms = px.bar(
            term_counts, x="Count", y="Term", orientation="h",
            title="AE Terms by Frequency",
            color="Count", color_continuous_scale="Reds",
        )
        st.plotly_chart(fig_terms, use_container_width=True)

        st.dataframe(ae_df, use_container_width=True, hide_index=True)
    else:
        st.info("No adverse events found. Seed demo data first.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Lab Results
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Laboratory Results")
    all_labs = []

    for subj in subjects:
        try:
            visits = client.get_visits(subj["id"])
            for v in visits:
                forms = client.get_forms(v["id"])
                form_map = {f["form_oid"]: json.loads(f["data_json"] or "{}") for f in forms}
                for result in form_map.get("LB", {}).get("results", []):
                    all_labs.append({
                        "Subject":   subj["subject_key"],
                        "Visit":     v["visit_name"],
                        "Test":      result.get("name"),
                        "Code":      result.get("test"),
                        "Value":     result.get("value"),
                        "Unit":      result.get("unit"),
                        "Flag":      result.get("flag"),
                    })
        except ApiError:
            pass

    if all_labs:
        lab_df = pd.DataFrame(all_labs)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Lab Results", len(lab_df))
        abnormal_count = len(lab_df[lab_df["Flag"] != "N"])
        c2.metric("Abnormal Results", abnormal_count)
        c3.metric(
            "Abnormal Rate",
            f"{abnormal_count / len(lab_df) * 100:.1f}%"
        )

        # Flag colour coding
        def _flag_colour(flag):
            if flag in ("HH", "LL"):
                return "background-color: #ffcccc"
            elif flag in ("H", "L"):
                return "background-color: #fff3cd"
            return ""

        # Filter to abnormal only
        show_abnormal = st.checkbox("Show abnormal results only", value=False)
        display_df = lab_df[lab_df["Flag"] != "N"] if show_abnormal else lab_df

        # Test filter
        test_options = ["All"] + sorted(lab_df["Test"].dropna().unique().tolist())
        selected_test = st.selectbox("Filter by Test", test_options)
        if selected_test != "All":
            display_df = display_df[display_df["Test"] == selected_test]

        st.dataframe(
            display_df.style.applymap(_flag_colour, subset=["Flag"]),
            use_container_width=True,
            hide_index=True,
        )

        # Flag distribution chart
        flag_counts = lab_df["Flag"].value_counts().reset_index()
        flag_counts.columns = ["Flag", "Count"]
        fig_flags = px.bar(
            flag_counts, x="Flag", y="Count",
            color="Flag",
            title="Lab Result Flags Distribution",
            color_discrete_map={"N": "#4CAF50", "H": "#FF9800", "L": "#2196F3",
                                 "HH": "#F44336", "LL": "#9C27B0"},
        )
        st.plotly_chart(fig_flags, use_container_width=True)
    else:
        st.info("No lab results found. Seed demo data first.")
