# Model and Prompt Version Control

This document describes how SynapseAudit tracks version configurations and detects performance drift.

## 1. Version Configurations
The engine tracks performance parameters side-by-side across two distinct axes:
- **Model Version**: The base LLM or encoder version (e.g., `clinical-nlp-v1` vs. `clinical-nlp-v2`).
- **Prompt Version**: The instructions, system prompts, or few-shot exemplars (e.g., `sys_v1.0_baseline` vs. `sys_v1.1_modifier_boost`).

## 2. Version Comparison Matrices
By comparing baseline predictions with the candidate version, the system evaluates:
- **Specialty-Level F1 & Kappa Drift**: Tracking whether prompt optimizations for one specialty (e.g., Oncology) cause regressions in another (e.g., Cardiology).
- **Code Family Drift**: Monitoring frequency shifts in common billing code families (e.g., CPT E/M codes `99213` and `99214`) to identify artificial upcoding trends.

## 3. Why Version Comparison Matters
Without offline version comparison, prompt tuning or model updates introduce silent regressions:
- A change to improve cardiology extraction might cause a loss of modifier rule triggers in general outpatient notes.
- Slight phrasing changes can cause the model to mismatch dosage units, presenting a severe risk to downstream clinical safety checks.
- Comparison matrices identify exactly *did* it get worse, *where* did it get worse, and *why* it got worse, allowing clinical analysts to audit the candidate.
