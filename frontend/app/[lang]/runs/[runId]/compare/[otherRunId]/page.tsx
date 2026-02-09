import Link from "next/link";

import { StatusBlock } from "@/components/status-block";
import { fetchRun } from "@/lib/api";
import { Lang, getDict } from "@/lib/i18n";

type DiffRow = {
  key: string;
  left: string;
  right: string;
};

export default async function ComparePage({
  params
}: {
  params: Promise<{ lang: string; runId: string; otherRunId: string }>;
}) {
  const { lang, runId, otherRunId } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  const isFa = safeLang === "fa";
  const d = getDict(safeLang);
  const left = await fetchRun(runId);
  const right = await fetchRun(otherRunId);

  const leftResult = left?.result ?? {};
  const rightResult = right?.result ?? {};
  const rows: DiffRow[] = [
    { key: isFa ? "وضعیت" : "Status", left: left?.status ?? "-", right: right?.status ?? "-" },
    { key: isFa ? "تصمیم بازبینی" : "Review Decision", left: left?.review_decision ?? "-", right: right?.review_decision ?? "-" },
    { key: isFa ? "Reason Codes" : "Reason Codes", left: left?.review_reason_codes?.join(", ") ?? "-", right: right?.review_reason_codes?.join(", ") ?? "-" },
    { key: isFa ? "فروشنده" : "Vendor", left: String(leftResult.vendor_name ?? "-"), right: String(rightResult.vendor_name ?? "-") },
    { key: isFa ? "شماره فاکتور" : "Invoice No", left: String(leftResult.invoice_no ?? "-"), right: String(rightResult.invoice_no ?? "-") },
    { key: isFa ? "مبلغ کل" : "Total", left: String(leftResult.total ?? "-"), right: String(rightResult.total ?? "-") },
    { key: isFa ? "مالیات" : "Tax", left: String(leftResult.tax ?? "-"), right: String(rightResult.tax ?? "-") },
    { key: isFa ? "مدل" : "Model", left: left?.model_name ?? "-", right: right?.model_name ?? "-" },
    { key: isFa ? "مسیر" : "Route", left: left?.route_name ?? "-", right: right?.route_name ?? "-" }
  ];

  return (
    <>
      <section className="hero-block">
        <p className="eyebrow">{d.compareTitle}</p>
        <h2 className="hero-title">{isFa ? "مقایسه دقیق دو اجرا در سطح فیلد" : "Field-level comparison between two runs"}</h2>
        <p className="hero-copy">
          <code>{runId}</code> vs <code>{otherRunId}</code>
        </p>
      </section>

      <section className="card">
        {!left || !right ? (
          <StatusBlock
            tone="danger"
            title={isFa ? "مقایسه قابل انجام نیست" : "Comparison cannot be completed"}
            description={
              isFa
                ? "حداقل یکی از اجراها از API دریافت نشد. شناسه‌ها و اتصال backend را بررسی کنید."
                : "At least one run is unavailable from API. Verify run ids and backend connectivity."
            }
            actions={
              <Link href={`/${safeLang}/runs`} className="btn secondary">
                {isFa ? "بازگشت به اجراها" : "Back to Runs"}
              </Link>
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{isFa ? "فیلد" : "Field"}</th>
                  <th>{runId}</th>
                  <th>{otherRunId}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const different = row.left !== row.right;
                  return (
                    <tr key={row.key}>
                      <td>{row.key}</td>
                      <td style={different ? { background: "#ecfdf5" } : undefined}>{row.left}</td>
                      <td style={different ? { background: "#fef3c7" } : undefined}>{row.right}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
