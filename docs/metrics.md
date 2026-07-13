# Clinical QA Validation Metrics Reference

This document defines the core performance and compliance metrics tracked by the SynapseAudit regression engine.

## Metric Glossary

- **Exact-Match Accuracy**: The percentage of clinical encounters where the model's predicted codes perfectly match the gold-standard codes.
- **Modifier Accuracy**: The percentage of eligible encounters where Modifier 25 is correctly attached to E/M codes when a separate procedure is performed.
- **Unit Accuracy**: The percentage of medication dosage matches where the predicted code matches the correct unit (e.g., `mcg` vs. `mg`).
- **HCC Capture Rate**: The percentage of gold-standard Hierarchical Condition Categories (HCCs) correctly captured by the model.
- **Regression Delta**: The net performance difference (F1, Kappa, or accuracy) between the baseline model and the candidate model.
- **Cohen’s Kappa ($\kappa$)**: Statistical measure of agreement between the model's predictions and human coders, adjusted for chance agreement.
- **Claim Deniability Risk Index (CDRI)**: A composite compliance score indicating the density of NCCI conflicts, wrong modifiers, and overcoded E/M levels.

---

## Formulations

### Cohen's Kappa ($\kappa$)
$$\kappa = \frac{p_o - p_e}{1 - p_e}$$
Where:
- $p_o$ is the relative observed agreement between the model's predicted code set and the gold-standard labels.
- $p_e$ is the hypothetical probability of random agreement.

### Claim Deniability Risk Index (CDRI)
$$\text{CDRI} = \frac{\text{NCCI Violations} \times 1.5 + \text{Wrong Modifier} \times 1.5 + \text{Overcoded E/M Level}}{\text{Total Encounters}}$$
A high CDRI indicates that model predictions introduce significant financial audit risks.
