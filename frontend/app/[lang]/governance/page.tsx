import {
  fetchAuditEvents,
  fetchAuditVerify,
  fetchCapacityEstimateSample,
  fetchChangeRiskSample,
  fetchRuntimeVersions
} from "@/lib/api";
import { EmptyBlock } from "@/components/empty-block";
import { StatusBlock } from "@/components/status-block";
import { Lang, getDict } from "@/lib/i18n";

export default async function GovernancePage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const d = getDict(safeLang);

  const [audit, versions, risk, capacity, events] = await Promise.all([
    fetchAuditVerify(),
    fetchRuntimeVersions(),
    fetchChangeRiskSample(),
    fetchCapacityEstimateSample(),
    fetchAuditEvents(24)
  ]);
  const anyMissing = !audit || !versions || !risk || !capacity || !events;

  return (
    <>
      <section className="hero-block">
        <p className="eyebrow">{d.governance}</p>
        <h2 className="hero-title">{isFa ? "ردیابی تغییرات، نسخه‌ها و ظرفیت با شفافیت کامل" : "Trace change, runtime versions, and capacity with full transparency"}</h2>
        <p className="hero-copy">
          {isFa
            ? "داده‌های این صفحه از endpointهای governance و audit خوانده می‌شود تا آمادگی انتشار و پایایی سیستم قابل ارزیابی باشد."
            : "This view is wired to governance and audit endpoints to evaluate release readiness and operational reliability."}
        </p>
        {anyMissing ? (
          <div style={{ marginTop: 12 }}>
            <StatusBlock
              tone="warning"
              title={isFa ? "بخشی از داده‌های حاکمیت کامل نیست" : "Some governance data is currently incomplete"}
              description={
                isFa
                  ? "یک یا چند endpoint پاسخ نداده‌اند. UI با داده‌های موجود رندر شده و بخش‌های ناقص مشخص شده‌اند."
                  : "One or more endpoints did not respond. The UI is rendered with available data and missing sections are marked."
              }
            />
          </div>
        ) : null}
      </section>

      <div className="grid-3">
        <section className="card">
          <h3>{d.audit}</h3>
          {audit ? (
            <div className="info-list">
              <div className="info-item">
                <strong>{isFa ? "اعتبار زنجیره" : "Chain Integrity"}</strong>
                <span className={audit.valid ? "badge ok" : "badge danger"}>{audit.valid ? "VALID" : "INVALID"}</span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "رویداد بررسی‌شده" : "Events Checked"}</strong>
                <span>{audit.events_checked}</span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "Head Hash" : "Head Hash"}</strong>
                <code>{audit.head_hash ?? "-"}</code>
              </div>
            </div>
          ) : (
            <EmptyBlock
              title={isFa ? "اعتبارسنجی زنجیره در دسترس نیست" : "Chain verification is unavailable"}
              description={isFa ? "endpoint مربوط به audit/verify پاسخ نداد." : "The audit/verify endpoint did not respond."}
            />
          )}
        </section>

        <section className="card">
          <h3>{isFa ? "ریسک تغییر" : "Change Risk"}</h3>
          {risk ? (
            <div className="info-list">
              <div className="info-item">
                <strong>{isFa ? "سطح ریسک" : "Risk Level"}</strong>
                <span className={risk.risk_level === "low" ? "badge ok" : risk.risk_level === "high" ? "badge danger" : "badge warn"}>
                  {risk.risk_level.toUpperCase()}
                </span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "مولفه‌های تغییر" : "Changed Components"}</strong>
                <span>{risk.changed_components.join(", ") || "-"}</span>
              </div>
            </div>
          ) : (
            <EmptyBlock
              title={isFa ? "ارزیابی ریسک در دسترس نیست" : "Change risk evaluation unavailable"}
              description={isFa ? "endpoint مربوط به change-risk پاسخ نداد." : "The change-risk endpoint did not respond."}
            />
          )}
        </section>

        <section className="card">
          <h3>{isFa ? "ظرفیت سیستم" : "System Capacity"}</h3>
          {capacity ? (
            <div className="info-list">
              <div className="info-item">
                <strong>{isFa ? "ظرفیت کل (docs/sec)" : "System Capacity (docs/sec)"}</strong>
                <span>{capacity.capacity_system_docs_per_sec.toFixed(3)}</span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "پیشنهاد بار پیک" : "Recommended Peak Lambda"}</strong>
                <span>{capacity.recommended_peak_lambda.toFixed(3)}</span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "هزینه تقریبی هر سند" : "Estimated Cost Per Doc"}</strong>
                <span>{capacity.cost_per_doc?.cost_per_doc?.toFixed(4) ?? "-"}</span>
              </div>
            </div>
          ) : (
            <EmptyBlock
              title={isFa ? "برآورد ظرفیت در دسترس نیست" : "Capacity estimate unavailable"}
              description={isFa ? "endpoint مربوط به capacity-estimate پاسخ نداد." : "The capacity-estimate endpoint did not respond."}
            />
          )}
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <h3>{d.runtimeVersions}</h3>
          {!versions ? (
            <EmptyBlock
              title={isFa ? "نسخه‌های runtime در دسترس نیست" : "Runtime versions unavailable"}
              description={isFa ? "endpoint runtime-versions پاسخ نداد." : "Runtime versions endpoint did not respond."}
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{isFa ? "مولفه" : "Component"}</th>
                    <th>{isFa ? "نسخه" : "Version"}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(versions.versions).map(([key, value]) => (
                    <tr key={key}>
                      <td>{key}</td>
                      <td>{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card">
          <h3>{isFa ? "Artifact Hashes" : "Artifact Hashes"}</h3>
          {!versions ? (
            <EmptyBlock title={isFa ? "هش آرتیفکت‌ها در دسترس نیست" : "Artifact hashes unavailable"} description={isFa ? "داده نسخه‌ها دریافت نشد." : "Version payload is unavailable."} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{isFa ? "Artifact" : "Artifact"}</th>
                    <th>SHA256</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(versions.artifact_hashes).map(([key, value]) => (
                    <tr key={key}>
                      <td>{key}</td>
                      <td style={{ overflowWrap: "anywhere" }}>{value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <h3>{isFa ? "ظرفیت مرحله‌ای" : "Stage Capacity Breakdown"}</h3>
          {!capacity ? (
            <EmptyBlock
              title={isFa ? "جزئیات ظرفیت مرحله‌ای در دسترس نیست" : "Stage capacity details unavailable"}
              description={isFa ? "برآورد ظرفیت دریافت نشد." : "Capacity estimate payload is unavailable."}
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{isFa ? "مرحله" : "Stage"}</th>
                    <th>{isFa ? "service_time_ms" : "service_time_ms"}</th>
                    <th>{isFa ? "concurrency" : "concurrency"}</th>
                    <th>{isFa ? "capacity_docs_per_sec" : "capacity_docs_per_sec"}</th>
                  </tr>
                </thead>
                <tbody>
                  {capacity.stage_capacities.map((row, idx) => (
                    <tr key={idx}>
                      <td>{String((row.stage as string) || "-")}</td>
                      <td>{String((row.service_time_ms as number) ?? "-")}</td>
                      <td>{String((row.concurrency as number) ?? "-")}</td>
                      <td>{String((row.capacity_docs_per_sec as number) ?? "-")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="card">
          <h3>{isFa ? "رویدادهای اخیر Audit" : "Recent Audit Events"}</h3>
          {!events ? (
            <EmptyBlock
              title={isFa ? "رویدادهای audit در دسترس نیست" : "Audit events unavailable"}
              description={isFa ? "endpoint audit/events پاسخ نداد." : "Audit events endpoint did not respond."}
            />
          ) : events.items.length === 0 ? (
            <EmptyBlock
              title={isFa ? "رویدادی ثبت نشده" : "No event has been recorded"}
              description={isFa ? "بعد از اجرای عملیات روی سند، رویدادها در این بخش ظاهر می‌شوند." : "Events will appear here after running document operations."}
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{isFa ? "زمان" : "Timestamp"}</th>
                    <th>{isFa ? "رویداد" : "Event"}</th>
                    <th>Run</th>
                  </tr>
                </thead>
                <tbody>
                  {events.items.map((event, idx) => (
                    <tr key={`${event.hash ?? "event"}-${idx}`}>
                      <td>{event.timestamp_utc}</td>
                      <td>
                        <span className="badge">{event.event_type}</span>
                      </td>
                      <td style={{ overflowWrap: "anywhere" }}>{event.run_id || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
