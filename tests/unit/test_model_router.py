from services.model_router import select_model_for_extraction


def test_router_prefers_persian_model_for_fa_without_tables():
    assert select_model_for_extraction({"language": "fa", "pages": 1, "has_tables": False}) == "gemma-3-4b-persian"


def test_router_prefers_qwen_for_tables():
    assert select_model_for_extraction({"language": "fa", "pages": 1, "has_tables": True}) == "qwen2.5-7b-instruct"


def test_router_default_is_qwen_for_en():
    assert select_model_for_extraction({"language": "en", "pages": 1, "has_tables": False}) == "qwen2.5-7b-instruct"
