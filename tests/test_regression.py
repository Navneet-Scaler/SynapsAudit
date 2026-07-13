from src.metrics import compute_classification_metrics, compute_cohens_kappa, calculate_financial_impact

def test_classification_metrics():
    # Exact match
    pred = {"I50.23", "93451"}
    gt = {"I50.23", "93451"}
    p, r, f1 = compute_classification_metrics(pred, gt)
    assert p == 1.0
    assert r == 1.0
    assert f1 == 1.0

    # Partial match
    pred = {"I50.23", "93451"}
    gt = {"I50.23"}
    p, r, f1 = compute_classification_metrics(pred, gt)
    assert p == 0.5
    assert r == 1.0
    assert abs(f1 - 0.6666) < 0.01

def test_cohens_kappa():
    # Complete agreement
    evals = [(1, 1), (1, 1), (0, 0), (0, 0)]
    k = compute_cohens_kappa(evals)
    assert k == 1.0

    # Mixed agreement
    evals = [(1, 1), (1, 0), (0, 1), (0, 0)]
    k = compute_cohens_kappa(evals)
    assert k == 0.0

def test_financial_impact():
    violations = [
        {"error_type": "hcc_miss"},
        {"error_type": "wrong_modifier"},
        {"error_type": "ncci_conflict"},
        {"error_type": "overcode"}
    ]
    impact = calculate_financial_impact(violations)
    assert impact["revenue_leakage"] == 2500.0
    assert impact["rejection_liability"] == 150.0 + 850.0 + 1200.0
    assert impact["max_ar_delay_days"] == 45
