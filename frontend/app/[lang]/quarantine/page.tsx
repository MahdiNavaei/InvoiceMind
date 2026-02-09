import Link from "next/link";

import { EmptyBlock } from "@/components/empty-block";
import { QuarantineTable } from "@/components/quarantine-table";
import { StatusBlock } from "@/components/status-block";
import { fetchQuarantineItems } from "@/lib/api";
import { Lang, getDict } from "@/lib/i18n";

export default async function QuarantinePage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const d = getDict(safeLang);
  const list = await fetchQuarantineItems(100);
  const rows = list?.items ?? [];
  const apiConnected = Boolean(list);

  return (
    <>
      <section className="hero-block">
        <p className="eyebrow">{d.quarantine}</p>
        <h2 className="hero-title">{isFa ? "کنترل چرخه قرنطینه و بازپردازش" : "Control quarantine lifecycle and reprocessing"}</h2>
        <p className="hero-copy">
          {isFa
            ? "این صفحه reason codeها، وضعیت فعلی و عملیات reprocess را برای هر آیتم قرنطینه فراهم می‌کند."
            : "This page surfaces reason codes, current status, and reprocess operations for each quarantined item."}
        </p>
      </section>

      {!apiConnected ? (
        <section className="card">
          <StatusBlock
            tone="danger"
            title={isFa ? "اتصال قرنطینه برقرار نیست" : "Quarantine API is unavailable"}
            description={
              isFa
                ? "امکان خواندن لیست قرنطینه وجود ندارد. سرویس backend و دسترسی توکن را بررسی کنید."
                : "Unable to read quarantine list. Verify backend availability and token access."
            }
          />
        </section>
      ) : rows.length === 0 ? (
        <section className="card">
          <EmptyBlock
            title={isFa ? "آیتم قرنطینه‌ای وجود ندارد" : "No quarantine item exists"}
            description={
              isFa
                ? "در حال حاضر سندی به قرنطینه نرفته است. می‌توانید از صفحه Upload یک ورودی تستی ارسال کنید."
                : "No document is currently quarantined. You can submit a test document from Upload."
            }
            actions={
              <Link href={`/${safeLang}/upload`} className="btn">
                {isFa ? "رفتن به Upload" : "Go to Upload"}
              </Link>
            }
          />
        </section>
      ) : (
        <QuarantineTable lang={safeLang} items={rows} />
      )}
    </>
  );
}
