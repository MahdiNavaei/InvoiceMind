export type MetricsSnapshot = {
  run_created: number;
  run_succeeded: number;
  run_warn: number;
  run_needs_review: number;
  run_failed: number;
  run_timed_out: number;
  run_cancelled: number;
  stage_retried: number;
  quarantine_created: number;
  quarantine_reprocessed: number;
  queue_depth: number;
};

export type RunStage = {
  stage_name: string;
  status: string;
  attempt: number;
  error_code?: string | null;
};

export type DocumentPayload = {
  id: string;
  tenant_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  language: string;
  ingestion_status: string;
  quality_tier?: string | null;
  quality_score?: number | null;
  quarantine_item_id?: string | null;
  quarantine_reason_codes?: string[] | null;
  created_at: string;
  message?: string | null;
};

export type RunPayload = {
  run_id: string;
  document_id: string;
  tenant_id: string;
  status: string;
  model_name?: string | null;
  route_name?: string | null;
  review_decision?: string | null;
  review_reason_codes?: string[] | null;
  decision_log?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  validation_issues?: Array<Record<string, unknown>> | null;
  stages: RunStage[];
};

export type RunExportPayload = {
  run_id: string;
  status: string;
  review_decision?: string | null;
  result?: Record<string, unknown> | null;
};

export type QuarantineItem = {
  id: string;
  document_id: string;
  tenant_id: string;
  stage: string;
  status: string;
  reason_codes: string[];
  reprocess_count: number;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  details?: Record<string, unknown> | null;
};

export type QuarantineListPayload = {
  items: QuarantineItem[];
  total: number;
};

export type AuditVerifyPayload = {
  valid: boolean;
  events_checked: number;
  head_hash?: string | null;
  first_error_index?: number | null;
  error?: string | null;
};

export type RuntimeVersionsPayload = {
  versions: Record<string, string>;
  artifact_hashes: Record<string, string>;
  runtime: Record<string, string | number>;
};

export type ChangeRiskPayload = {
  risk_level: string;
  changed_components: string[];
};

export type CapacityEstimatePayload = {
  capacity_system_docs_per_sec: number;
  recommended_peak_lambda: number;
  stage_capacities: Array<Record<string, unknown>>;
  cost_per_doc: Record<string, number>;
};

export type AuditEvent = {
  timestamp_utc: string;
  event_type: string;
  run_id?: string | null;
  payload?: Record<string, unknown> | null;
  prev_hash?: string | null;
  hash?: string | null;
};

export type AuditEventsPayload = {
  items: AuditEvent[];
};

function apiBaseUrl(): string {
  return process.env.INVOICEMIND_API_BASE_URL || "http://localhost:8000";
}

let tokenCache: { token: string; expiresAt: number } | null = null;

async function getAccessToken(): Promise<string | null> {
  const staticToken = process.env.INVOICEMIND_API_TOKEN;
  if (staticToken) return staticToken;

  const now = Date.now();
  if (tokenCache && tokenCache.expiresAt > now + 10_000) {
    return tokenCache.token;
  }

  const username = process.env.INVOICEMIND_API_USERNAME || "admin";
  const password = process.env.INVOICEMIND_API_PASSWORD || "admin123";
  try {
    const res = await fetch(`${apiBaseUrl()}/v1/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept-Language": "en-US" },
      body: JSON.stringify({ username, password }),
      cache: "no-store"
    });
    if (!res.ok) return null;
    const payload = (await res.json()) as { access_token?: string };
    if (!payload.access_token) return null;
    tokenCache = {
      token: payload.access_token,
      // token default ttl is 120 minutes; keep a conservative cache.
      expiresAt: now + (100 * 60 * 1000)
    };
    return payload.access_token;
  } catch {
    return null;
  }
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
  opts?: { auth?: boolean }
): Promise<T | null> {
  const requireAuth = opts?.auth ?? false;
  const headers = new Headers(init?.headers || {});
  headers.set("Accept-Language", headers.get("Accept-Language") || "en-US");

  if (requireAuth) {
    const token = await getAccessToken();
    if (!token) return null;
    headers.set("Authorization", `Bearer ${token}`);
  }

  try {
    const res = await fetch(`${apiBaseUrl()}${path}`, {
      ...init,
      headers,
      cache: "no-store"
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchMetricsSnapshot(): Promise<MetricsSnapshot | null> {
  return requestJson<MetricsSnapshot>("/metrics");
}

export async function fetchRun(runId: string): Promise<RunPayload | null> {
  return requestJson<RunPayload>(`/v1/runs/${encodeURIComponent(runId)}`, undefined, { auth: true });
}

export async function fetchDocument(documentId: string): Promise<DocumentPayload | null> {
  return requestJson<DocumentPayload>(`/v1/documents/${encodeURIComponent(documentId)}`, undefined, { auth: true });
}

export async function fetchRunExport(runId: string): Promise<RunExportPayload | null> {
  return requestJson<RunExportPayload>(`/v1/runs/${encodeURIComponent(runId)}/export`, undefined, { auth: true });
}

export async function fetchQuarantineItems(limit = 50): Promise<QuarantineListPayload | null> {
  return requestJson<QuarantineListPayload>(`/v1/quarantine?limit=${limit}`, undefined, { auth: true });
}

export async function fetchAuditVerify(): Promise<AuditVerifyPayload | null> {
  return requestJson<AuditVerifyPayload>("/v1/audit/verify", undefined, { auth: true });
}

export async function fetchRuntimeVersions(): Promise<RuntimeVersionsPayload | null> {
  return requestJson<RuntimeVersionsPayload>("/v1/governance/runtime-versions", undefined, { auth: true });
}

export async function fetchChangeRiskSample(): Promise<ChangeRiskPayload | null> {
  return requestJson<ChangeRiskPayload>(
    "/v1/governance/change-risk",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ changed_components: ["model_version", "routing_threshold"] })
    },
    { auth: true }
  );
}

export async function fetchCapacityEstimateSample(): Promise<CapacityEstimatePayload | null> {
  return requestJson<CapacityEstimatePayload>(
    "/v1/governance/capacity-estimate",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stages: [
          { stage: "ocr", service_time_ms: 500, concurrency: 2 },
          { stage: "extract", service_time_ms: 700, concurrency: 1 },
          { stage: "postprocess", service_time_ms: 90, concurrency: 4 }
        ]
      })
    },
    { auth: true }
  );
}

export async function fetchAuditEvents(limit = 100): Promise<AuditEventsPayload | null> {
  return requestJson<AuditEventsPayload>(`/v1/audit/events?limit=${limit}`, undefined, { auth: true });
}
