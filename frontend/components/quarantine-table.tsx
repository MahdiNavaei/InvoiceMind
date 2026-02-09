"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { QuarantineItem } from "@/lib/api";
import { Lang } from "@/lib/i18n";

type Props = {
  lang: Lang;
  items: QuarantineItem[];
};

type ReprocessResponse = {
  message?: string;
  detail?: string;
  status?: string;
};

export function QuarantineTable({ lang, items }: Props) {
  const isFa = lang === "fa";
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [loadingItemId, setLoadingItemId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const labels = useMemo(
    () => ({
      status: isFa ? "وضعیت" : "Status",
      stage: isFa ? "مرحله" : "Stage",
      created: isFa ? "تاریخ ایجاد" : "Created At",
      reasonCodes: isFa ? "کدهای دلیل" : "Reason Codes",
      reprocessCount: isFa ? "تعداد Reprocess" : "Reprocess Count",
      action: isFa ? "اکشن" : "Action",
      reprocess: isFa ? "بازپردازش" : "Reprocess",
      pending: isFa ? "در حال اجرا..." : "Running...",
      failed: isFa ? "بازپردازش ناموفق بود." : "Reprocess request failed."
    }),
    [isFa]
  );

  const statuses = useMemo(() => ["ALL", ...Array.from(new Set(items.map((item) => item.status))).sort()], [items]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return items.filter((item) => {
      const okStatus = status === "ALL" || item.status === status;
      if (!okStatus) return false;
      if (!normalized) return true;
      return (
        item.id.toLowerCase().includes(normalized) ||
        item.stage.toLowerCase().includes(normalized) ||
        item.reason_codes.join(" ").toLowerCase().includes(normalized) ||
        item.document_id.toLowerCase().includes(normalized)
      );
    });
  }, [items, query, status]);

  async function reprocess(itemId: string) {
    setLoadingItemId(itemId);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`/api/invoicemind/quarantine/${encodeURIComponent(itemId)}/reprocess`, {
        method: "POST"
      });
      const payload = (await res.json()) as ReprocessResponse;
      if (!res.ok) {
        setError(payload.detail || payload.message || labels.failed);
      } else {
        setMessage(payload.message || payload.status || "OK");
        router.refresh();
      }
    } catch {
      setError(labels.failed);
    } finally {
      setLoadingItemId(null);
    }
  }

  return (
    <>
      <div className="grid-2">
        <section className="card">
          <h3>{isFa ? "فیلتر قرنطینه" : "Quarantine Filters"}</h3>
          <div className="field">
            <label>{isFa ? "جستجو" : "Search"}</label>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={isFa ? "ID، stage، reason code" : "ID, stage, reason code"} />
          </div>
          <div className="field">
            <label>{labels.status}</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {statuses.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className="card">
          <h3>{isFa ? "وضعیت عملیاتی" : "Operational Snapshot"}</h3>
          <div className="info-list">
            <div className="info-item">
              <strong>{isFa ? "کل آیتم‌ها" : "Total Items"}</strong>
              <span>{items.length}</span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "در حال انتظار" : "Open Items"}</strong>
              <span>{items.filter((item) => !item.status.includes("RESOLVED")).length}</span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "حل‌شده" : "Resolved"}</strong>
              <span>{items.filter((item) => item.status.includes("RESOLVED")).length}</span>
            </div>
          </div>
        </section>
      </div>

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>{labels.status}</th>
              <th>{labels.stage}</th>
              <th>{labels.reasonCodes}</th>
              <th>{labels.reprocessCount}</th>
              <th>{labels.created}</th>
              <th>{labels.action}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="empty-block">
                    <p className="empty-title">{isFa ? "نتیجه‌ای با این فیلتر پیدا نشد" : "No item matched current filters"}</p>
                    <p className="empty-description">
                      {isFa
                        ? "جستجو یا وضعیت را تغییر دهید تا آیتم‌ها نمایش داده شوند."
                        : "Adjust search query or status filter to display matching items."}
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((item) => (
                <tr key={item.id}>
                  <td style={{ maxWidth: 220, overflowWrap: "anywhere" }}>
                    <code>{item.id}</code>
                  </td>
                  <td>
                    <span className={item.status.includes("RESOLVED") ? "badge ok" : "badge warn"}>{item.status}</span>
                  </td>
                  <td>{item.stage}</td>
                  <td style={{ maxWidth: 320, overflowWrap: "anywhere" }}>{item.reason_codes.join(", ") || "-"}</td>
                  <td>{item.reprocess_count}</td>
                  <td>{item.created_at}</td>
                <td>
                  <button className="btn secondary" type="button" onClick={() => reprocess(item.id)} disabled={loadingItemId !== null}>
                    {loadingItemId === item.id ? (
                      <span className="loading-inline">
                        <span className="loading-dot" />
                        {labels.pending}
                      </span>
                    ) : (
                      labels.reprocess
                    )}
                  </button>
                </td>
              </tr>
            ))
          )}
          </tbody>
        </table>
      </div>

      {message ? <p className="muted" style={{ color: "var(--accent)" }}>{message}</p> : null}
      {error ? <p className="muted" style={{ color: "var(--danger)" }}>{error}</p> : null}
    </>
  );
}
