import Link from "next/link";

import { EmptyBlock } from "@/components/empty-block";
import { StatusBlock } from "@/components/status-block";
import { fetchAuditVerify, fetchRuntimeVersions } from "@/lib/api";
import { Lang, getDict } from "@/lib/i18n";

export default async function SettingsPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const d = getDict(safeLang);

  const [versions, audit] = await Promise.all([fetchRuntimeVersions(), fetchAuditVerify()]);
  const apiConnected = Boolean(versions) || Boolean(audit);

  return (
    <>
      <section className="hero-block">
        <p className="eyebrow">{d.settingsTitle}</p>
        <h2 className="hero-title">{isFa ? "ترجیحات رابط و وضعیت پیکربندی" : "Interface preferences and configuration status"}</h2>
        <p className="hero-copy">
          {isFa
            ? "این صفحه به‌جای کنترل‌های نمایشی، وضعیت واقعی نسخه‌ها و صحت زنجیره audit را نمایش می‌دهد."
            : "Instead of fake toggles, this page shows real runtime/version state and audit chain integrity."}
        </p>
        {!apiConnected ? (
          <div style={{ marginTop: 12 }}>
            <StatusBlock
              tone="warning"
              title={isFa ? "داده تنظیمات از API دریافت نشد" : "Settings data could not be fetched"}
              description={
                isFa
                  ? "نسخه‌ها و گزارش audit در دسترس نیستند. لطفاً backend را اجرا کنید."
                  : "Runtime versions and audit report are unavailable. Please ensure backend is running."
              }
            />
          </div>
        ) : null}
      </section>

      <div className="grid-2">
        <section className="card">
          <h3>{d.language}</h3>
          <p className="muted">{isFa ? "برای تغییر زبان از دکمه‌های زیر استفاده کنید." : "Use the links below to switch language."}</p>
          <div className="inline-actions">
            <Link href="/en/dashboard" className="btn secondary">
              English
            </Link>
            <Link href="/fa/dashboard" className="btn">
              فارسی
            </Link>
          </div>
          <p className="muted">
            {isFa ? "جهت نمایش صفحه (RTL/LTR) به‌صورت خودکار بر اساس زبان اعمال می‌شود." : "Page direction (RTL/LTR) is applied automatically based on language."}
          </p>
        </section>

        <section className="card">
          <h3>{d.audit}</h3>
          {audit ? (
            <div className="info-list">
              <div className="info-item">
                <strong>{isFa ? "صحت زنجیره" : "Chain Verification"}</strong>
                <span className={audit.valid ? "badge ok" : "badge danger"}>{audit.valid ? "VALID" : "INVALID"}</span>
              </div>
              <div className="info-item">
                <strong>{isFa ? "رویدادهای بررسی‌شده" : "Checked Events"}</strong>
                <span>{audit.events_checked}</span>
              </div>
              <div className="info-item">
                <strong>Head Hash</strong>
                <code>{audit.head_hash ?? "-"}</code>
              </div>
            </div>
          ) : (
            <EmptyBlock
              title={isFa ? "گزارش audit در دسترس نیست" : "Audit report is unavailable"}
              description={
                isFa
                  ? "endpoint مربوط به audit/verify پاسخ نداده است."
                  : "Audit verify endpoint did not respond."
              }
            />
          )}
        </section>
      </div>

      <section className="card">
        <h3>{d.runtimeVersions}</h3>
        {!versions ? (
          <EmptyBlock
            title={isFa ? "نسخه‌های runtime در دسترس نیست" : "Runtime versions unavailable"}
            description={isFa ? "endpoint نسخه‌ها پاسخ نداد." : "Runtime versions endpoint did not respond."}
          />
        ) : (
          <div className="grid-2">
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

            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>{isFa ? "آرتیفکت" : "Artifact"}</th>
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
          </div>
        )}
      </section>
    </>
  );
}
