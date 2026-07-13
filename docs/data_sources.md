# Clinical Data Provenance & Safety Frame

This document details the source data and dataset construction used to evaluate NLP model variants under SynapseAudit.

## 1. MIMIC-IV-Note (Deidentified Grounding)
MIMIC-IV-Note serves as the clinical grounding baseline for simulating semi-structured hospital encounters:
- **Discharge Summaries**: Detailed text containing reason for admission, hospital course, final discharge diagnoses (used to evaluate ICD-10 extraction), and medications.
- **Radiology Reports**: Imaging descriptions with anatomical findings and procedure details (used to benchmark CPT procedure extraction).

## 2. MTSamples (Specialty Transcripts)
Ambulatory care and specialty note transcripts are modeled after MTSamples patterns. These represent specialty outpatient visits (e.g., Cardiology, Orthopedics, Endocrinology) where clinical billing modifier triggers frequently appear.

## 3. Synthetic Edge-Cases
To protect compliance integrity and simulate safety-critical failures, a set of synthetic edge cases is generated:
- **Modifier 25 Trigger Scenarios**: Notes documenting an E/M visit and a minor procedure performed on the same day to evaluate modifier placement.
- **NCCI Mutually Exclusive Procedures**: Notes containing clinical descriptors of procedures that cannot be billed together on the same day.
- **Dosage Unit Confusions**: Edge cases designed with unit hazards (e.g., `mg` vs `mcg` for levothyroxine, or insulin units) to test entity extraction precision.
- **CMS HCC Risk Indicators**: Notes detailing chronic diseases (e.g., diabetes complications, Stage III/IV CKD) that map to CMS Hierarchical Condition Categories (HCCs).

---

> [!IMPORTANT]
> **Safety and Compliance Disclaimer**  
> All patient records, note text, and clinical histories in this repository are synthetic, simulated, or derived from deidentified open benchmarks. This dataset is designed strictly for **offline clinical NLP validation and prompt regression testing**. It is not intended, approved, or compliant for live patient billing or real-time clinical intervention.
