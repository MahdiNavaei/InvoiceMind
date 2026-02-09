"use client";

import Link from "next/link";
import { useMemo, useRef, useState } from "react";

import { Lang } from "@/lib/i18n";

type Props = {
  lang: Lang;
};

type UploadResult = {
  upload?: {
    id?: string;
    ingestion_status?: string;
    quarantine_item_id?: string;
    quarantine_reason_codes?: string[];
    quality_tier?: string;
    quality_score?: number;
    message?: string;
  };
  run?: {
    run_id?: string;
    status?: string;
    message?: string;
  } | null;
};

export function UploadPanel({ lang }: Props) {
  const isFa = lang === "fa";
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [autoRun, setAutoRun] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  const labels = useMemo(
    () => ({
      title: isFa ? "ارسال سند واقعی به API" : "Upload Real Document to API",
      hint: isFa ? "فایل را Drag & Drop کنید یا برای انتخاب کلیک کنید." : "Drag and drop a file, or click to select.",
      autoRun: isFa ? "پس از upload، اجرای پردازش ساخته شود" : "Create processing run after upload",
      submit: isFa ? "ارسال سند" : "Submit Document",
      running: isFa ? "در حال ارسال..." : "Submitting...",
      noFile: isFa ? "ابتدا یک فایل انتخاب کنید." : "Select a file first.",
      apiErr: isFa ? "ارسال ناموفق بود." : "Request failed.",
      supported: isFa ? "فرمت‌های پیشنهادی: PNG, JPG, PDF, XLSX" : "Suggested formats: PNG, JPG, PDF, XLSX",
      openRun: isFa ? "جزئیات اجرا" : "Open Run Detail",
      openQ: isFa ? "مشاهده قرنطینه" : "Open Quarantine",
      clearFile: isFa ? "حذف فایل انتخاب‌شده" : "Clear selected file",
      accepted: isFa ? "سند با موفقیت پذیرفته شد." : "Document was accepted successfully.",
      quarantined: isFa ? "سند به قرنطینه رفت. reason code را بررسی کنید." : "Document was quarantined. Check reason codes.",
      rejected: isFa ? "ورودی رد شد. جزئیات قرارداد کیفیت را بررسی کنید." : "Input was rejected. Review quality contract details."
    }),
    [isFa]
  );

  function onPick(nextFile: File | null) {
    setFile(nextFile);
    setError(null);
    setSuccess(null);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setResult(null);
    if (!file) {
      setError(labels.noFile);
      return;
    }

    setLoading(true);
    try {
      const form = new FormData();
      form.set("file", file);
      form.set("auto_run", autoRun ? "true" : "false");

      const res = await fetch("/api/invoicemind/upload-and-run", {
        method: "POST",
        body: form
      });
      const payload = (await res.json()) as UploadResult;
      if (!res.ok) {
        setError(payload.upload?.message || labels.apiErr);
      } else if (payload.upload?.ingestion_status === "ACCEPTED") {
        setSuccess(labels.accepted);
      } else if (payload.upload?.ingestion_status?.startsWith("QUARANTINED")) {
        setSuccess(labels.quarantined);
      } else if (payload.upload?.ingestion_status === "REJECTED") {
        setSuccess(labels.rejected);
      } else {
        setSuccess(payload.upload?.message || (isFa ? "عملیات با موفقیت انجام شد." : "Operation completed successfully."));
      }
      setResult(payload);
    } catch {
      setError(labels.apiErr);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h3>{labels.title}</h3>
      <form onSubmit={onSubmit}>
        <input
          ref={inputRef}
          type="file"
          hidden
          accept=".png,.jpg,.jpeg,.webp,.pdf,.xlsx"
          onChange={(e) => onPick(e.target.files?.[0] ?? null)}
        />
        <button
          type="button"
          className={`card file-drop ${dragging ? "active" : "idle"}`}
          style={{ width: "100%" }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            onPick(e.dataTransfer.files?.[0] ?? null);
          }}
          onClick={() => inputRef.current?.click()}
        >
          <p style={{ margin: 0, fontWeight: 700 }}>{file ? file.name : labels.hint}</p>
          <p className="muted" style={{ margin: "6px 0 0" }}>
            {labels.supported}
          </p>
        </button>
        {file ? (
          <div className="inline-actions" style={{ marginBottom: 12 }}>
            <button className="btn ghost" type="button" onClick={() => onPick(null)}>
              {labels.clearFile}
            </button>
          </div>
        ) : null}

        <div className="field" style={{ marginTop: 12 }}>
          <label>{labels.autoRun}</label>
          <select value={autoRun ? "yes" : "no"} onChange={(e) => setAutoRun(e.target.value === "yes")}>
            <option value="yes">{isFa ? "بله" : "Yes"}</option>
            <option value="no">{isFa ? "خیر" : "No"}</option>
          </select>
        </div>

        <button className="btn" disabled={loading}>
          {loading ? (
            <span className="loading-inline">
              <span className="loading-dot" />
              {labels.running}
            </span>
          ) : (
            labels.submit
          )}
        </button>
      </form>

      {error ? (
        <p className="muted" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="muted" style={{ color: "var(--accent)" }}>
          {success}
        </p>
      ) : null}

      {result?.upload ? (
        <section className="card" style={{ marginTop: 12 }}>
          <h3 style={{ marginTop: 0 }}>{isFa ? "نتیجه پردازش ورودی" : "Ingestion Outcome"}</h3>
          <div className="info-list">
            <div className="info-item">
              <strong>{isFa ? "وضعیت" : "Status"}</strong>
              <span className={result.upload.ingestion_status === "ACCEPTED" ? "badge ok" : "badge warn"}>
                {result.upload.ingestion_status || "UNKNOWN"}
              </span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "کیفیت" : "Quality"}</strong>
              <span>
                {result.upload.quality_tier || "-"} /{" "}
                {typeof result.upload.quality_score === "number" ? result.upload.quality_score.toFixed(2) : "-"}
              </span>
            </div>
            <div className="info-item">
              <strong>{isFa ? "Reason Codes" : "Reason Codes"}</strong>
              <span>{result.upload.quarantine_reason_codes?.join(", ") || "-"}</span>
            </div>
          </div>

          <div className="inline-actions" style={{ marginTop: 12 }}>
            {result.upload.quarantine_item_id ? (
              <Link href={`/${lang}/quarantine`} className="btn secondary">
                {labels.openQ}
              </Link>
            ) : null}
            {result.run?.run_id ? (
              <Link href={`/${lang}/runs/${encodeURIComponent(result.run.run_id)}`} className="btn">
                {labels.openRun}
              </Link>
            ) : null}
          </div>
        </section>
      ) : null}
    </div>
  );
}
