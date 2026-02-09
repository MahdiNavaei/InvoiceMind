# InvoiceMind Documentation

This document is the single technical documentation entry point for the `InvoiceMind` repository.

## 1) Project Summary

`InvoiceMind` is a bilingual invoice intelligence platform designed for local-first processing.
It covers the full lifecycle of invoice handling:

- ingestion
- quality validation
- extraction
- policy-based routing
- human review and correction
- export and audit traceability

Core design principles:

- **Local-first runtime** for privacy and cost control
- **Evidence-first decisions** for defensibility
- **Audit-ready operations** through immutable audit events
- **Operational clarity** with explicit quarantine and reprocess paths

## 2) System Topology

### Backend (`app/`)

- FastAPI service with versioned routes under `/v1`
- SQLAlchemy persistence layer
- Orchestrator-driven run lifecycle
- Governance and audit endpoints

### Frontend (`frontend/`)

- Next.js App Router application
- English/Persian interface (`/en/*`, `/fa/*`)
- Queue-based operations for runs and quarantine
- Governance-focused pages for runtime and audit visibility

### Config Bundles (`config/`)

Versioned runtime artifacts:

- `prompts/`
- `templates/`
- `routing/`
- `policies/`
- `models/`
- `active_versions.yaml`

These define the active extraction and decisioning behavior without changing core service code.

## 3) Runtime Data and Storage

Default storage root:

- `INVOICEMIND_STORAGE_ROOT=app/storage`

Subdirectories:

- `app/storage/raw` for uploaded document bytes
- `app/storage/runs` for run outputs and intermediate artifacts
- `app/storage/quarantine` for quarantined payloads and metadata
- `app/storage/audit` for audit event logs

Operational note:

- storage artifacts are runtime outputs and should not be committed to Git.

## 4) Environment Configuration

### Backend

Start from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Critical environment variables:

- application/runtime: `INVOICEMIND_ENV`, `INVOICEMIND_EXECUTION_MODE`
- persistence: `INVOICEMIND_DB_URL`, `INVOICEMIND_STORAGE_ROOT`
- quality gates: confidence and coverage thresholds
- governance versions: prompt/template/routing/policy/model versions
- security: JWT secret and token policy

### Frontend

Start from `frontend/.env.local.example`:

```powershell
Copy-Item frontend/.env.local.example frontend/.env.local
```

Required values:

- `INVOICEMIND_API_BASE_URL`
- `INVOICEMIND_API_USERNAME`
- `INVOICEMIND_API_PASSWORD`

## 5) Local LLM and Model Management

Model metadata is tracked in:

- `models.yaml`

Runtime versioning is tracked in:

- `config/active_versions.yaml`
- `config/models/<MODEL_VERSION>/model.yaml`

Recommended operational pattern:

1. Keep model metadata in Git.
2. Keep large model weight files outside Git.
3. Pin model/runtime versions in environment variables.
4. Update policy/routing/template versions together when behavior changes.

Optional GGUF runtime example:

```powershell
ollama import <path-to-gguf> --name invoicemind-extractor
ollama run invoicemind-extractor --prompt "extract invoice fields"
```

## 6) API Overview

### Health

- `GET /health`
- `GET /ready`
- `GET /metrics`

### Authentication

- `POST /v1/auth/token`

### Document and Run Processing

- `POST /v1/documents`
- `GET /v1/documents/{document_id}`
- `POST /v1/documents/{document_id}/runs`
- `GET /v1/runs/{run_id}`
- `POST /v1/runs/{run_id}/cancel`
- `POST /v1/runs/{run_id}/replay`
- `GET /v1/runs/{run_id}/export`

### Quarantine

- `GET /v1/quarantine`
- `GET /v1/quarantine/{item_id}`
- `POST /v1/quarantine/{item_id}/reprocess`

### Governance and Audit

- `GET /v1/audit/verify`
- `GET /v1/audit/events`
- `GET /v1/governance/runtime-versions`
- `POST /v1/governance/change-risk`
- `POST /v1/governance/capacity-estimate`

## 7) Local Development Workflow

### One-click (Windows)

```bat
run.bat
```

### Manual

Backend:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/migrate.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## 8) Testing and Release Readiness

Backend tests:

```powershell
pytest
```

Frontend checks:

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

Suggested pre-release checks:

- service health and readiness endpoints respond correctly
- upload-to-export workflow succeeds in both `/en` and `/fa` routes
- quarantine and reprocess operations work end-to-end
- audit chain verification returns valid status
- frontend production build completes without errors

## 9) Security and Compliance Notes

- Follow `SECURITY.md` for vulnerability reporting.
- Use non-default JWT secret in staging/production.
- Never commit real environment files or sensitive production credentials.
- Use synthetic data for screenshots and demonstrations.

## 10) Documentation Ownership

- Keep this file updated as the architecture and runtime behavior evolve.
- Treat this file as the canonical technical guide for contributors and reviewers.
