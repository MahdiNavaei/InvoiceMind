from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASES_DIR = ROOT / "Docs" / "Phases"
REPORTS_DIR = PHASES_DIR / "Reports"


def extract_mandatory_docs(phase_file: Path) -> list[str]:
    lines = phase_file.read_text(encoding="utf-8").splitlines()
    docs: list[str] = []
    capture = False
    for line in lines:
        if line.strip().startswith("## Mandatory Doc Coverage"):
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture and line.strip().startswith("- `") and line.strip().endswith("`"):
            docs.append(line.strip()[3:-1])
    return docs


def short_hash(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return h[:12]


def main() -> None:
    for phase_file in sorted(PHASES_DIR.glob("Phase_*.md")):
        docs = extract_mandatory_docs(phase_file)
        phase_name = phase_file.stem
        out_dir = REPORTS_DIR / phase_name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "Doc_Coverage_Evidence.md"

        rows = []
        for rel in docs:
            p = ROOT / rel
            rows.append(
                (
                    rel,
                    "YES" if p.exists() else "NO",
                    p.stat().st_mtime if p.exists() else 0,
                    short_hash(p) if p.exists() else "-",
                )
            )

        rows.sort(key=lambda x: x[0].lower())

        lines = [
            f"# Doc Coverage Evidence — {phase_name}",
            "",
            "| Document | Exists | SHA256(12) |",
            "|---|---|---|",
        ]
        for doc, exists, _, h in rows:
            lines.append(f"| `{doc}` | {exists} | `{h}` |")

        lines.append("")
        lines.append(f"Total mandatory docs: {len(rows)}")
        lines.append(f"Present docs: {sum(1 for _, e, _, _ in rows if e == 'YES')}")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Generated: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
