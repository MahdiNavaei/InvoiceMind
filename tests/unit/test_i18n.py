from app.i18n import pick_lang, t


def test_pick_lang_defaults_to_en():
    assert pick_lang(None) == "en"


def test_pick_lang_fa():
    assert pick_lang("fa-IR") == "fa"


def test_translation_works():
    assert t("health_ok", "en") == "Service is healthy."
    assert t("health_ok", "fa") == "سرویس سالم است."
