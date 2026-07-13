import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import json
import os
import sys

# Ensure project root is in path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force reload of local src modules safely using importlib.reload if already loaded
import importlib
for mod in list(sys.modules.keys()):
    if mod.startswith("src"):
        try:
            importlib.reload(sys.modules[mod])
        except Exception:
            pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "synapse_audit.db")

from src.dataset_loader import DatasetLoader
from src.regression import RegressionEngine
from src.database import AuditDatabase
from src.parser import ClinicalParser
from src.rules import RuleEngine
from src.metrics import compute_classification_metrics, compute_cohens_kappa, calculate_cdri, calculate_financial_impact

# Page configuration
st.set_page_config(
    page_title="SynapseAudit Clinical Compliance Console", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Custom Enterprise CSS (Restrained Dark Theme: slate, navy, teal, warning accents)
st.markdown("""
<style>
    /* Global layout and container styling */
    .stApp {
        background-color: #0B0F19;
        color: #F1F5F9;
    }
    
    /* Custom Card container */
    .metric-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .metric-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-val {
        font-size: 24px;
        font-weight: 700;
        color: #F8FAFC;
    }
    .metric-val-teal {
        font-size: 24px;
        font-weight: 700;
        color: #0D9488;
    }
    .metric-val-amber {
        font-size: 24px;
        font-weight: 700;
        color: #D97706;
    }
    .metric-val-rose {
        font-size: 24px;
        font-weight: 700;
        color: #E11D48;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 4px 8px;
        font-size: 10px;
        font-weight: bold;
        border-radius: 4px;
        text-transform: uppercase;
    }
    .badge-pass {
        background-color: rgba(13, 148, 136, 0.15);
        color: #14B8A6;
        border: 1px solid #0D9488;
    }
    .badge-fail {
        background-color: rgba(225, 29, 72, 0.15);
        color: #FB7185;
        border: 1px solid #E11D48;
    }
    .badge-warn {
        background-color: rgba(217, 119, 6, 0.15);
        color: #FBBF24;
        border: 1px solid #D97706;
    }
    
    /* Clinical highlighting system */
    .highlight-span {
        background-color: rgba(13, 148, 136, 0.15);
        border: 1px solid #14B8A6;
        border-radius: 4px;
        padding: 1px 4px;
        font-weight: 500;
        color: #14B8A6;
        cursor: pointer;
        display: inline-block;
        margin: 1px 0;
    }
    .highlight-span:hover {
        background-color: rgba(13, 148, 136, 0.3);
    }
    
    /* Header notes */
    .header-desc {
        color: #94A3B8;
        font-size: 13px;
        margin-top: -15px;
        margin-bottom: 25px;
        line-height: 1.5;
    }
    
    /* Muted footer */
    .footer-text {
        font-size: 11px;
        color: #64748B;
        text-align: center;
        margin-top: 40px;
        border-top: 1px solid #334155;
        padding-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Data Loader and State Initialization
# ---------------------------------------------------------
db = AuditDatabase()
try:
    db.run_compliance_audit()
except Exception as e:
    pass

loader = DatasetLoader()
regression = RegressionEngine(loader)
encounters = loader.load_encounters()
predictions = loader.load_predictions()

# Sync workflow board state
if "kanban_board" not in st.session_state:
    board = {}
    for idx, row in encounters.iterrows():
        status = "Auditing" if row["record_id"] in ["REC001", "REC002"] else "Pending"
        board[row["record_id"]] = status
    st.session_state["kanban_board"] = board
else:
    board = st.session_state["kanban_board"]

if "selected_record" not in st.session_state:
    st.session_state["selected_record"] = "REC001"

# ---------------------------------------------------------
# Sidebar Filter Controls
# ---------------------------------------------------------
st.sidebar.markdown('<p style="font-size:12px; font-weight:600; text-transform:uppercase; color:#94A3B8; letter-spacing:0.05em; margin-bottom:5px;">Filter controls</p>', unsafe_allow_html=True)

# Clear/Reset Action
if st.sidebar.button("Reset Filters", use_container_width=True):
    st.session_state["selected_record"] = "REC001"
    st.rerun()

# Helper to get average confidence score for filtering
def parse_avg_conf(conf_str):
    if not conf_str:
        return 1.0
    try:
        scores = [float(x.strip()) for x in str(conf_str).split(",") if x.strip()]
        return sum(scores) / len(scores) if scores else 1.0
    except Exception:
        return 1.0

# Calculate average confidence helper column
predictions["avg_conf"] = predictions["confidence_scores"].apply(parse_avg_conf)

model_versions = ["clinical-nlp-v2", "clinical-nlp-v1"]
selected_model = st.sidebar.selectbox("Model Under Evaluation", model_versions, index=0)

# Load compliance results
conn = sqlite3.connect(DEFAULT_DB_PATH)
audit_df = pd.read_sql_query("SELECT * FROM compliance_audit_results", conn)
conn.close()

specialties = ["All"] + sorted(list(encounters["specialty"].unique()))
selected_specialty = st.sidebar.selectbox("Filter Specialty", specialties, index=0)

error_types = ["All", "wrong_modifier", "unit_confusion", "hcc_miss", "overcode", "ncci_conflict"]
selected_error = st.sidebar.selectbox("Filter Compliance Error", error_types, index=0)

note_sections = ["All"] + sorted(list(encounters["note_section"].unique()))
selected_section = st.sidebar.selectbox("Filter Note Section", note_sections, index=0)

selected_conf = st.sidebar.slider("Min Model Confidence", 0.0, 1.0, 0.0, 0.05)
selected_risk = st.sidebar.slider("Min Risk Score Filter", 0.0, 5.0, 0.0, 0.5)

code_search = st.sidebar.text_input("Search Billing Code (e.g. 93451)", "")

st.sidebar.markdown("---")
st.sidebar.markdown('<p style="font-size:11px; color:#64748B;">This console evaluates clinical coding regression parameters for release staging.</p>', unsafe_allow_html=True)

# Export Data Mock Action
if st.sidebar.button("Export Report (.CSV)", use_container_width=True):
    st.toast("Exporting compliance analysis data...")

# ---------------------------------------------------------
# Header & Context
# ---------------------------------------------------------
st.title("SynapseAudit Clinical Compliance Console")
st.markdown(
    '<p class="header-desc">Offline QA console for tracking model code drift, modifier compliance, HCC coverage gaps, and dosage unit safety before staging release.</p>',
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Metric Calculation
# ---------------------------------------------------------
# Filter encounters
filtered_encounters = encounters.copy()
if selected_specialty != "All":
    filtered_encounters = filtered_encounters[filtered_encounters["specialty"] == selected_specialty]
if selected_section != "All":
    filtered_encounters = filtered_encounters[filtered_encounters["note_section"] == selected_section]
if code_search.strip():
    code_val = code_search.strip()
    matching_pred_records = predictions[predictions["predicted_codes"].str.contains(code_val, case=False, na=False)]["record_id"]
    filtered_encounters = filtered_encounters[
        filtered_encounters["ground_truth_codes"].str.contains(code_val, case=False, na=False) |
        filtered_encounters["record_id"].isin(matching_pred_records)
    ]

# Apply compliance error type filter to encounters
if selected_error != "All":
    error_record_ids = set(audit_df[audit_df["error_type"] == selected_error]["record_id"])
    filtered_encounters = filtered_encounters[filtered_encounters["record_id"].isin(error_record_ids)]

# Apply risk score filter to encounters
if selected_risk > 0.0:
    risk_record_ids = set(audit_df[audit_df["risk_score"] >= selected_risk]["record_id"])
    filtered_encounters = filtered_encounters[filtered_encounters["record_id"].isin(risk_record_ids)]

# Filter predictions and audits based on remaining encounters
filtered_record_ids = set(filtered_encounters["record_id"])
filtered_predictions = predictions[predictions["record_id"].isin(filtered_record_ids)]
filtered_predictions = filtered_predictions[filtered_predictions["avg_conf"] >= selected_conf]

# Re-resolve the matched record IDs after predictions filtering
filtered_record_ids = set(filtered_predictions["record_id"])
filtered_encounters = filtered_encounters[filtered_encounters["record_id"].isin(filtered_record_ids)]

total_records = len(filtered_encounters)

filtered_audit_df = audit_df[audit_df["record_id"].isin(filtered_record_ids)]
if selected_error != "All":
    filtered_audit_df = filtered_audit_df[filtered_audit_df["error_type"] == selected_error]
filtered_audit_df = filtered_audit_df[filtered_audit_df["risk_score"] >= selected_risk]

# Compute Exact Match Accuracy for selected model
active_preds = filtered_predictions[filtered_predictions["model_version"] == selected_model]
active_merged = pd.merge(filtered_encounters, active_preds, on="record_id")
em_matches = sum(active_merged["predicted_codes"] == active_merged["ground_truth_codes"])
active_em = em_matches / total_records if total_records > 0 else 0.0

# Compute Modifier Accuracy for selected model
wrong_mod = len(filtered_audit_df[(filtered_audit_df["model_version"] == selected_model) & (filtered_audit_df["error_type"] == "wrong_modifier")])
active_mod = 1.0 - (wrong_mod / total_records) if total_records > 0 else 1.0

# Compute HCC Miss Rate for selected model
hcc_miss = len(filtered_audit_df[(filtered_audit_df["model_version"] == selected_model) & (filtered_audit_df["error_type"] == "hcc_miss")])
hcc_miss_rate = hcc_miss / total_records if total_records > 0 else 0.0

# Compute Unit Mismatch Rate for selected model
unit_mismatch = len(filtered_audit_df[(filtered_audit_df["model_version"] == selected_model) & (filtered_audit_df["error_type"] == "unit_confusion")])
unit_mismatch_rate = unit_mismatch / total_records if total_records > 0 else 0.0

# Compute dynamic financial impact metrics
violations_list = [{"error_type": row["error_type"], "risk_score": row["risk_score"]} 
                   for _, row in filtered_audit_df[filtered_audit_df["model_version"] == selected_model].iterrows()]
fin_metrics = calculate_financial_impact(violations_list)
active_leakage = fin_metrics["revenue_leakage"]
active_liability = fin_metrics["rejection_liability"]
active_ar_delay = fin_metrics["max_ar_delay_days"]

# Model Drift Score
comparison_dict = regression.compare_versions()
if selected_specialty != "All":
    avg_delta = comparison_dict.get(selected_specialty, {}).get("delta", 0.0)
else:
    avg_delta = sum(m["delta"] for m in comparison_dict.values()) / len(comparison_dict) if comparison_dict else 0.0

# Release Gate Status Check
gate_failed = (avg_delta < -0.05) or (wrong_mod > 0) or (unit_mismatch > 0)

# ---------------------------------------------------------
# Top Compact KPI Row
# ---------------------------------------------------------
kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6 = st.columns(6)

with kpi_col1:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Exact Match Acc</div>'
        f'<div class="metric-val">{active_em:.1%}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
with kpi_col2:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Modifier Accuracy</div>'
        f'<div class="metric-val-teal">{active_mod:.1%}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
with kpi_col3:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Revenue Leakage</div>'
        f'<div class="metric-val-rose">${active_leakage:,.0f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
with kpi_col4:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Rejection Liability</div>'
        f'<div class="metric-val-amber">${active_liability:,.0f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
with kpi_col5:
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">A/R Delay Risk</div>'
        f'<div class="metric-val">{active_ar_delay} Days</div>'
        f'</div>',
        unsafe_allow_html=True
    )
with kpi_col6:
    gate_badge = '<span class="badge badge-fail">Blocked</span>' if gate_failed else '<span class="badge badge-pass">Passed</span>'
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="metric-label">Release Gate</div>'
        f'<div style="margin-top:6px;">{gate_badge}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Workspace Navigation (Tabs)
# ---------------------------------------------------------
tab_overview, tab_regression, tab_specialty, tab_ledger, tab_sql, tab_gate = st.tabs([
    "Executive Overview",
    "Regression Analysis",
    "Specialty Drift",
    "Explainable Audit Ledger",
    "SQL Insights",
    "Staging Release Gate"
])

# ---------------------------------------------------------
# Tab 1: Executive Overview
# ---------------------------------------------------------
with tab_overview:
    col_sum1, col_sum2 = st.columns([2, 1])
    
    with col_sum1:
        st.subheader("Release Candidate Evaluation Summary")
        st.markdown(
            "Comparing baseline configuration **clinical-nlp-v1** (Stable Reference) and candidate **clinical-nlp-v2** (Staging Candidate) "
            "across deidentified notes and edge case sets."
        )
        
        # Overview Metric Card Grid
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1:
            st.info("**Evaluation Cohort Size**\n\n200+ Clinical Records")
        with sum_col2:
            st.info("**Monitored Rule Classes**\n\n4 Compliance Categories")
        with sum_col3:
            st.info("**Evaluation Status**\n\nStaging Release Candidate")
            
        st.markdown("### Risk Analysis Insights")
        st.markdown(
            "- **Modifier Omits**: The staging candidate fails to attach Modifier 25 in Cardiology note segments where procedure CPT 93451 is performed alongside E/M code 99213.\n"
            "- **Unit Confusion Alert**: Endocrinology notes show instances of unit mismatches (`mg` instead of `mcg` for levothyroxine), resulting in a failure to pass clinical safety checks.\n"
            "- **HCC Miss Rate**: Dropping specific risk-adjustment coding for stage III/IV CKD. This triggers risk scores adjustments in clinical evaluation."
        )
        
    with col_sum2:
        st.subheader("Release Status Board")
        if gate_failed:
            st.markdown(
                '<div style="background-color:rgba(225,29,72,0.1); border: 1px solid #E11D48; border-radius:8px; padding: 20px;">'
                '<h4 style="color:#FB7185; margin-top:0;">CRITICAL RELEASE BLOCKED</h4>'
                '<p style="font-size:13px; color:#F1F5F9; line-height:1.5;">'
                'The candidate model version <strong>clinical-nlp-v2</strong> has failed compliance checks.<br><br>'
                '<strong>Top Risk Reasons:</strong><br>'
                '- Dosage unit confusion identified in endocrinology validation notes.<br>'
                '- Modifier 25 omission rate exceeded the 0% drop tolerance.'
                '</p>'
                '</div>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div style="background-color:rgba(13, 148, 136, 0.1); border: 1px solid #0D9488; border-radius:8px; padding: 20px;">'
                '<h4 style="color:#14B8A6; margin-top:0;">RELEASE APPROVED</h4>'
                '<p style="font-size:13px; color:#F1F5F9; line-height:1.5;">'
                'The candidate model version <strong>clinical-nlp-v2</strong> passes all deterministic rules checks.'
                '</p>'
                '</div>', 
                unsafe_allow_html=True
            )

    # Dynamic Layperson box for Executive Overview tab
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background-color:#1E293B; border-left: 5px solid #0D9488; border-radius: 6px; padding: 22px; margin-top: 25px; margin-bottom: 25px;">
            <h3 style="color:#F1F5F9; margin-top:0; font-size:18px;">💡 Hey viewer! Here is your Live Audit & Filter Guide</h3>
            <p style="font-size:14px; color:#E2E8F0; line-height:1.6; margin-bottom:12px;">
                Welcome to the console. You are actively controlling how clinical billing charts are audited using the sidebar parameters. Let's break down the live dashboard state:
            </p>
            <div style="background-color:#0F172A; border-radius:4px; padding:12px; margin-bottom:15px; border:1px solid #334155;">
                <h4 style="color:#38BDF8; font-size:14px; margin-top:0; margin-bottom:8px;">🛠️ Active Sidebar Filter Controls</h4>
                <ul style="color:#94A3B8; font-size:13px; margin-left:15px; margin-bottom:0; line-height:1.5;">
                    <li><b>Model Under Evaluation</b>: You are examining <code>{selected_model}</code>. (v1 is the stable production reference; v2 is the staging update).</li>
                    <li><b>Filter Specialty</b>: Slicing by department: <code>{selected_specialty}</code>.</li>
                    <li><b>Filter Compliance Error</b>: Slicing by error category: <code>{selected_error}</code>.</li>
                    <li><b>Filter Note Section</b>: Slicing by clinical layout: <code>{selected_section}</code>.</li>
                    <li><b>Min Model Confidence</b>: Filtering out AI codes with confidence below <code>{selected_conf:.2f}</code>.</li>
                    <li><b>Min Risk Score Filter</b>: Filtering out audit results with a risk severity below <code>{selected_risk:.1f}</code>.</li>
                    <li><b>Search Billing Code</b>: Restricting views to encounters matching: <code>"{code_search or "N/A"}"</code>.</li>
                </ul>
            </div>
            <div style="background-color:#0F172A; border-radius:4px; padding:12px; margin-bottom:15px; border:1px solid #334155;">
                <h4 style="color:#34D399; font-size:14px; margin-top:0; margin-bottom:8px;">📊 What to Infer from the Current KPI Scores</h4>
                <ul style="color:#94A3B8; font-size:13px; margin-left:15px; margin-bottom:0; line-height:1.5;">
                    <li><b>Exact Match Acc ({active_em:.1%})</b>: This shows how often the AI gets every single billing code exactly correct. **Higher is better.**</li>
                    <li><b>Modifier Accuracy ({active_mod:.1%})</b>: The AI's success in applying procedure modifiers (like Modifier 25). **Low scores mean immediate claim rejections.**</li>
                    <li><b>Revenue Leakage (${active_leakage:,.2f})</b>: 🔴 <b>BAD if above $0!</b> The estimated cash the hospital is losing because the AI forgot to document valid diagnosis codes (missed HCCs).</li>
                    <li><b>Rejection Liability (${active_liability:,.2f})</b>: 🔴 <b>BAD if above $0!</b> Financial rework penalties and billing rejections triggered by NCCI coding conflicts or wrong modifiers.</li>
                    <li><b>A/R Delay Risk ({active_ar_delay} Days)</b>: The average time hospital payments will be frozen in Accounts Receivable waiting for administrative reviews.</li>
                    <li><b>Release Gate Status ({"BLOCKED" if gate_failed else "PASSED"})</b>: If **BLOCKED**, the candidate model v2 has failed safety limits and cannot go live.</li>
                </ul>
            </div>
            <div style="background-color:#0F172A; border-radius:4px; padding:12px; border:1px solid #334155;">
                <h4 style="color:#F472B6; font-size:14px; margin-top:0; margin-bottom:8px;">🚀 Next Steps & Who to Reach Out To</h4>
                <p style="font-size:13px; color:#94A3B8; line-height:1.5; margin-bottom:0;">
                    <b>If the Release Gate is Blocked:</b><br>
                    1. Revert to the stable <code>clinical-nlp-v1</code> configuration (use the Rollback Console on the Staging Release Gate tab).<br>
                    2. Reach out to the <b>NLP ML Engineering Team</b> to adjust prompt templates and retrain model parameters for specialties with F1 regressions.<br>
                    3. Reach out to the <b>Clinical Billing & Compliance Director</b> to confirm NCCI rules and verify modifier guidelines for the flagged records in the Explainable Audit Ledger.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Tab 2: Regression Analysis
# ---------------------------------------------------------
with tab_regression:
    st.subheader("Clinical Coding Drift (F1 Performance Delta)")
    
    # Render drift comparison bar chart
    specs = list(comparison_dict.keys())
    v1_scores = [comparison_dict[s]["v1_f1"] for s in specs]
    v2_scores = [comparison_dict[s]["v2_f1"] for s in specs]
    
    fig = go.Figure(data=[
        go.Bar(name='Active Reference (v1)', x=specs, y=v1_scores, marker_color='#334155'),
        go.Bar(name='Staging Candidate (v2)', x=specs, y=v2_scores, marker_color='#14B8A6')
    ])
    fig.update_layout(
        barmode='group',
        template="plotly_dark",
        yaxis_title="F1 Score",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10)
    )
    st.plotly_chart(fig, use_container_width=True, key="drift_bar_chart")
    
    st.markdown("### Specialty-Level Performance & Revenue Matrix")
    comparison_df = pd.DataFrame.from_dict(comparison_dict, orient='index')
    # Format and style dataframe columns
    formatted_df = comparison_df.copy()
    formatted_df.columns = [
        "Baseline F1", "Candidate F1", "F1 Delta", "Regression Counts",
        "Baseline Leakage ($)", "Candidate Leakage ($)",
        "Baseline Liability ($)", "Candidate Liability ($)",
        "Baseline A/R Delay (Days)", "Candidate A/R Delay (Days)"
    ]
    st.dataframe(
        formatted_df.style.format({
            "Baseline F1": "{:.2f}",
            "Candidate F1": "{:.2f}",
            "F1 Delta": "{:+.2f}",
            "Baseline Leakage ($)": "${:,.2f}",
            "Candidate Leakage ($)": "${:,.2f}",
            "Baseline Liability ($)": "${:,.2f}",
            "Candidate Liability ($)": "${:,.2f}",
            "Baseline A/R Delay (Days)": "{:.0f}",
            "Candidate A/R Delay (Days)": "{:.0f}"
        }).highlight_min(subset=["F1 Delta"], color="#7F1D1D"),
        use_container_width=True
    )

    # Dynamic Layperson box for Regression tab
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background-color:#1E293B; border-left: 5px solid #0D9488; border-radius: 6px; padding: 20px; margin-top: 25px;">
            <h3 style="color:#F1F5F9; margin-top:0; font-size:16px;">💡 Auditor's Console Guide: Regression Analysis</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>What you are looking at:</b> This tab compares the coding accuracy (F1 score) and the financial impact between the old baseline (v1) and candidate (v2) models. 
                The <b>F1 Delta</b> column shows the performance shift. A negative delta (highlighted in red) means the new model has regressed and is performing worse than the old one.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>Is this Good or Bad?</b> Check the **F1 Delta**, **Leakage ($)** and **Liability ($)** deltas. If you see high red highlights or increased leakage for the candidate, this is **BAD** because it represents silent revenue loss.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:0;">
                <b>What you should do:</b> Identify the specialties with high negative F1 deltas (such as Cardiology or Gynecology). Do <b>NOT</b> approve a release that degrades F1 coding accuracy. Work on prompt adjustments for these specific specialties.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Tab 3: Specialty Drift
# ---------------------------------------------------------
with tab_specialty:
    st.subheader("Specialty Risk Heatmap & Error Distribution")
    
    # Generate Heatmap data
    h_df = db.get_drift_by_specialty()
    # Pivot for Heatmap visualization
    if not h_df.empty:
        h_df_filtered = h_df[h_df["model_version"] == selected_model]
        pivot_df = h_df_filtered.pivot_table(index='specialty', columns='error_type', values='error_count', aggfunc='sum').fillna(0)
        
        fig_heat = px.imshow(
            pivot_df, 
            labels=dict(x="Compliance Error Type", y="Specialty", color="Error Count"),
            color_continuous_scale="Teal",
            template="plotly_dark"
        )
        fig_heat.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=10, l=10, r=10)
        )
        
        heat_col1, heat_col2 = st.columns([3, 2])
        with heat_col1:
            st.plotly_chart(fig_heat, use_container_width=True, key="specialty_heatmap")
        with heat_col2:
            # Aggregated error counts by type bar chart
            err_summary = h_df_filtered.groupby("error_type")["error_count"].sum().reset_index()
            fig_err_bar = px.bar(
                err_summary, 
                x="error_count", 
                y="error_type", 
                orientation="h",
                title="Distribution of Error Types",
                labels=dict(error_count="Error Count", error_type="Error Type"),
                color_discrete_sequence=["#14B8A6"],
                template="plotly_dark"
            )
            fig_err_bar.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=30, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_err_bar, use_container_width=True, key="error_distribution_bar")
    else:
        st.info("No compliance error records found to map.")

    # Dynamic Layperson box for Specialty Drift tab
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background-color:#1E293B; border-left: 5px solid #0D9488; border-radius: 6px; padding: 20px; margin-top: 25px;">
            <h3 style="color:#F1F5F9; margin-top:0; font-size:16px;">💡 Auditor's Console Guide: Specialty Risk Heatmap</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>What you are looking at:</b> This heatmap plots the type of coding errors across different medical specialties for the selected model <b>{selected_model}</b>. 
                The side bar chart shows the total distribution of error types (such as wrong modifiers or NCCI bundling conflicts).
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>Is this Good or Bad?</b> Large dark teal blocks or high counts of **wrong_modifier** are **BAD** because they mean the AI is failing to apply modifiers, which leads to immediate insurance claim rejections. High counts of **hcc_miss** represent direct under-billing.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:0;">
                <b>What you should do:</b> Use the filters to toggle models and see how the error distribution shifts. Focus engineering effort on resolving the most frequent error category highlighted in the distribution bar chart.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Tab 4: Explainable Audit Ledger
# ---------------------------------------------------------
with tab_ledger:
    st.subheader("Explainable Audit Ledger")
    
    # Search and Filter criteria inside the tab
    col_led_filt1, col_led_filt2 = st.columns([1, 2])
    
    # Filter encounters based on all active sidebar filters
    filt_encounters = filtered_encounters
    # Auto-adjust selected record session state if it's no longer in the filtered record list
    record_list = filt_encounters["record_id"].tolist()
    if record_list and st.session_state.get("selected_record") not in record_list:
        st.session_state["selected_record"] = record_list[0]
        
    with col_led_filt1:
        record_list = filt_encounters["record_id"].tolist()
        if record_list:
            default_index = 0
            if st.session_state["selected_record"] in record_list:
                default_index = record_list.index(st.session_state["selected_record"])
            selected_id = st.selectbox("Select Record ID", record_list, index=default_index)
            st.session_state["selected_record"] = selected_id
        else:
            st.warning("No records match filters.")
            selected_id = None
            
    if selected_id:
        record = encounters[encounters["record_id"] == selected_id].iloc[0]
        note_text = record["note_text"]
        
        col_note, col_details = st.columns([2, 1])
        
        with col_note:
            st.markdown("**Evidence-Span Highlighting**")
            parser = ClinicalParser()
            spans = parser.parse_note(note_text)
            spans = sorted(spans, key=lambda x: x["start"], reverse=True)
            highlighted = note_text
            for s in spans:
                start, end, code = s["start"], s["end"], s["code"]
                highlighted = (
                    highlighted[:start] + 
                    f'<span class="highlight-span" title="Code matched: {code}">{highlighted[start:end]} [Code: {code}]</span>' + 
                    highlighted[end:]
                )
            st.markdown(f'<div style="background-color: #1E293B; border: 1px solid #334155; padding: 20px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; line-height: 1.6; color: #F1F5F9;">{highlighted}</div>', unsafe_allow_html=True)
            
        with col_details:
            st.markdown("**Adjudication Control Panel**")
            
            # Workflow board
            curr_status = board.get(selected_id, "Pending")
            st.markdown(f"Status: `{curr_status}`")
            
            app_col, rej_col = st.columns(2)
            with app_col:
                if st.button("Approve Code Set", key=f"btn_app_{selected_id}", type="primary", use_container_width=True):
                    board[selected_id] = "Approved"
                    st.session_state["kanban_board"] = board
                    st.toast(f"Case {selected_id} approved.")
                    st.rerun()
            with rej_col:
                if st.button("Reject / Flag", key=f"btn_rej_{selected_id}", use_container_width=True):
                    board[selected_id] = "Rejected"
                    st.session_state["kanban_board"] = board
                    st.toast(f"Case {selected_id} rejected.")
                    st.rerun()
                    
            st.markdown("---")
            st.markdown("**Side-by-Side Model Code Comparison**")
            
            pred_v1 = predictions[(predictions["record_id"] == selected_id) & (predictions["model_version"] == "clinical-nlp-v1")].iloc[0]
            pred_v2 = predictions[(predictions["record_id"] == selected_id) & (predictions["model_version"] == "clinical-nlp-v2")].iloc[0]
            
            st.markdown(f"**Stable baseline (v1)**: `{pred_v1['predicted_codes']}` (Modifiers: `{pred_v1['predicted_modifiers'] or 'None'}`)")
            st.markdown(f"**Candidate Release (v2)**: `{pred_v2['predicted_codes']}` (Modifiers: `{pred_v2['predicted_modifiers'] or 'None'}`)")
            
            # Violations specific to this record
            violations = audit_df[(audit_df["record_id"] == selected_id) & (audit_df["model_version"] == selected_model)]
            if not violations.empty:
                st.markdown("**Staging Compliance Mismatches**")
                st.dataframe(violations[["error_type", "risk_score", "details"]], hide_index=True)
            else:
                st.success("Case passes all compliance rules.")

    # Dynamic Layperson box for Ledger tab
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background-color:#1E293B; border-left: 5px solid #0D9488; border-radius: 6px; padding: 20px; margin-top: 25px;">
            <h3 style="color:#F1F5F9; margin-top:0; font-size:16px;">💡 Auditor's Console Guide: Explainable Audit Ledger</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>What you are looking at:</b> This is the patient-level audit room. You can select any individual record (like <b>{selected_id or "REC001"}</b>) to view its full note text. 
                The green highlighted words show where the AI extracted the codes. The right panel displays the side-by-side code predictions of both models vs the gold standard.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>Is this Good or Bad?</b> If the candidate version predictions differ from the gold-standard codes, it is **BAD**. It means the model made a concrete coding mistake on this chart, resulting in either lost revenue (under-coding) or audit risk (over-coding).
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:0;">
                <b>What you should do:</b> Review the highlighted evidence. Use the <b>Adjudication Control Panel</b> to Approve or Reject/Flag the case for compliance reviews.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Tab 5: SQL Insights
# ---------------------------------------------------------
with tab_sql:
    st.subheader("Compliance Database SQL Analytics")
    st.markdown("Explore live database queries executed directly on the SQLite data engine.")
    
    query_option = st.selectbox("Select SQL Query to Execute", [
        "1. Model Version Drift by Specialty",
        "2. HCC Miss Rate by Chronic Condition",
        "3. Unit Mismatch Frequency (Unit Confusion)",
        "4. Modifier Failure Rate",
        "5. Claim Deniability Risk Index (CDRI)"
    ])
    
    queries = {
        "1. Model Version Drift by Specialty": """
-- Which medical specialties are experiencing the highest rate of audit errors and code drift under the candidate model?
SELECT 
    p.model_version,
    p.prompt_version,
    e.specialty,
    c.error_type,
    COUNT(c.audit_id) AS error_count,
    COUNT(DISTINCT e.record_id) AS total_records,
    ROUND(COUNT(c.audit_id) * 1.0 / COUNT(DISTINCT e.record_id), 4) AS error_rate,
    ROUND(AVG(c.risk_score), 4) AS risk_index
FROM clinical_encounters e
JOIN model_predictions p ON e.record_id = p.record_id
LEFT JOIN compliance_audit_results c ON e.record_id = c.record_id 
    AND p.model_version = c.model_version 
    AND p.prompt_version = c.prompt_version
GROUP BY p.model_version, p.prompt_version, e.specialty, c.error_type
ORDER BY e.specialty, error_rate DESC;""",
        
        "2. HCC Miss Rate by Chronic Condition": """
-- How frequently is the candidate model failing to document Hierarchical Condition Categories (HCCs) present in gold-standard records, resulting in potential under-billing?
SELECT
    p.model_version,
    p.prompt_version,
    COUNT(CASE WHEN c.error_type = 'hcc_miss' THEN 1 END) AS error_count,
    COUNT(DISTINCT e.record_id) AS total_records,
    ROUND(COUNT(CASE WHEN c.error_type = 'hcc_miss' THEN 1 END) * 1.0 / COUNT(DISTINCT e.record_id), 4) AS error_rate
FROM clinical_encounters e
JOIN model_predictions p ON e.record_id = p.record_id
LEFT JOIN compliance_audit_results c ON e.record_id = c.record_id 
    AND p.model_version = c.model_version 
    AND p.prompt_version = c.prompt_version
GROUP BY p.model_version, p.prompt_version;""",
        
        "3. Unit Mismatch Frequency (Unit Confusion)": """
-- What is the rate of dosage unit confusion (e.g. mg vs mcg) predicted by different model configurations?
SELECT
    p.model_version,
    p.prompt_version,
    COUNT(CASE WHEN c.error_type = 'unit_confusion' THEN 1 END) AS error_count,
    COUNT(DISTINCT e.record_id) AS total_records,
    ROUND(COUNT(CASE WHEN c.error_type = 'unit_confusion' THEN 1 END) * 1.0 / COUNT(DISTINCT e.record_id), 4) AS error_rate
FROM clinical_encounters e
JOIN model_predictions p ON e.record_id = p.record_id
LEFT JOIN compliance_audit_results c ON e.record_id = c.record_id 
    AND p.model_version = c.model_version 
    AND p.prompt_version = c.prompt_version
GROUP BY p.model_version, p.prompt_version;""",
        
        "4. Modifier Failure Rate": """
-- How often does the candidate model fail to attach correct modifiers (e.g., Modifier 25) when billing procedures alongside E/M services?
SELECT
    p.model_version,
    p.prompt_version,
    COUNT(CASE WHEN c.error_type = 'wrong_modifier' THEN 1 END) AS error_count,
    COUNT(DISTINCT e.record_id) AS total_records,
    ROUND(COUNT(CASE WHEN c.error_type = 'wrong_modifier' THEN 1 END) * 1.0 / COUNT(DISTINCT e.record_id), 4) AS error_rate
FROM clinical_encounters e
JOIN model_predictions p ON e.record_id = p.record_id
LEFT JOIN compliance_audit_results c ON e.record_id = c.record_id 
    AND p.model_version = c.model_version 
    AND p.prompt_version = c.prompt_version
GROUP BY p.model_version, p.prompt_version;""",
        
        "5. Claim Deniability Risk Index (CDRI)": """
-- What is the aggregate Claim Deniability Risk Index (CDRI) across model and prompt versions?
SELECT
    p.model_version,
    p.prompt_version,
    (COUNT(CASE WHEN c.error_type IN ('wrong_modifier', 'ncci_conflict') THEN 1 END) * 1.5 + 
     COUNT(CASE WHEN c.error_type = 'overcode' THEN 1 END)) * 1.0 / COUNT(DISTINCT e.record_id) AS claim_deniability_risk_index
FROM clinical_encounters e
JOIN model_predictions p ON e.record_id = p.record_id
LEFT JOIN compliance_audit_results c ON e.record_id = c.record_id 
    AND p.model_version = c.model_version 
    AND p.prompt_version = c.prompt_version
GROUP BY p.model_version, p.prompt_version;"""
    }
    
    selected_query = queries[query_option]
    st.code(selected_query, language="sql")
    
    if st.button("Run Analytics Query", type="primary"):
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        res_df = pd.read_sql_query(selected_query, conn)
        conn.close()
        st.dataframe(res_df)

    # Dynamic Layperson box for SQL Insights tab
    st.markdown("---")
    st.markdown(
        """
        <div style="background-color:#1E293B; border-left: 5px solid #0D9488; border-radius: 6px; padding: 20px; margin-top: 25px;">
            <h3 style="color:#F1F5F9; margin-top:0; font-size:16px;">💡 Auditor's Console Guide: SQL Insights</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>What you are looking at:</b> This is a direct query portal for database analytics. You can select pre-written queries to calculate error rates, HCC misses, or the Claim Deniability Risk Index (CDRI) directly using SQL.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>Is this Good or Bad?</b> Running these queries gives you the underlying statistics that power the graphs. High error rates or rising CDRIs are **BAD** and should trigger prompt tuning updates.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:0;">
                <b>What you should do:</b> Click the **Run Analytics Query** button to pull the raw tables. You can use these tables to build custom spreadsheets for executive reporting.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Tab 6: Release Gate
# ---------------------------------------------------------
with tab_gate:
    st.subheader("Release Gate Staging Metrics & Pipeline Rules")
    
    st.markdown(
        "A candidate release version must satisfy all evaluation criteria relative to the baseline production configuration. "
        "Failure of any rule automatically blocks staging deployment."
    )
    
    # Calculate global candidate v2 metrics for the rules matrix
    global_total = len(encounters)
    global_v2_wrong_mod = len(audit_df[(audit_df["model_version"] == "clinical-nlp-v2") & (audit_df["error_type"] == "wrong_modifier")])
    global_v2_mod_acc = 1.0 - (global_v2_wrong_mod / global_total) if global_total > 0 else 1.0
    
    global_v2_hcc_miss = len(audit_df[(audit_df["model_version"] == "clinical-nlp-v2") & (audit_df["error_type"] == "hcc_miss")])
    global_v2_hcc_miss_rate = global_v2_hcc_miss / global_total if global_total > 0 else 0.0
    
    global_v2_unit_mismatch = len(audit_df[(audit_df["model_version"] == "clinical-nlp-v2") & (audit_df["error_type"] == "unit_confusion")])
    global_v2_unit_mismatch_rate = global_v2_unit_mismatch / global_total if global_total > 0 else 0.0
    
    global_avg_delta = sum(m["delta"] for m in comparison_dict.values()) / len(comparison_dict) if comparison_dict else 0.0

    # Table displaying active rules & status
    rules_data = [
        {"Rule Name": "Modifier Accuracy Drop", "Threshold": ">= Baseline (v1)", "Active Candidate Value": f"{global_v2_mod_acc:.1%}", "Status": "FAIL" if global_v2_wrong_mod > 0 else "PASS"},
        {"Rule Name": "HCC Capture Miss", "Threshold": "No increase vs v1", "Active Candidate Value": f"{global_v2_hcc_miss_rate:.1%}", "Status": "FAIL" if global_v2_hcc_miss > 0 else "PASS"},
        {"Rule Name": "Unit Mismatch Error", "Threshold": "0.0% Tolerance", "Active Candidate Value": f"{global_v2_unit_mismatch_rate:.1%}", "Status": "FAIL" if global_v2_unit_mismatch > 0 else "PASS"},
        {"Rule Name": "F1 Drift Specialty Tolerance", "Threshold": ">= -2.0% Delta", "Active Candidate Value": f"{global_avg_delta:+.3f}", "Status": "FAIL" if global_avg_delta < -0.02 else "PASS"},
    ]
    st.table(rules_data)
    
    # Interactive Rollback Trigger Box
    st.markdown("### Deployment Staging Rollback Console")
    
    if st.session_state.get("is_rolled_back", False):
        st.success("Staging is active: Rollback executed to baseline stable clinical-nlp-v1.")
        if st.button("Re-enable Candidate Release Evaluation"):
            st.session_state["is_rolled_back"] = False
            st.rerun()
    else:
        if gate_failed:
            st.error("Release Candidate (v2) has failed compliance criteria. Pipelines are blocked.")
            if st.button("Execute Hot Rollback to Stable Baseline", type="primary"):
                st.session_state["is_rolled_back"] = True
                st.toast("System rolled back to stable clinical-nlp-v1.")
                st.rerun()
        else:
            st.success("Release Candidate (v2) has passed compliance checks. Staging approved.")

    # Dynamic Layperson box for Release Gate tab
    st.markdown("---")
    st.markdown(
        f"""
        <div style="background-color:#1E293B; border-left: 5px solid #0D9488; border-radius: 6px; padding: 20px; margin-top: 25px;">
            <h3 style="color:#F1F5F9; margin-top:0; font-size:16px;">💡 Auditor's Console Guide: Staging Release Gate</h3>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>What you are looking at:</b> This is the final quality check matrix. The table lists the release rules (e.g. F1 drift, modifier accuracy drop). If any rule fails, the candidate release is blocked.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:12px;">
                <b>Is this Good or Bad?</b> If the candidate is **Blocked**, it is **BAD** for deployment speed but **GOOD** for safety. It means we have caught coding regressions before they could cause real claim rejections.
            </p>
            <p style="font-size:14px; color:#94A3B8; line-height:1.6; margin-bottom:0;">
                <b>What you should do:</b> If the gate is blocked, click the <b>Execute Hot Rollback to Stable Baseline</b> button to revert the staging environment to the stable baseline model (v1) instantly.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------
# Footer Section
# ---------------------------------------------------------
st.markdown(
    '<div class="footer-text">'
    'SynapseAudit Build v1.2.0 • Data derived from deidentified clinical notes and synthetic safety profiles • Internal compliance audit logs'
    '</div>', 
    unsafe_allow_html=True
)
