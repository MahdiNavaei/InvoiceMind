import Link from "next/link";

import { EmptyBlock } from "@/components/empty-block";
import { StatusBlock } from "@/components/status-block";
import { fetchAuditEvents, fetchMetricsSnapshot } from "@/lib/api";
import { Lang, getDict } from "@/lib/i18n";

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 100) return 100;
  return value;
}

export default async function DashboardPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const d = getDict(safeLang);

  const [metrics, eventsPayload] = await Promise.all([fetchMetricsSnapshot(), fetchAuditEvents(40)]);
  const events = eventsPayload?.items ?? [];
  const metricsConnected = Boolean(metrics);
  const eventsConnected = Boolean(eventsPayload);

  const queueDepth = metrics?.queue_depth ?? 0;
  const succeeded = metrics?.run_succeeded ?? 0;
  const warnings = metrics?.run_warn ?? 0;
  const reviews = metrics?.run_needs_review ?? 0;
  const failed = metrics?.run_failed ?? 0;
  const retries = metrics?.stage_retried ?? 0;
  const quarantined = metrics?.quarantine_created ?? 0;
  const reprocessed = metrics?.quarantine_reprocessed ?? 0;
  const cancelled = metrics?.run_cancelled ?? 0;
  const timedOut = metrics?.run_timed_out ?? 0;
  const completed = succeeded + warnings + reviews + failed;

  const successRate = completed > 0 ? clampPercent((succeeded / completed) * 100) : 0;
  const reviewRate = completed > 0 ? clampPercent((reviews / completed) * 100) : 0;
  const failureRate = completed > 0 ? clampPercent((failed / completed) * 100) : 0;

  return (
    <>
      <section className="hero-block">
        <div className="hero-grid">
          <div>
            <p className="eyebrow">{isFa ? "تصویر لحظه‌ای سیستم" : "Live System Snapshot"}</p>
            <h2 className="hero-title">
              {isFa ? "کیفیت پردازش، بازبینی و قرنطینه را یک‌جا کنترل کن" : "Control quality, review pressure, and quarantine in one place"}
            </h2>
            <p className="hero-copy">
              {isFa
                ? "داشبورد بر اساس داده‌های واقعی API ساخته شده و شاخص‌های عملیاتی، رویدادها و کیفیت خروجی را به‌صورت لحظه‌ای نمایش می‌دهد."
                : "This dashboard is wired to live API signals and presents operational metrics, event flow, and output quality in real time."}
            </p>
            <div className="hero-actions">
              <Link href={`/${safeLang}/upload`} className="btn">
                {isFa ? "شروع بارگذاری جدید" : "Start New Upload"}
              </Link>
              <Link href={`/${safeLang}/runs`} className="btn secondary">
                {isFa ? "مشاهده اجراها" : "Browse Runs"}
              </Link>
              <Link href={`/${safeLang}/quarantine`} className="btn ghost">
                {isFa ? "مدیریت قرنطینه" : "Manage Quarantine"}
              </Link>
            </div>
          </div>

          <div className="kpi-grid">
            <article className="kpi-tile">
              <p className="kpi-label">{d.queueDepth}</p>
              <div className="kpi-value">{queueDepth}</div>
            </article>
            <article className="kpi-tile">
              <p className="kpi-label">{d.successRate}</p>
              <div className="kpi-value">{successRate.toFixed(1)}%</div>
            </article>
            <article className="kpi-tile">
              <p className="kpi-label">{d.reviewRate}</p>
              <div className="kpi-value">{reviewRate.toFixed(1)}%</div>
            </article>
            <article className="kpi-tile">
              <p className="kpi-label">{isFa ? "تعداد Retry" : "Retries"}</p>
              <div className="kpi-value">{retries}</div>
            </article>
          </div>
        </div>
        {!metricsConnected ? (
          <div style={{ marginTop: 12 }}>
            <StatusBlock
              tone="warning"
              title={isFa ? "اتصال Metrics برقرار نیست" : "Metrics connection is unavailable"}
              description={
                isFa
                  ? "شاخص‌ها با مقدار پیش‌فرض نمایش داده شده‌اند. backend را با run.bat یا uvicorn اجرا کنید."
                  : "Metrics are currently shown with fallback values. Start backend using run.bat or uvicorn."
              }
            />
          </div>
        ) : null}
        {!eventsConnected ? (
          <div style={{ marginTop: 10 }}>
            <StatusBlock
              tone="warning"
              title={isFa ? "رویدادهای audit موقتاً در دسترس نیست" : "Audit events are temporarily unavailable"}
              description={
                isFa
                  ? "برای مشاهده timeline اجراها، سرویس API و دسترسی توکن باید فعال باشد."
                  : "Run timeline requires API availability and a valid access token."
              }
            />
          </div>
        ) : null}
      </section>

      <div className="grid-2">
        <section className="card">
          <h3>{isFa ? "سلامت پایپ‌لاین" : "Pipeline Health"}</h3>
          <div className="progress-row">
            <div className="progress-head">
              <span>{isFa ? "موفق" : "Success"}</span>
              <strong>{successRate.toFixed(1)}%</strong>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${successRate}%` }} />
            </div>
          </div>
          <div className="progress-row">
            <div className="progress-head">
              <span>{isFa ? "نیازمند بازبینی" : "Needs Review"}</span>
              <strong>{reviewRate.toFixed(1)}%</strong>
            </div>
            <div className="progress-track">
              <div className="progress-fill warn" style={{ width: `${reviewRate}%` }} />
            </div>
          </div>
          <div className="progress-row">
            <div className="progress-head">
              <span>{isFa ? "خطا/شکست" : "Failure"}</span>
              <strong>{failureRate.toFixed(1)}%</strong>
            </div>
            <div className="progress-track">
              <div className="progress-fill danger" style={{ width: `${failureRate}%` }} />
            </div>
          </div>
          <div className="info-list" style={{ marginTop: 10 }}>
            <div className="info-item">
              <strong>{isFa ? "قرنطینه‌های جدید" : "New quarantines"}</strong>
              <span>{quarantined}</span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "قرنطینه بازپردازش‌شده" : "Reprocessed quarantines"}</strong>
              <span>{reprocessed}</span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "Timeout / Cancelled" : "Timeout / Cancelled"}</strong>
              <span>
                {timedOut} / {cancelled}
              </span>
            </div>
          </div>
        </section>

        <section className="card">
          <h3>{isFa ? "آخرین رویدادهای عملیاتی" : "Recent Operational Events"}</h3>
          {events.length === 0 ? (
            <EmptyBlock
              title={isFa ? "رویدادی برای نمایش ثبت نشده است" : "No event has been recorded yet"}
              description={
                isFa
                  ? "یک سند آپلود کنید و یک run بسازید تا رویدادهای عملیاتی در این بخش نمایش داده شود."
                  : "Upload a document and create a run to populate operational events in this section."
              }
              actions={
                <Link href={`/${safeLang}/upload`} className="btn secondary">
                  {isFa ? "رفتن به Upload" : "Go to Upload"}
                </Link>
              }
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{isFa ? "زمان" : "Timestamp"}</th>
                    <th>{isFa ? "نوع رویداد" : "Event Type"}</th>
                    <th>Run</th>
                  </tr>
                </thead>
                <tbody>
                  {events.slice(0, 12).map((event, idx) => (
                    <tr key={`${event.hash ?? "evt"}-${idx}`}>
                      <td>{event.timestamp_utc}</td>
                      <td>
                        <span className="badge">{event.event_type}</span>
                      </td>
                      <td>
                        {event.run_id ? (
                          <Link href={`/${safeLang}/runs/${encodeURIComponent(event.run_id)}`}>{event.run_id}</Link>
                        ) : (
                          "-"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <div className="grid-3">
        <section className="card">
          <h3>{isFa ? "وضعیت نهایی اجراها" : "Run Outcomes"}</h3>
          <p className="muted">
            {isFa ? "خروجی‌های نهایی برای اجراهای تکمیل‌شده." : "Final statuses for completed runs."}
          </p>
          <div className="info-list">
            <div className="info-item">
              <strong>SUCCESS</strong>
              <span className="badge ok">{succeeded}</span>
            </div>
            <div className="info-item">
              <strong>WARN</strong>
              <span className="badge warn">{warnings}</span>
            </div>
            <div className="info-item">
              <strong>NEEDS_REVIEW</strong>
              <span className="badge warn">{reviews}</span>
            </div>
            <div className="info-item">
              <strong>FAILED</strong>
              <span className="badge danger">{failed}</span>
            </div>
          </div>
        </section>

        <section className="card">
          <h3>{isFa ? "پوشش قابلیت‌های UI" : "UI Feature Coverage"}</h3>
          <p className="muted">
            {isFa ? "تمام ماژول‌های فازهای جدید از طریق صفحه‌های عملیاتی قابل استفاده هستند." : "All new phase modules are accessible through operational screens."}
          </p>
          <ul>
            <li>{isFa ? "Upload + Create Run" : "Upload + Create Run"}</li>
            <li>{isFa ? "Run Detail + Cancel/Replay + Export" : "Run Detail + Cancel/Replay + Export"}</li>
            <li>{isFa ? "Quarantine List + Reprocess" : "Quarantine List + Reprocess"}</li>
            <li>{isFa ? "Audit Verify + Runtime Versions + Risk + Capacity" : "Audit Verify + Runtime Versions + Risk + Capacity"}</li>
          </ul>
        </section>

        <section className="card">
          <h3>{isFa ? "دسترسی سریع" : "Quick Access"}</h3>
          <div className="inline-actions">
            <Link href={`/${safeLang}/runs`} className="btn secondary">
              {isFa ? "اجراها" : "Runs"}
            </Link>
            <Link href={`/${safeLang}/quarantine`} className="btn secondary">
              {isFa ? "قرنطینه" : "Quarantine"}
            </Link>
            <Link href={`/${safeLang}/governance`} className="btn secondary">
              {isFa ? "حاکمیت" : "Governance"}
            </Link>
            <Link href={`/${safeLang}/settings`} className="btn ghost">
              {isFa ? "تنظیمات" : "Settings"}
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
