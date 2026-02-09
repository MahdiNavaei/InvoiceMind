import Link from "next/link";

import { EmptyBlock } from "@/components/empty-block";
import { RunActions } from "@/components/run-actions";
import { RunCompareForm } from "@/components/run-compare-form";
import { StatusBlock } from "@/components/status-block";
import { fetchDocument, fetchRun, fetchRunExport } from "@/lib/api";
import { Lang, getDict } from "@/lib/i18n";

export default async function RunDetailPage({
  params
}: {
  params: Promise<{ lang: string; runId: string }>;
}) {
  const { lang, runId } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const d = getDict(safeLang);
  const run = await fetchRun(runId);
  const [runExport, document] = await Promise.all([fetchRunExport(runId), run ? fetchDocument(run.document_id) : Promise.resolve(null)]);

  const result = run?.result ?? {};
  const issues = run?.validation_issues ?? [];
  const reasonCodes = run?.review_reason_codes ?? [];
  const decision = run?.review_decision ?? "UNKNOWN";
  const decisionVersions = (run?.decision_log?.versions as Record<string, string> | undefined) ?? {};
  const decisionThresholds = (run?.decision_log?.thresholds as Record<string, number> | undefined) ?? {};
  const decisionInputHash = String((run?.decision_log?.inputs_snapshot as Record<string, unknown> | undefined)?.hash_sha256 ?? "-");

  if (!run) {
    return (
      <>
        <section className="card">
          <h2>
            {d.runDetail}: {runId}
          </h2>
          <StatusBlock
            tone="danger"
            title={isFa ? "جزئیات اجرا بارگذاری نشد" : "Run detail could not be loaded"}
            description={
              isFa
                ? "شناسه اجرا نادرست است یا API فعلاً در دسترس نیست."
                : "The run id is invalid, or the API is currently unreachable."
            }
            actions={
              <>
                <Link href={`/${safeLang}/runs`} className="btn secondary">
                  {isFa ? "بازگشت به اجراها" : "Back to Runs"}
                </Link>
                <Link href={`/${safeLang}/upload`} className="btn">
                  {isFa ? "ساخت اجرای جدید" : "Create New Run"}
                </Link>
              </>
            }
          />
        </section>
      </>
    );
  }

  return (
    <>
      <section className="hero-block">
        <p className="eyebrow">{isFa ? "جزئیات اجرا" : "Run Details"}</p>
        <h2 className="hero-title">
          {isFa ? "ردیابی کامل تصمیم‌ها و خروجی‌ها" : "Full traceability of decisions and outputs"}
        </h2>
        <div className="info-list" style={{ marginTop: 12 }}>
          <div className="info-item">
            <strong>Run ID</strong>
            <code>{run.run_id}</code>
          </div>
          <div className="info-item">
            <strong>{isFa ? "وضعیت اجرا" : "Run Status"}</strong>
            <span
              className={
                run.status === "SUCCESS"
                  ? "badge ok"
                  : run.status === "FAILED" || run.status === "CANCELLED"
                    ? "badge danger"
                    : run.status === "WARN" || run.status === "NEEDS_REVIEW"
                      ? "badge warn"
                      : "badge"
              }
            >
              {run.status}
            </span>
          </div>
          <div className="info-item">
            <strong>{d.reviewDecision}</strong>
            <span className={decision === "AUTO_APPROVED" ? "badge ok" : "badge warn"}>{decision}</span>
          </div>
          <div className="info-item">
            <strong>Tenant</strong>
            <code>{run.tenant_id}</code>
          </div>
        </div>
      </section>

      <div className="grid-2">
        <section className="card">
          <h3>{isFa ? "خلاصه سند استخراج‌شده" : "Extracted Document Snapshot"}</h3>
          <div className="info-list">
            <div className="info-item">
              <strong>{isFa ? "فروشنده" : "Vendor"}</strong>
              <span>{String(result.vendor_name ?? (isFa ? "نامشخص" : "Unknown"))}</span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "شماره فاکتور" : "Invoice No"}</strong>
              <span>{String(result.invoice_no ?? "-")}</span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "مبلغ کل" : "Total Amount"}</strong>
              <span>
                {String(result.total ?? "-")} {typeof result.currency === "string" ? result.currency : ""}
              </span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "مسیردهی مدل" : "Model Route"}</strong>
              <span>
                {run.model_name ?? "-"} / {run.route_name ?? "-"}
              </span>
            </div>
          </div>
        </section>

        <section className="card">
          <h3>{isFa ? "قرارداد کیفیت سند" : "Document Quality Contract"}</h3>
          {!document ? (
            <StatusBlock
              tone="warning"
              title={isFa ? "متادیتای سند در دسترس نیست" : "Document metadata is unavailable"}
              description={
                isFa
                  ? "نمای جزئیات کیفیت ممکن است ناقص باشد. اتصال endpoint سند را بررسی کنید."
                  : "Quality details may be incomplete. Please verify document endpoint connectivity."
              }
            />
          ) : (
            <div className="info-list">
              <div className="info-item">
                <strong>{isFa ? "Ingestion Status" : "Ingestion Status"}</strong>
                <span className={document.ingestion_status === "ACCEPTED" ? "badge ok" : "badge warn"}>{document.ingestion_status}</span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "کیفیت" : "Quality"}</strong>
                <span>
                  {document.quality_tier ?? "-"} / {typeof document.quality_score === "number" ? document.quality_score.toFixed(2) : "-"}
                </span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "فایل" : "Filename"}</strong>
                <span>{document.filename}</span>
              </div>
              <div className="info-item">
                <strong>{d.reasonCodes}</strong>
                <span>{document.quarantine_reason_codes?.join(", ") || "-"}</span>
              </div>
            </div>
          )}
        </section>
      </div>

      <div className="grid-3">
        <RunActions lang={safeLang} runId={runId} />
        <RunCompareForm lang={safeLang} runId={runId} />
        <section className="card">
          <h3>{isFa ? "وضعیت خروجی Export" : "Export Output Status"}</h3>
          {runExport ? (
            <>
              <p>
                <span className={runExport.status === "SUCCESS" ? "badge ok" : "badge"}>{runExport.status}</span>
              </p>
              <p className="muted">
                {isFa
                  ? "خروجی export برای این اجرا در دسترس است."
                  : "Export payload is available for this run."}
              </p>
            </>
          ) : (
            <StatusBlock
              tone="warning"
              title={isFa ? "Export هنوز آماده نیست" : "Export is not ready yet"}
              description={
                isFa
                  ? "این endpoint فقط برای اجراهای نهایی (SUCCESS/WARN/NEEDS_REVIEW) پاسخ می‌دهد."
                  : "This endpoint responds only for finalized runs (SUCCESS/WARN/NEEDS_REVIEW)."
              }
            />
          )}
        </section>
      </div>

      <div className="grid-2">
        <section className="card">
          <h3>{isFa ? "Decision Log" : "Decision Log"}</h3>
          {!run.decision_log ? (
            <EmptyBlock
              title={isFa ? "Decision log ثبت نشده" : "No decision log recorded"}
              description={
                isFa
                  ? "برای برخی اجراها ممکن است سیاست بازبینی اعمال نشده باشد یا داده‌ها هنوز نهایی نشده باشند."
                  : "Some runs may not include review-policy logs yet, or data may still be incomplete."
              }
            />
          ) : (
            <>
              <div className="info-list">
                <div className="info-item">
                  <strong>{isFa ? "هش ورودی" : "Input Hash"}</strong>
                  <code>{decisionInputHash}</code>
                </div>
              </div>
              <h4 style={{ marginBottom: 8 }}>{isFa ? "نسخه‌ها" : "Versions"}</h4>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{isFa ? "مولفه" : "Component"}</th>
                      <th>{isFa ? "نسخه" : "Version"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(decisionVersions).map(([key, value]) => (
                      <tr key={key}>
                        <td>{key}</td>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h4 style={{ margin: "14px 0 8px" }}>{isFa ? "Thresholds" : "Thresholds"}</h4>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>{isFa ? "پارامتر" : "Parameter"}</th>
                      <th>{isFa ? "مقدار" : "Value"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(decisionThresholds).map(([key, value]) => (
                      <tr key={key}>
                        <td>{key}</td>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>

        <section className="card">
          <h3>{isFa ? "مراحل اجرا" : "Execution Stages"}</h3>
          {run.stages.length === 0 ? (
            <EmptyBlock
              title={isFa ? "مرحله‌ای ثبت نشده" : "No stage has been recorded"}
              description={
                isFa
                  ? "احتمالاً اجرا هنوز شروع نشده یا قبل از اجرای pipeline متوقف شده است."
                  : "The run may still be queued, or it may have been interrupted before pipeline execution."
              }
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{isFa ? "مرحله" : "Stage"}</th>
                    <th>{isFa ? "وضعیت" : "Status"}</th>
                    <th>{isFa ? "تلاش" : "Attempt"}</th>
                    <th>{isFa ? "کد خطا" : "Error Code"}</th>
                  </tr>
                </thead>
                <tbody>
                  {run.stages.map((stage) => (
                    <tr key={`${stage.stage_name}-${stage.attempt}`}>
                      <td>{stage.stage_name}</td>
                      <td>{stage.status}</td>
                      <td>{stage.attempt}</td>
                      <td>{stage.error_code || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h4 style={{ margin: "14px 0 8px" }}>{isFa ? "Validation Issues" : "Validation Issues"}</h4>
          {issues.length === 0 ? (
            <p className="muted">{isFa ? "Issue ثبت نشده." : "No validation issue recorded."}</p>
          ) : (
            <ul>
              {issues.map((issue, idx) => (
                <li key={idx}>
                  <span className="badge warn">{String((issue as Record<string, unknown>).code ?? "ISSUE")}</span>
                </li>
              ))}
            </ul>
          )}

          <h4 style={{ margin: "14px 0 8px" }}>{d.reasonCodes}</h4>
          {reasonCodes.length === 0 ? (
            <p className="muted">-</p>
          ) : (
            <ul>
              {reasonCodes.map((code) => (
                <li key={code}>
                  <span className="badge warn">{code}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}
