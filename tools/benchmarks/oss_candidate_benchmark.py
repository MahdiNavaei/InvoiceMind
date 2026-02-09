from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.extraction import (
    decide_final_status,
    detect_language,
    run_ocr,
    run_structured_extraction,
    validate_result,
)

DEFAULT_OUT = (
    ROOT
    / "Docs"
    / "Phases"
    / "Reports"
    / "Phase_03_Extraction_Pipeline_and_Orchestration"
    / "OSS_Benchmark_Report.md"
)


def _candidate_status() -> list[dict[str, str]]:
    candidates = [
        ("invoice2data", ROOT / "external" / "invoice2data"),
        ("docTR", ROOT / "external" / "doctr"),
        ("docling", ROOT / "external" / "docling"),
        ("Arshasb-meta", ROOT / "external" / "arshasb-meta"),
    ]
    out: list[dict[str, str]] = []
    for name, path in candidates:
        out.append(
            {
                "candidate": name,
                "clone_present": "YES" if path.exists() else "NO",
                "path": str(path.relative_to(ROOT)) if path.exists() else str(path),
            }
        )
    return out


def _sample_paths() -> list[Path]:
    candidates = [
        ROOT / "tests" / "e2e" / "sample_invoice.png",
        ROOT / "external" / "arshasb-meta" / "page_08734.png",
    ]
    return [p for p in candidates if p.exists()]


def _run_pipeline_on_sample(path: Path) -> dict[str, Any]:
    language = detect_language(path.name)

    t0 = time.perf_counter()
    ocr = run_ocr(str(path), path.name)
    ocr_ms = round((time.perf_counter() - t0) * 1000, 2)

    t1 = time.perf_counter()
    extracted = run_structured_extraction(
        text=ocr.text,
        filename=path.name,
        language=language,
        file_path=str(path),
        ocr_confidence=ocr.confidence,
    )
    extract_ms = round((time.perf_counter() - t1) * 1000, 2)

    issues = validate_result(
        extracted.result,
        extraction_confidence=extracted.confidence,
        ocr_confidence=ocr.confidence,
    )
    final_status, reasons = decide_final_status(
        extracted.result,
        issues,
        extraction_confidence=extracted.confidence,
        ocr_confidence=ocr.confidence,
    )

    return {
        "sample": str(path.relative_to(ROOT)),
        "language": language,
        "ocr_provider": ocr.provider,
        "ocr_confidence": round(ocr.confidence, 4),
        "ocr_latency_ms": ocr_ms,
        "extraction_provider": extracted.provider,
        "model_name": extracted.model_name,
        "route_name": extracted.route_name,
        "extraction_confidence": round(extracted.confidence, 4),
        "extract_latency_ms": extract_ms,
        "issue_count": len(issues),
        "final_status": final_status,
        "reason_codes": reasons,
    }


def build_report() -> tuple[str, dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    candidates = _candidate_status()
    samples = _sample_paths()
    results = [_run_pipeline_on_sample(path) for path in samples]

    payload = {
        "generated_at_utc": now,
        "candidates": candidates,
        "results": results,
    }

    lines: list[str] = []
    lines.append("# OSS Benchmark Report (Phase 03)")
    lines.append("")
    lines.append(f"Generated at (UTC): `{now}`")
    lines.append("")
    lines.append("## Candidate Availability")
    lines.append("")
    lines.append("| Candidate | Clone Present | Path |")
    lines.append("|---|---|---|")
    for row in candidates:
        lines.append(f"| {row['candidate']} | {row['clone_present']} | `{row['path']}` |")
    lines.append("")

    lines.append("## Pipeline Benchmark Samples")
    lines.append("")
    lines.append(
        "| Sample | OCR Provider | OCR Conf | OCR ms | Extraction Provider | Model | Route | Ext Conf | Ext ms | Issues | Final Status |"
    )
    lines.append("|---|---|---:|---:|---|---|---|---:|---:|---:|---|")
    for row in results:
        lines.append(
            f"| `{row['sample']}` | {row['ocr_provider']} | {row['ocr_confidence']} | {row['ocr_latency_ms']} | "
            f"{row['extraction_provider']} | {row['model_name']} | {row['route_name']} | {row['extraction_confidence']} | "
            f"{row['extract_latency_ms']} | {row['issue_count']} | {row['final_status']} |"
        )
    lines.append("")

    lines.append("## Notes")
    lines.append("- `invoice2data` is probed in extraction adapter and used when a valid result is returned.")
    lines.append("- If external OCR/model deps are unavailable, deterministic and heuristic fallbacks keep the pipeline runnable.")
    lines.append("- This report is intended for reproducible local MVP benchmarking.")
    lines.append("")

    return "\n".join(lines) + "\n", payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 03 OSS benchmark report.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Markdown output path")
    parser.add_argument("--json-out", default=None, help="Optional JSON output path")
    args = parser.parse_args()

    markdown, payload = build_report()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote report: {out_path}")

    if args.json_out:
        json_out = Path(args.json_out)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote JSON: {json_out}")


if __name__ == "__main__":
    main()
