-- SynapseAudit SQL Compliance & Drift Analysis Queries
-- Designed for PostgreSQL/SQLite-compatible clinical analytics

-- ==========================================
-- 1. Model Version Drift by Specialty
-- ==========================================
-- Business Question:
-- Which medical specialties are experiencing the highest rate of audit errors and code drift under the candidate model?
-- Expected Columns:
--   - model_version: Model identifier under evaluation (e.g., v1 baseline vs v2 candidate).
--   - prompt_version: Prompt configuration version.
--   - specialty: The clinical specialty area (e.g., Cardiology, Orthopedics).
--   - error_type: Category of compliance check failed.
--   - error_count: Total counts of that error category.
--   - total_records: Volume of records evaluated in this cohort.
--   - error_rate: Normalized rate of errors (error_count / total_records).
--   - risk_index: Average clinical billing liability risk score for this specialty segment.
-- Interpretation:
--   Look for high error_rates (>0.05) or sudden increases in error counts between model versions within a specialty (e.g., a candidate model regressing in Cardiology).
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
ORDER BY e.specialty, error_rate DESC;


-- ==========================================
-- 2. HCC Miss Rate by Chronic Condition
-- ==========================================
-- Business Question:
-- How frequently is the candidate model failing to document Hierarchical Condition Categories (HCCs) present in gold-standard records, resulting in potential under-billing?
-- Expected Columns:
--   - model_version: Model identifier.
--   - prompt_version: Prompt config version.
--   - error_count: Count of missed HCC condition incidents ('hcc_miss').
--   - total_records: Total records evaluated.
--   - error_rate: Proportion of records with missed HCCs.
-- Interpretation:
--   An increase in error_rate under a candidate model represents a negative regression where chronic conditions are dropped, leading to reduced risk adjustment factor (RAF) scores.
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
GROUP BY p.model_version, p.prompt_version;


-- ==========================================
-- 3. Unit Mismatch Frequency (Unit Confusion)
-- ==========================================
-- Business Question:
-- What is the rate of dosage unit confusion (e.g. mg vs mcg) predicted by different model configurations?
-- Expected Columns:
--   - model_version: Model identifier.
--   - prompt_version: Prompt config version.
--   - error_count: Counts of dosage unit confusion errors ('unit_confusion').
--   - total_records: Total records evaluated.
--   - error_rate: Frequency of unit confusion incidents.
-- Interpretation:
--   Any error_rate > 0% in this category represents a clinical safety risk where dosage units were incorrectly matched. This should block candidate release.
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
GROUP BY p.model_version, p.prompt_version;


-- ==========================================
-- 4. Modifier Failure Rate
-- ==========================================
-- Business Question:
-- How often does the candidate model fail to attach correct modifiers (e.g., Modifier 25) when billing procedures alongside E/M services?
-- Expected Columns:
--   - model_version: Model identifier.
--   - prompt_version: Prompt config version.
--   - error_count: Counts of incorrect/omitted modifiers.
--   - total_records: Total records evaluated.
--   - error_rate: Frequency of modifier billing violations.
-- Interpretation:
--   High error_rate in this query indicates the model is omitting modifiers, causing immediate claim rejections and billing compliance issues.
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
GROUP BY p.model_version, p.prompt_version;


-- ==========================================
-- 5. Claim Deniability Risk Index (CDRI)
-- ==========================================
-- Business Question:
-- What is the aggregate Claim Deniability Risk Index (CDRI) across model and prompt versions?
-- Expected Columns:
--   - model_version: Model identifier.
--   - prompt_version: Prompt config version.
--   - claim_deniability_risk_index: Weighted score of total coding conflicts (NCCI, Wrong Modifier, E/M overcode).
-- Interpretation:
--   A score < 0.10 is acceptable. Any increase in CDRI compared to the baseline indicates higher billing denial risk.
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
GROUP BY p.model_version, p.prompt_version;


-- ==========================================
-- 6. Model-to-Model Regression Comparison
-- ==========================================
-- Business Question:
-- Which specific patient records show discrepancies between the baseline model predictions and the candidate model?
-- Expected Columns:
--   - record_id: Patient/encounter unique identifier.
--   - v1_codes: predicted codes under baseline v1.
--   - v2_codes: predicted codes under candidate v2.
--   - ground_truth_codes: The human-adjudicated coder baseline.
-- Interpretation:
--   Identify individual edge cases where the candidate model v2 lost correct matches that v1 successfully extracted.
SELECT
    v1.record_id,
    v1.predicted_codes AS v1_codes,
    v2.predicted_codes AS v2_codes,
    e.ground_truth_codes
FROM model_predictions v1
JOIN model_predictions v2 ON v1.record_id = v2.record_id AND v1.model_version = 'clinical-nlp-v1' AND v2.model_version = 'clinical-nlp-v2'
JOIN clinical_encounters e ON v1.record_id = e.record_id
WHERE v1.predicted_codes != v2.predicted_codes;
