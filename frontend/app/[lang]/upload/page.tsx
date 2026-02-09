import Link from "next/link";

import { StatusBlock } from "@/components/status-block";
import { UploadPanel } from "@/components/upload-panel";
import { Lang, getDict } from "@/lib/i18n";

export default async function UploadPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const d = getDict(safeLang);
  const apiBase = process.env.INVOICEMIND_API_BASE_URL || "http://localhost:8000";

  return (
    <>
      <section className="hero-block">
        <div className="hero-grid">
          <div>
            <p className="eyebrow">{isFa ? "ورود سند" : "Document Intake"}</p>
            <h2 className="hero-title">{isFa ? "شروع جریان پردازش از ورودی واقعی" : "Start the workflow from real ingestion"}</h2>
            <p className="hero-copy">
              {isFa
                ? "این صفحه مستقیم به endpoint واقعی متصل است: سند را دریافت می‌کند، قرارداد کیفیت را اجرا می‌کند و در صورت نیاز run می‌سازد."
                : "This page is wired to the real ingestion endpoint: it validates quality contracts and optionally creates a run."}
            </p>
          </div>

          <div className="info-list">
            <div className="info-item">
              <strong>API Base</strong>
              <code>{apiBase}</code>
            </div>
            <div className="info-item">
              <strong>{isFa ? "رفتار قرنطینه" : "Quarantine Behavior"}</strong>
              <span>{isFa ? "در صورت نقض قرارداد کیفیت فعال می‌شود" : "Activated on quality contract violations"}</span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "سپس چه می‌شود؟" : "Then what?"}</strong>
              <span>{isFa ? "از صفحه اجراها یا قرنطینه ادامه می‌دهید" : "Continue from runs or quarantine pages"}</span>
            </div>
          </div>
        </div>
        {apiBase.includes("localhost") || apiBase.includes("127.0.0.1") ? (
          <div style={{ marginTop: 12 }}>
            <StatusBlock
              tone="info"
              title={isFa ? "حالت توسعه محلی فعال است" : "Local development mode is active"}
              description={
                isFa
                  ? "در صورت خطا، ابتدا مطمئن شوید backend روی آدرس فوق در حال اجراست."
                  : "If requests fail, first ensure backend is running on the API base shown above."
              }
            />
          </div>
        ) : null}
      </section>

      <div className="grid-2">
        <UploadPanel lang={safeLang} />
        <section className="card">
          <h3>{isFa ? "راهنمای سریع اپراتور" : "Operator Quick Guide"}</h3>
          <div className="info-list">
            <div className="info-item">
              <strong>1</strong>
              <span>{isFa ? "سند را ارسال کنید و وضعیت ACCEPTED/QUARANTINED را ببینید." : "Upload a document and inspect ACCEPTED/QUARANTINED status."}</span>
            </div>
            <div className="info-item">
              <strong>2</strong>
              <span>{isFa ? "اگر run ساخته شد، جزئیات و اکشن‌های cancel/replay را در Run Detail انجام دهید." : "If a run is created, use cancel/replay actions in Run Detail."}</span>
            </div>
            <div className="info-item">
              <strong>3</strong>
              <span>{isFa ? "در صورت قرنطینه، reason code را بررسی و reprocess کنید." : "If quarantined, inspect reason codes and trigger reprocess."}</span>
            </div>
          </div>

          <div className="inline-actions" style={{ marginTop: 14 }}>
            <Link href={`/${safeLang}/runs`} className="btn secondary">
              {d.runs}
            </Link>
            <Link href={`/${safeLang}/quarantine`} className="btn secondary">
              {d.quarantine}
            </Link>
            <Link href={`/${safeLang}/governance`} className="btn ghost">
              {d.governance}
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
