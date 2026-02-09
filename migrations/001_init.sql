-- Initial schema for InvoiceMind local MVP
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  storage_path TEXT NOT NULL,
  language TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  replay_of_run_id TEXT NULL,
  idempotency_key TEXT UNIQUE NULL,
  status TEXT NOT NULL,
  requested_by TEXT NOT NULL,
  model_name TEXT NULL,
  route_name TEXT NULL,
  error_code TEXT NULL,
  result_json TEXT NULL,
  validation_issues_json TEXT NULL,
  cancel_requested INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  finished_at TEXT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS run_stages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  stage_name TEXT NOT NULL,
  status TEXT NOT NULL,
  attempt INTEGER NOT NULL,
  error_code TEXT NULL,
  details_json TEXT NULL,
  started_at TEXT NULL,
  finished_at TEXT NULL,
  FOREIGN KEY(run_id) REFERENCES runs(id)
);
