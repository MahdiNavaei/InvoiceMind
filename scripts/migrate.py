from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings

REQUIRED_BASE_TABLES = {"documents", "runs", "run_stages"}
BASELINE_REVISION = "20260209_0001"


def _run_alembic(*args: str) -> int:
    cmd = [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), *args]
    completed = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return completed.returncode


def _schema_state() -> tuple[bool, bool]:
    """Return (has_base_schema, has_valid_version_row)."""
    try:
        engine = create_engine(
            settings.db_url,
            connect_args={"check_same_thread": False} if settings.db_url.startswith("sqlite") else {},
        )
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        has_base = REQUIRED_BASE_TABLES.issubset(tables)

        has_version_table = "alembic_version" in tables
        has_version_row = False
        if has_version_table:
            with engine.connect() as conn:
                rows = list(conn.execute(text("select version_num from alembic_version")))
                has_version_row = len(rows) > 0
        engine.dispose()
    except Exception:  # noqa: BLE001
        return False, False

    return has_base, has_version_row


def _is_existing_schema_without_version() -> bool:
    has_base, has_version_row = _schema_state()
    return has_base and not has_version_row


def main() -> None:
    if _is_existing_schema_without_version():
        rc = _run_alembic("stamp", BASELINE_REVISION)
        if rc != 0:
            raise SystemExit(rc)
        rc = _run_alembic("upgrade", "head")
        if rc != 0:
            raise SystemExit(rc)
        print("Migration applied: existing schema stamped to baseline and upgraded to head")
        return

    rc = _run_alembic("upgrade", "head")
    if rc == 0:
        print("Migration applied: alembic upgrade head")
        return

    # Legacy bootstrap fallback: schema may already exist; stamp as head.
    if _is_existing_schema_without_version():
        rc2 = _run_alembic("stamp", "head")
        if rc2 == 0:
            print("Migration applied: fallback stamp head for existing schema")
            return
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
