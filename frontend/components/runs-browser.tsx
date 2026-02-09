"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { EmptyBlock } from "@/components/empty-block";
import { Lang } from "@/lib/i18n";

export type RunRow = {
  runId: string;
  status: string;
  lastEvent: string;
  timestamp: string;
  reviewDecision?: string | null;
  reasonCodes?: string[];
  errorCode?: string | null;
};

type Props = {
  lang: Lang;
  rows: RunRow[];
};

export function RunsBrowser({ lang, rows }: Props) {
  const isFa = lang === "fa";
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("ALL");
  const [baseRunId, setBaseRunId] = useState("");
  const [otherRunId, setOtherRunId] = useState("");

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesStatus = status === "ALL" || row.status === status;
      if (!matchesStatus) return false;
      if (!normalized) return true;
      return (
        row.runId.toLowerCase().includes(normalized) ||
        row.lastEvent.toLowerCase().includes(normalized) ||
        row.status.toLowerCase().includes(normalized) ||
        (row.reviewDecision || "").toLowerCase().includes(normalized) ||
        (row.reasonCodes || []).join(" ").toLowerCase().includes(normalized)
      );
    });
  }, [rows, query, status]);

  const statusOptions = useMemo(() => {
    const out = Array.from(new Set(rows.map((row) => row.status))).sort();
    return ["ALL", ...out];
  }, [rows]);

  return (
    <>
      <div className="grid-2">
        <section className="card">
          <h3>{isFa ? "فیلتر و جستجو" : "Filter and Search"}</h3>
          <div className="field">
            <label>{isFa ? "جستجو (شناسه اجرا، رویداد، تصمیم)" : "Search (run id, event, decision)"}</label>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={isFa ? "مثلا run id یا AUTO_APPROVED" : "e.g. run id or AUTO_APPROVED"} />
          </div>
          <div className="field">
            <label>{isFa ? "وضعیت" : "Status"}</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {statusOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>
          <div className="inline-actions">
            <button
              className="btn ghost"
              type="button"
              onClick={() => {
                setQuery("");
                setStatus("ALL");
              }}
              disabled={!query && status === "ALL"}
            >
              {isFa ? "پاک کردن فیلترها" : "Clear Filters"}
            </button>
          </div>
        </section>

        <section className="card">
          <h3>{isFa ? "مقایسه دو اجرا" : "Compare Two Runs"}</h3>
          <p className="muted">
            {isFa ? "دو شناسه اجرا وارد کنید تا اختلاف خروجی‌ها را ببینید." : "Provide two run IDs to inspect field-level differences."}
          </p>
          <div className="field">
            <label>{isFa ? "اجرای اول" : "Base run"}</label>
            <input value={baseRunId} onChange={(e) => setBaseRunId(e.target.value)} />
          </div>
          <div className="field">
            <label>{isFa ? "اجرای دوم" : "Other run"}</label>
            <input value={otherRunId} onChange={(e) => setOtherRunId(e.target.value)} />
          </div>
          <div className="inline-actions">
            <Link
              className="btn"
              href={baseRunId && otherRunId ? `/${lang}/runs/${encodeURIComponent(baseRunId)}/compare/${encodeURIComponent(otherRunId)}` : `/${lang}/runs`}
            >
              {isFa ? "باز کردن صفحه مقایسه" : "Open Compare Page"}
            </Link>
          </div>
        </section>
      </div>

      <section className="card">
        <h3>{isFa ? "خروجی مانیتورینگ اجراها" : "Run Monitoring Output"}</h3>
        {filtered.length === 0 ? (
          <EmptyBlock
            title={isFa ? "خروجی فیلتر خالی است" : "No run matches this filter"}
            description={
              isFa
                ? "فیلتر وضعیت یا عبارت جستجو را تغییر بده تا اجراهای بیشتری ببینی."
                : "Adjust your status filter or search query to view matching runs."
            }
            actions={
              <button
                className="btn secondary"
                type="button"
                onClick={() => {
                  setQuery("");
                  setStatus("ALL");
                }}
              >
                {isFa ? "ریست فیلتر" : "Reset Filters"}
              </button>
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>{isFa ? "وضعیت" : "Status"}</th>
                  <th>{isFa ? "آخرین رویداد" : "Last Event"}</th>
                  <th>{isFa ? "تصمیم بازبینی" : "Review Decision"}</th>
                  <th>{isFa ? "Reason Codes" : "Reason Codes"}</th>
                  <th>{isFa ? "زمان" : "Timestamp"}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.runId}>
                    <td style={{ overflowWrap: "anywhere" }}>
                      <Link href={`/${lang}/runs/${encodeURIComponent(row.runId)}`}>{row.runId}</Link>
                    </td>
                    <td>
                      <span
                        className={
                          row.status === "SUCCESS"
                            ? "badge ok"
                            : row.status === "FAILED" || row.status === "CANCELLED"
                              ? "badge danger"
                              : row.status === "WARN" || row.status === "NEEDS_REVIEW"
                                ? "badge warn"
                                : "badge"
                        }
                      >
                        {row.status}
                      </span>
                    </td>
                    <td>{row.lastEvent}</td>
                    <td>{row.reviewDecision || "-"}</td>
                    <td>{row.reasonCodes?.join(", ") || "-"}</td>
                    <td>{row.timestamp}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
