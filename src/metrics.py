import numpy as np

def compute_classification_metrics(predicted_set, ground_truth_set):
    """
    predicted_set: set of predicted codes
    ground_truth_set: set of ground truth codes
    """
    if not predicted_set and not ground_truth_set:
        return 1.0, 1.0, 1.0
        
    tp = len(predicted_set.intersection(ground_truth_set))
    fp = len(predicted_set - ground_truth_set)
    fn = len(ground_truth_set - predicted_set)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return precision, recall, f1

def compute_cohens_kappa(evaluations):
    """
    evaluations: List of tuples (coder1_agreed, coder2_agreed) where values are 1 (agree) or 0 (disagree).
    If evaluations is empty or all constant, returns 1.0 or 0.0 accordingly.
    """
    if not evaluations:
        return 1.0
    
    n = len(evaluations)
    c1 = [x[0] for x in evaluations]
    c2 = [x[1] for x in evaluations]
    
    # Observed agreement
    po = sum(1 for x, y in evaluations if x == y) / n
    
    # Probability of random agreement
    c1_yes = sum(c1) / n
    c1_no = 1 - c1_yes
    c2_yes = sum(c2) / n
    c2_no = 1 - c2_yes
    
    pe = (c1_yes * c2_yes) + (c1_no * c2_no)
    
    if pe == 1.0:
        return 1.0
        
    kappa = (po - pe) / (1 - pe)
    return kappa

def calculate_cdri(num_violations, num_records, num_overcoded_em=0):
    """
    CDRI = (Violations * 1.5 + Overcoded E/M) / Total Records
    """
    if num_records == 0:
        return 0.0
    return (num_violations * 1.5 + num_overcoded_em) / num_records

def calculate_financial_impact(violations):
    """
    Computes financial impact from a list of compliance violations:
    - hcc_miss: under-coding, causing $2,500 of annual revenue leakage.
    - wrong_modifier: modifier omission, causing $150 in admin rework costs and 45 days of payment delay.
    - ncci_conflict: mutually exclusive procedures, causing $850 in denied claims.
    - overcode: E/M over-coding, causing $1,200 in audit liability.
    """
    revenue_leakage = 0.0
    rejection_liability = 0.0
    max_ar_delay_days = 0
    
    for v in violations:
        error_type = v.get("error_type", "")
        if error_type == "hcc_miss":
            revenue_leakage += 2500.0
        elif error_type == "wrong_modifier":
            rejection_liability += 150.0
            max_ar_delay_days = max(max_ar_delay_days, 45)
        elif error_type == "ncci_conflict":
            rejection_liability += 850.0
            max_ar_delay_days = max(max_ar_delay_days, 30)
        elif error_type == "overcode":
            rejection_liability += 1200.0
            
    return {
        "revenue_leakage": revenue_leakage,
        "rejection_liability": rejection_liability,
        "max_ar_delay_days": max_ar_delay_days
    }
