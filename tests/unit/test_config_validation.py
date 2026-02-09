from app.config import Settings, validate_settings


def test_validate_settings_accepts_valid_config():
    cfg = Settings(
        environment="dev",
        execution_mode="background",
        queue_warn_depth=3,
        queue_reject_depth=6,
        max_stage_attempts=2,
        stage_timeout_seconds=10,
        run_timeout_seconds=30,
        worker_poll_seconds=0.5,
        worker_batch_size=2,
        low_confidence_threshold=0.5,
        low_ocr_confidence_threshold=0.5,
        required_field_coverage_threshold=0.8,
    )
    validate_settings(cfg)


def test_validate_settings_rejects_bad_queue_depth():
    cfg = Settings(queue_warn_depth=5, queue_reject_depth=5)
    try:
        validate_settings(cfg)
    except ValueError as exc:
        assert "QUEUE_REJECT_DEPTH" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_validate_settings_rejects_default_prod_secret():
    cfg = Settings(environment="prod", jwt_secret="change-this-in-prod")
    try:
        validate_settings(cfg)
    except ValueError as exc:
        assert "JWT_SECRET" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
