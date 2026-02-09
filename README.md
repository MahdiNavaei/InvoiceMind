# InvoiceMind

Local-LLM, Evidence-first, Audit-ready Invoice Processing

`InvoiceMind` یک پلتفرم دو‌زبانه (فارسی/انگلیسی) برای پردازش هوشمند فاکتور است که به‌صورت Local-First طراحی شده و چرخه کامل `upload -> extraction -> review/quarantine -> export` را با قابلیت ممیزی (Audit Trail) پوشش می‌دهد.

## Key Features

- FastAPI backend + Next.js frontend
- دو‌زبانه (FA/EN) با RTL/LTR
- Quality gates و تصمیم‌گیری `AUTO_APPROVED | NEEDS_REVIEW`
- Quarantine workflow با reason codes و reprocess
- Governance endpoints (audit verify, runtime versions, change risk, capacity estimate)
- Local model strategy با نسخه‌بندی config

## Tech Stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy, Alembic
- Frontend: Next.js 16, React 19, TypeScript
- Database: SQLite (default)
- Runtime: local-first (optional Ollama for GGUF)

## Quick Start (Windows)

```bat
run.bat
```

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:3000`

## Manual Run

### Backend

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/migrate.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Environment Setup

- Backend template: `.env.example`
- Frontend template: `frontend/.env.local.example`

## Tests

### Backend

```powershell
pytest
```

### Frontend

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

## API Surface (Main)

- Health: `GET /health`, `GET /ready`, `GET /metrics`
- Auth: `POST /v1/auth/token`
- Documents: `POST /v1/documents`, `GET /v1/documents/{document_id}`
- Runs: create/get/cancel/replay/export
- Quarantine: list/get/reprocess
- Governance: audit verify/events, runtime versions, change risk, capacity

## Documentation

تمام مستندات پروژه در یک فایل یکپارچه نگهداری می‌شود:

- `Docs/README.md`

## License & Security

- License: `AGPL-3.0` (`LICENSE`)
- Security Policy: `SECURITY.md`
