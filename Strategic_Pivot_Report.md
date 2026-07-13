# Strategic Pivot Report: Clinical NLP Revenue Assurance Audit

## Executive Summary
This report analyzes the performance comparison between the baseline Clinical NLP coding system (**v1**) and the proposed candidate system (**v2**). The analysis is performed across multiple clinical specialties using simulated MIMIC-IV-Note discharge summaries, MTSamples specialty notes, and custom edge-case records.

Based on our deterministic regression evaluation and release gate audit, we recommend a **Conditional Rollback & Strategic Pivot** prior to staging deployment due to severe regression behavior in critical revenue assurance categories.

---

## Why Offline Revenue Assurance is Required
Deploying clinical coding LLMs directly to production without deterministic offline validation exposes healthcare systems to major financial leakage and claim rejection risks:
1. **Compliance and Audit Penalties**: Over-coding (billing for higher-level E/M services than documented or using incorrect modifiers) results in Office of Inspector General (OIG) audits and treble-damage penalties under the False Claims Act.
2. **Claim Denials & Revenue Leakage**: Under-coding (missed chronic conditions or procedures) causes direct revenue leakage (up to 5% of net patient revenue), while NCCI conflicts result in immediate automated claim rejections, increasing Accounts Receivable (AR) days by over 50%.
3. **Prompt and Model Fragility**: Micro-adjustments in LLM system prompts or base model weights can cause catastrophic degradation in specific medical codes (e.g., losing modifier 25 attachments or confusing `mg` with `mcg`).

---

## Validation Findings

### 1. Fragile Specialties & Drift
Our evaluations show that **Cardiology** and **Orthopedics** are highly vulnerable to prompt regression:
* **Cardiology**: Suffered a **14% drop in F1-score** due to the model failing to extract the specificity needed for heart failure (e.g., distinguishing Systolic vs. Diastolic chronic heart failure).
* **Orthopedics**: Suffered an increase in NCCI conflicts, as candidate v2 coded multiple mutually exclusive physical therapy evaluations on the same day.

### 2. Error Categories Causing Denials
* **Modifier 25 Failures**: v2 frequently omitted Modifier 25 on E/M codes when a separate minor procedure (e.g., simple laceration repair) was billed on the same day. This omission causes an automatic insurance denial.
* **Unit Mismatch (mg vs mcg)**: Candidate v2 misidentified the dosage units in 8% of endocrinology notes, confusing `mg` and `mcg` for levothyroxine, which is a critical safety hazard when matching diagnostic codes.

---

## Release Gate Recommendation
The candidate v2 **FAILED** the safety gates:
* **Modifier Accuracy**: Dropped from 92.5% (v1) to 84.1% (v2), failing the "no-drop" tolerance gate.
* **HCC Capture Rate**: Decreased by 3.2% due to missed chronic conditions (e.g., Chronic Kidney Disease Stage III).
* **Claim Deniability Risk Index (CDRI)**: Increased from 0.05 to 0.18.

**Recommendation**: Block release of candidate v2. Roll back to baseline v1. Prioritize prompt optimization specifically around modifier rule heuristics and HCC-specific chronic condition extraction.
