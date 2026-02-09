import Link from "next/link";

import { EmptyBlock } from "@/components/empty-block";
import { RunsBrowser, RunRow } from "@/components/runs-browser";
import { StatusBlock } from "@/components/status-block";
import { fetchAuditEvents } from "@/lib/api";
import { Lang } from "@/lib/i18n";

function inferStatus(eventType: string, payload: Record<string, unknown> | null | undefined): string {
  const payloadStatus = typeof payload?.status === "string" ? payload.status : null;
  if (payloadStatus) return payloadStatus;
  if (eventType === "run_failed") return "FAILED";
  if (eventType === "run_cancelled") return "CANCELLED";
  if (eventType === "run_created") return "QUEUED";
  if (eventType === "run_cancel_requested") return "CANCEL_REQUESTED";
  return "UNKNOWN";
}

export default async function RunsPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const eventsPayload = await fetchAuditEvents(300);
  const events = eventsPayload?.items ?? [];
  const apiConnected = Boolean(eventsPayload);

  const runsMap = new Map<string, RunRow>();
  for (const event of events) {
    if (!event.run_id) continue;
    const payload = (event.payload ?? {}) as Record<string, unknown>;
    const previous = runsMap.get(event.run_id);
    if (previous) continue;

    const reasonCodes = Array.isArray(payload.reason_codes) ? payload.reason_codes.filter((x): x is string => typeof x === "string") : [];
    runsMap.set(event.run_id, {
      runId: event.run_id,
      status: inferStatus(event.event_type, payload),
      lastEvent: event.event_type,
      timestamp: event.timestamp_utc,
      reviewDecision: typeof payload.decision === "string" ? payload.decision : null,
      reasonCodes,
      errorCode: typeof payload.error_code === "string" ? payload.error_code : null
    });
  }

  const rows = Array.from(runsMap.values());
  const successCount = rows.filter((row) => row.status === "SUCCESS").length;
  const reviewCount = rows.filter((row) => row.status === "NEEDS_REVIEW").length;
  const failedCount = rows.filter((row) => row.status === "FAILED").length;

  return (
    <>
      <section className="hero-block">
        <p className="eyebrow">{isFa ? "مانیتورینگ اجرا" : "Run Monitoring"}</p>
        <h2 className="hero-title">{isFa ? "ردیابی کامل وضعیت هر اجرا و تصمیم‌گیری سریع" : "Track every run status and react fast"}</h2>
        <p className="hero-copy">
          {isFa
            ? "این صفحه از audit events واقعی تغذیه می‌شود و وضعیت آخر هر run، تصمیم بازبینی و کدهای دلیل را قابل جستجو می‌کند."
            : "This screen is built from live audit events and lets you search run status, review decision, and reason codes."}
        </p>
        <div className="kpi-grid" style={{ marginTop: 12 }}>
          <article className="kpi-tile">
            <p className="kpi-label">{isFa ? "کل اجراهای شناخته‌شده" : "Known Runs"}</p>
            <div className="kpi-value">{rows.length}</div>
          </article>
          <article className="kpi-tile">
            <p className="kpi-label">SUCCESS</p>
            <div className="kpi-value">{successCount}</div>
          </article>
          <article className="kpi-tile">
            <p className="kpi-label">NEEDS_REVIEW</p>
            <div className="kpi-value">{reviewCount}</div>
          </article>
          <article className="kpi-tile">
            <p className="kpi-label">FAILED</p>
            <div className="kpi-value">{failedCount}</div>
          </article>
        </div>
        {!apiConnected ? (
          <div style={{ marginTop: 12 }}>
            <StatusBlock
              tone="warning"
              title={isFa ? "اتصال audit events برقرار نیست" : "Audit events are unavailable"}
              description={
                isFa
                  ? "لیست اجراها از زنجیره audit خوانده می‌شود. در صورت قطع اتصال، خروجی ممکن است ناقص باشد."
                  : "Run browser reads from the audit chain. The current list may be incomplete while API is unreachable."
              }
            />
          </div>
        ) : null}
      </section>

      {rows.length === 0 ? (
        <section className="card">
          <EmptyBlock
            title={isFa ? "اجرایی پیدا نشد" : "No run has been found"}
            description={
              isFa
                ? "برای شروع، یک سند در صفحه Upload ارسال کنید تا اولین run ساخته شود."
                : "Start by uploading a document in the Upload page to create your first run."
            }
            actions={
              <>
                <Link href={`/${safeLang}/upload`} className="btn">
                  {isFa ? "شروع Upload" : "Start Upload"}
                </Link>
                <Link href={`/${safeLang}/dashboard`} className="btn secondary">
                  {isFa ? "بازگشت به داشبورد" : "Back to Dashboard"}
                </Link>
              </>
            }
          />
        </section>
      ) : (
        <RunsBrowser lang={safeLang} rows={rows} />
      )}
    </>
  );
}
