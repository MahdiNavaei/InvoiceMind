from app.services.change_management import classify_change_risk, evaluate_release_gate, runtime_version_snapshot


def test_runtime_version_snapshot_contains_hashes():
    snap = runtime_version_snapshot()
    assert "versions" in snap
    assert "artifact_hashes" in snap
    assert snap["versions"]["prompt_version"].startswith("PRM-")


def test_change_risk_classification():
    assert classify_change_risk(["model_version"]) == "high"
    assert classify_change_risk(["prompt"]) == "medium"
    assert classify_change_risk(["docs"]) == "low"


def test_release_gate_evaluation():
    baseline = {
        "doc_pass_rate": 0.95,
        "doc_critical_error_rate": 0.02,
        "critical_false_accept_rate": 0.0005,
    }
    candidate = {
        "doc_pass_rate": 0.951,
        "doc_critical_error_rate": 0.019,
        "critical_false_accept_rate": 0.0007,
    }
    result = evaluate_release_gate(metrics=candidate, baseline=baseline)
    assert result["passed"] is True
