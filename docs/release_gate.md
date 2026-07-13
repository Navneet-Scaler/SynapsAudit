# Operational Release Gate Policy

To prevent prompt or model changes from causing silent performance regressions in production, all updates must pass the automated release gate (`src/release_gate.py`).

## Gate Evaluation Rules

A candidate version (e.g., `v2` prompt configuration or updated LLM weights) is automatically blocked from release if any of the following rules are violated:

1. **Modifier Accuracy Regression Rule**: The candidate's Modifier 25 accuracy must be greater than or equal to the baseline model (`v1`) accuracy.
2. **HCC Capture Rate Rule**: The candidate's Hierarchical Condition Category (HCC) capture rate must not drop compared to the baseline (`v1`).
3. **Unit Confusion Tolerance Rule**: The dosage unit mismatch rate must be exactly $0\%$. Any instance of unit confusion (e.g., matching `mg` instead of `mcg` or vice versa) results in an immediate failure.
4. **Specialty F1 Drift Rule**: The candidate's F1-score for any individual specialty cohort (e.g., Cardiology, Orthopedics) must not degrade by more than $2\%$ compared to the baseline.
5. **Deniability Risk threshold Rule**: The Claim Deniability Risk Index (CDRI) of the candidate model must be less than or equal to $0.10$.

## Execution in CI/CD Pipelines
The release validator CLI checks these rules programmatically:
```bash
python3 src/release_gate.py
```
If any of the blocking rules fail, the script exits with code `1`, halting the CI/CD deployment pipeline.
