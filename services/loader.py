"""Model loader helper (instructions only).

This module does NOT execute heavy model loads. It scans `models.yaml` and
returns recommended backends and command templates or Python snippets to load
models locally using common runtimes (Ollama import/run, transformers, or a
ggml-based runner). The intent is to provide safe, reproducible instructions
for local-only deployments on Windows.
"""
import os
import yaml
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(__file__))
MODELS_YAML = os.path.join(ROOT, "models.yaml")


def load_models_index(path: Optional[str] = None) -> Dict:
    path = path or MODELS_YAML
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def list_models() -> List[Dict]:
    idx = load_models_index()
    return idx.get('models', [])


def find_model(name: str) -> Optional[Dict]:
    for m in list_models():
        if m.get('name') == name:
            return m
    return None


def recommend_backend(model: Dict) -> Dict:
    """Return a recommended backend and command snippets for local use.

    Returns a dict with keys: backend, notes, commands.
    """
    fname = model.get('file')
    fmt = model.get('format', '').lower()

    # Normalize detection
    if isinstance(fname, str) and fname.endswith('.gguf') or 'gguf' in fmt:
        backend = 'gguf/ollama/ggml'
        commands = [
            '# Ollama: import then run (if using Ollama runtime)',
            'ollama import <path_to_model_file> --name <alias>',
            'ollama run <alias> --prompt "..."'
        ]
        notes = 'GGUF quantized models are best used with an Ollama-like runtime or a GGML runner supporting GGUF. Test memory usage first.'
        return {'backend': backend, 'notes': notes, 'commands': commands}

    if isinstance(fname, str) and ('.safetensors' in fname or 'safetensors' in fmt):
        backend = 'transformers/accelerate or vLLM'
        commands = [
            '# Example (transformers):',
            'from transformers import AutoTokenizer, AutoModelForCausalLM',
            "tokenizer = AutoTokenizer.from_pretrained('<path_or_repo>')",
            "model = AutoModelForCausalLM.from_pretrained('<path_or_repo>', device_map='auto')",
        ]
        notes = 'safetensors weights typically load via Transformers or a fine-tuned vLLM runtime. Consider quantized GGUF for small-GPU devices.'
        return {'backend': backend, 'notes': notes, 'commands': commands}

    # Fallback
    return {
        'backend': 'unknown',
        'notes': 'Model format unrecognized; inspect file extension and choose appropriate runtime (Ollama, transformers, ggml).',
        'commands': []
    }


def get_instructions_for(name: str) -> Dict:
    m = find_model(name)
    if not m:
        return {'error': 'model not found'}
    rec = recommend_backend(m)
    return {'model': m, 'recommendation': rec}


if __name__ == '__main__':
    print('Available models:')
    for m in list_models():
        print('-', m.get('name'))
    print('\nExample instructions for qwen2.5-7b-instruct:')
    import json
    print(json.dumps(get_instructions_for('qwen2.5-7b-instruct'), indent=2, ensure_ascii=False))
