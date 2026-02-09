-- Phase 08-10 schema extensions for InvoiceMind
ALTER TABLE documents ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE documents ADD COLUMN ingestion_status TEXT NOT NULL DEFAULT 'ACCEPTED';
ALTER TABLE documents ADD COLUMN quality_tier TEXT NULL;
ALTER TABLE documents ADD COLUMN quality_score REAL NULL;

ALTER TABLE runs ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE runs ADD COLUMN review_decision TEXT NULL;
ALTER TABLE runs ADD COLUMN review_reason_codes_json TEXT NULL;
ALTER TABLE runs ADD COLUMN decision_log_json TEXT NULL;

CREATE TABLE IF NOT EXISTS quarantine_items (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  status TEXT NOT NULL,
  reason_codes_json TEXT NOT NULL,
  details_json TEXT NULL,
  storage_path TEXT NOT NULL,
  reprocess_count INTEGER NOT NULL DEFAULT 0,
  last_reprocessed_at TEXT NULL,
  resolved_at TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS ix_documents_tenant_id ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS ix_runs_tenant_id ON runs(tenant_id);
CREATE INDEX IF NOT EXISTS ix_quarantine_items_document_id ON quarantine_items(document_id);
CREATE INDEX IF NOT EXISTS ix_quarantine_items_tenant_id ON quarantine_items(tenant_id);
