"""Simple model router sketch for InvoiceMind.

Selects a model name (string) given document metadata. This is a lightweight
helper — replace decision rules with telemetry-driven policies in production.
"""
from typing import Dict

def select_model_for_extraction(doc_meta: Dict) -> str:
    """Return model key name from models.yaml for extraction tasks.

    doc_meta expected keys: language ("en"/"fa"), pages, has_tables (bool), quality ("low"/"high")
    """
    lang = doc_meta.get("language", "en")
    pages = int(doc_meta.get("pages", 1))
    has_tables = bool(doc_meta.get("has_tables", False))
    quality = doc_meta.get("quality", "high")

    # Simple routing rules
    if lang == "fa":
        # prefer Persian-specialized model for post-processing
        if has_tables:
            return "qwen2.5-7b-instruct"
        return "gemma-3-4b-persian"

    # for English or mixed
    if has_tables or pages > 3:
        # use stronger extraction model but still quantized
        return "qwen2.5-7b-instruct"

    # default fast path
    return "qwen2.5-7b-instruct"


def select_model_for_embeddings() -> str:
    return "Tooka-SBERT"


if __name__ == "__main__":
    # quick smoke example
    example = {"language": "fa", "pages": 2, "has_tables": False}
    print("Selected:", select_model_for_extraction(example))
