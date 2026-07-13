# SynapseAudit

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/Navneet-Scaler/SynapsAudit)
[![Live Dashboard](https://img.shields.io/badge/Live-Dashboard-green?logo=streamlit)](https://navneet-scaler-synapsaudit-dashboardsapp-k5q7lf.streamlit.app/)

### The Problem
Every dollar in a healthcare system flows directly through medical coding. Changes in base clinical NLP models or LLM prompt variations introduce silent code and prompt drift, leading to severe **revenue leakage** (missed chronic condition HCC codes) and immediate **billing claim rejections** (omitted billing modifiers and overcoded E/M levels).

### The Solution
**SynapseAudit** is an offline **Clinical NLP Revenue Assurance & Regression Engine** designed for deterministic validation of model-predicted CPT/ICD-10 codes, modifier logic, and HCC capture against a human-adjudicated gold-standard dataset.

### The Target Audience
This engine is built for **Product Analysts**, **AI QA Engineers**, and **Clinical Revenue Assurance Teams** to audit model revisions and enforce deployment safety gates before updates go live.

---

### Visual Workflow & Pipeline Architecture

```mermaid
graph LR
    %% Styling Classes
    classDef input fill:#1E293B,stroke:#475569,stroke-width:1px,color:#F8FAFC;
    classDef engine fill:#0F172A,stroke:#0D9488,stroke-width:2px,color:#F1F5F9;
    classDef metric fill:#1E293B,stroke:#334155,stroke-width:1px,color:#F8FAFC;
    classDef gate fill:#7F1D1D,stroke:#F87171,stroke-width:1.5px,color:#FEE2E2;
    classDef pass fill:#064E3B,stroke:#34D399,stroke-width:1.5px,color:#D1FAE5;

    %% Data Nodes
    A["Clinical Note Input <br> (EHR Charts)"]:::input
    B["AI Coding Predictions <br> (CPT / ICD-10 / Modifiers)"]:::input

    %% Processing Nodes
    C["SynapseAudit Loader <br> (Text Highlighting & Alignment)"]:::engine
    D{"Rules Verification <br> (Modifier, HCC, Unit Check)"}:::engine

    %% Review Nodes
    E["Drift & Performance Console <br> (F1 & Kappa Metrics)"]:::metric
    F["Explainable Audit Ledger <br> (Auditor Agree/Disagree)"]:::metric

    %% Gate Decisions
    G{"CI/CD Release Gate <br> (Tolerance Thresholds)"}:::gate
    H["Deploy Candidate Model"]:::pass
    I["Rollback to Stable Model"]:::gate

    %% Connections
    A & B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G -->|Pass| H
    G -->|Fail| I
```

> [!NOTE]
> ### 💡 Understanding the Business: The "Doctor, AI, and Insurance" Story
> 
> **1. What is actually happening here?**
> *   **The Doctor's Work**: When you visit a doctor, they write a detailed clinical note summarizing your symptoms, diagnoses, and treatments.
> *   **The AI's Job**: Hospitals use clinical autonomous coding engines (like **Arintra**) to read these notes and translate them into standardized billing codes (ICD-10, CPT, and modifiers) to request payment from insurance companies.
> *   **Arintra's Engine vs. SynapseAudit**:
>     *   **Arintra's Engine**: Actually does the clinical coding (inputting notes, predicting and producing billing codes directly from EHR systems like Epic or Cerner without human coders).
>     *   **SynapseAudit**: Is the QA Evaluation suite that tests and stress-tests coding outputs. It doesn't write codes itself; it checks if the AI-predicted codes (which could come from an engine like Arintra's) have regressed or violated compliance rules.
> 
> **2. Why is this validation engine (SynapseAudit) needed?**
> *   **If the AI under-codes (Misses details)**: If the AI misses that a patient has chronic diabetes (an HCC code), the hospital gets paid less than they should.
> *   **If the AI over-codes (Exaggerates details) or forgets billing rules**: If the AI lists a procedure but forgets to attach a mandatory billing modifier (Modifier 25), the insurance company immediately rejects the claim. This delays hospital payments and triggers federal audits (compliance liabilities).
> *   **The Problem of "AI Drift"**: Software updates or prompt tweaks to the AI model can cause it to suddenly lose accuracy on specific specialties (e.g., Cardiology), leading to systemic billing failures.
> 
> **3. Who pays us for this service?**
> *   **Hospital Networks & Healthcare Systems**: They pay for this tool to prevent millions of dollars in insurance claim rejections and compliance audits.
> *   **Autonomous AI Coding Vendors (like Arintra)**: An AI coding vendor like Arintra uses an internal engine like SynapseAudit to run regression audits on their own coding models whenever their engineers release a new version or change prompt templates.
> 
> *SynapseAudit acts as the regression testing gate—making sure that upgrading the AI doesn't cause it to become worse at coding and bankrupt the hospital.*

---

## Key Metrics

| Metric | Definition |
| :--- | :--- |
| **Exact-Match Accuracy** | The percentage of clinical encounters where the model's predicted codes perfectly match the gold-standard codes. |
| **Modifier Accuracy** | The percentage of eligible encounters where Modifier 25 is correctly attached to E/M codes when a separate procedure is performed. |
| **Unit Accuracy** | The percentage of medication dosage matches where the predicted code matches the correct unit (e.g., `mcg` vs. `mg`). |
| **HCC Capture Rate** | The percentage of gold-standard Hierarchical Condition Categories (HCCs) correctly captured by the model. |
| **Regression Delta** | The net performance difference (F1, Kappa, or accuracy) between the baseline model and the candidate model. |
| **Cohen’s Kappa ($\kappa$)** | Statistical measure of agreement between the model's predictions and human coders, adjusted for chance agreement. |
| **Claim Deniability Risk Index (CDRI)** | A composite compliance score indicating the density of NCCI conflicts, wrong modifiers, and overcoded E/M levels. |

---

## Data Provenance & Safety
To ensure compliance and realistic benchmarking, the engine runs on a validation dataset composed of:
1. **Deidentified Clinical Notes**: Semi-structured clinical profiles inspired by the MIMIC-IV-Note database (discharge summaries and radiology reports).
2. **Specialty Transcripts**: Outpatient encounter notes representing clinical text patterns from MTSamples (e.g., Cardiology, Orthopedics).
3. **Synthetic Edge Cases**: Simulated safety-critical scenarios containing billing challenges such as Modifier 25 eligibility, NCCI mutually exclusive procedures, and levothyroxine dosage unit checks.
4. **Gold-Standard Labeled Truth**: A simulated consensus coder dataset acting as the ground-truth baseline.

---

## Operational Release Gate Logic
The automated release gate (`src/release_gate.py`) evaluates candidates before staging deployment. A candidate version will fail deployment if:
- **Modifier Accuracy Drops**: Any decrease in Modifier 25 accuracy compared to the baseline (`v1`).
- **HCC Misses Increase**: Any rise in missed Hierarchical Condition Categories.
- **Unit Confusion Rises**: Any instance of dosage unit confusion (`mg` vs. `mcg`).
- **Specialty Drift Exceeds Tolerance**: Specialty-level F1-score drop greater than $2\%$.

---

## Version Comparison
SynapseAudit tracks side-by-side performance of model configurations:
- **Baseline Version (v1)**: Matches the standard production configuration (e.g., stable system prompt).
- **Candidate Version (v2)**: Represents the updated candidate (e.g., modified system prompt or updated base model).
- **Drift by Specialty**: Captures where specific medical specialties (e.g., Cardiology, Orthopedics) degrade under prompt modifications.

---

## Explainable Audit Ledger
The audit workflow is designed to allow clinical review teams to trace decisions:
- **Clinical Note Segment**: The raw clinical text.
- **Evidence-Span Highlighting**: Visual highlights indicating exactly where the model matched a code.
- **Predicted vs. Gold Codes**: Comparison of extracted codes side-by-side.
- **Mismatch Reason**: Detailed error categories (e.g., `hcc_miss`, `wrong_modifier`, `unit_confusion`).
- **Reviewer Decision**: Interactive buttons to record Auditor agreement (`Agree` / `Disagree`).

---

## Project Impact
- **200+** Simulated and deidentified clinical notes audited.
- **7** Core compliance and accuracy metrics evaluated per model version.
- **4** Major automated billing rule engines (Modifier 25, NCCI, Unit Mismatch, HCC Gap).
- **1** Unified CLI release gate to prevent regression deployments.

---

## Quick Start Setup

### 1. Installation & Environment Setup
Clone the repository and install requirements:
```bash
git clone https://github.com/Navneet-Scaler/SynapsAudit.git
cd SynapsAudit
pip install -r requirements.txt
```

### 2. Database Initialization
Build the SQLite analytics database containing baseline and candidate records:
```bash
python3 data/mock_generator.py
```

### 3. Run Automated Tests
Verify compliance rules, metrics, and gate checks:
```bash
python3 -m pytest
```

### 4. Run Release Gate Check
Run the CLI gate to verify if candidate `v2` matches compliance rules:
```bash
python3 src/release_gate.py
```

### 5. Launch the Dashboard
Run the Streamlit dashboard:
```bash
python3 -m streamlit run dashboards/app.py
```
