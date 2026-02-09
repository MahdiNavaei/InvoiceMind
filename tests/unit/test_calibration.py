from app.services.calibration import (
    brier_score,
    expected_calibration_error,
    fit_isotonic,
    fit_platt_scaler,
    sweep_risk_threshold,
)


def test_isotonic_and_platt_produce_probabilities():
    scores = [0.1, 0.2, 0.4, 0.8, 0.9]
    labels = [0, 0, 0, 1, 1]
    iso = fit_isotonic(scores, labels)
    platt = fit_platt_scaler(scores, labels, epochs=200)
    assert 0.0 <= iso.predict(0.5) <= 1.0
    assert 0.0 <= platt.predict(0.5) <= 1.0


def test_calibration_metrics_and_threshold_sweep():
    probs = [0.1, 0.3, 0.7, 0.9]
    labels = [0, 0, 1, 1]
    ece = expected_calibration_error(probs, labels)
    brier = brier_score(probs, labels)
    assert ece >= 0.0
    assert brier >= 0.0

    risks = [1 - p for p in probs]
    picked = sweep_risk_threshold(
        risks=risks,
        critical_error_labels=[1 if y == 0 else 0 for y in labels],
        critical_false_accept_ceiling=0.5,
        thresholds=[0.2, 0.4, 0.6, 0.8],
    )
    assert "threshold" in picked
    assert 0.0 <= picked["review_ratio"] <= 1.0
