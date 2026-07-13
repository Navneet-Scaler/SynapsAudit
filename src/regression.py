import pandas as pd
import os
import sqlite3
from src.metrics import compute_classification_metrics, calculate_financial_impact

class RegressionEngine:
    def __init__(self, loader):
        self.loader = loader

    def compare_versions(self, v1_model="clinical-nlp-v1", v2_model="clinical-nlp-v2"):
        """
        Compare metrics between two model/prompt versions.
        """
        encounters = self.loader.load_encounters()
        predictions = self.loader.load_predictions()
        
        v1_preds = predictions[predictions["model_version"] == v1_model]
        v2_preds = predictions[predictions["model_version"] == v2_model]
        
        merged_v1 = pd.merge(encounters, v1_preds, on="record_id")
        merged_v2 = pd.merge(encounters, v2_preds, on="record_id")
        
        comparison = {}
        specialties = encounters["specialty"].unique()
        
        for spec in specialties:
            v1_spec = merged_v1[merged_v1["specialty"] == spec]
            v2_spec = merged_v2[merged_v2["specialty"] == spec]
            
            # Compute macro-metrics for v1
            v1_f1s = []
            for _, row in v1_spec.iterrows():
                pred = set(c.strip() for c in row["predicted_codes"].split(",") if c.strip())
                gt = set(c.strip() for c in row["ground_truth_codes"].split(",") if c.strip())
                _, _, f1 = compute_classification_metrics(pred, gt)
                v1_f1s.append(f1)
                
            # Compute macro-metrics for v2
            v2_f1s = []
            regressions = 0
            for _, row in v2_spec.iterrows():
                pred = set(c.strip() for c in row["predicted_codes"].split(",") if c.strip())
                gt = set(c.strip() for c in row["ground_truth_codes"].split(",") if c.strip())
                _, _, f1 = compute_classification_metrics(pred, gt)
                v2_f1s.append(f1)
                
                # Check for direct regression (if v1 matched a code that v2 missed)
                v1_row = v1_spec[v1_spec["record_id"] == row["record_id"]]
                if not v1_row.empty:
                    v1_pred = set(c.strip() for c in v1_row.iloc[0]["predicted_codes"].split(",") if c.strip())
                    v1_matched = v1_pred.intersection(gt)
                    v2_matched = pred.intersection(gt)
                    if len(v1_matched - v2_matched) > 0:
                        regressions += 1
            
            # Calculate financial metrics for v1 and v2 in this specialty
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            db_path = os.path.join(project_root, "data", "synapse_audit.db")
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT record_id, model_version, error_type, risk_score FROM compliance_audit_results")
            all_violations = cursor.fetchall()
            conn.close()

            v1_rec_ids = set(v1_spec["record_id"])
            v2_rec_ids = set(v2_spec["record_id"])
            
            v1_violations = [{"error_type": error_type, "risk_score": risk_score} 
                             for rec_id, model_version, error_type, risk_score in all_violations 
                             if model_version == v1_model and rec_id in v1_rec_ids]
            
            v2_violations = [{"error_type": error_type, "risk_score": risk_score} 
                             for rec_id, model_version, error_type, risk_score in all_violations 
                             if model_version == v2_model and rec_id in v2_rec_ids]
            
            v1_fin = calculate_financial_impact(v1_violations)
            v2_fin = calculate_financial_impact(v2_violations)

            comparison[spec] = {
                "v1_f1": round(v1_avg_f1, 4),
                "v2_f1": round(v2_avg_f1, 4),
                "delta": round(v2_avg_f1 - v1_avg_f1, 4),
                "regression_records_count": regressions,
                "v1_leakage": v1_fin["revenue_leakage"],
                "v2_leakage": v2_fin["revenue_leakage"],
                "v1_liability": v1_fin["rejection_liability"],
                "v2_liability": v2_fin["rejection_liability"],
                "v1_ar_delay": v1_fin["max_ar_delay_days"],
                "v2_ar_delay": v2_fin["max_ar_delay_days"],
            }
            
        return comparison
