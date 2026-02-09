"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Lang } from "@/lib/i18n";

type Props = {
  lang: Lang;
  runId: string;
};

type RunActionResponse = {
  run_id?: string;
  status?: string;
  message?: string;
  detail?: string;
};

export function RunActions({ lang, runId }: Props) {
  const router = useRouter();
  const isFa = lang === "fa";
  const [loading, setLoading] = useState<"cancel" | "replay" | null>(null);
  const [response, setResponse] = useState<RunActionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const labels = useMemo(
    () => ({
      title: isFa ? "کنترل اجرای فعلی" : "Control Current Run",
      cancel: isFa ? "لغو اجرا" : "Cancel Run",
      replay: isFa ? "اجرای مجدد" : "Replay Run",
      pending: isFa ? "در حال ارسال..." : "Submitting...",
      failed: isFa ? "اجرای اکشن ناموفق بود." : "Action request failed.",
      done: isFa ? "اکشن با موفقیت ثبت شد." : "Action submitted successfully."
    }),
    [isFa]
  );

  async function trigger(action: "cancel" | "replay") {
    setLoading(action);
    setError(null);
    setSuccess(null);
    setResponse(null);
    try {
      const res = await fetch(`/api/invoicemind/runs/${encodeURIComponent(runId)}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action })
      });
      const payload = (await res.json()) as RunActionResponse;
      if (!res.ok) {
        setError(payload.detail || payload.message || labels.failed);
      } else {
        setResponse(payload);
        setSuccess(payload.message || labels.done);
        router.refresh();
      }
    } catch {
      setError(labels.failed);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="card">
      <h3>{labels.title}</h3>
      <p className="muted">
        {isFa
          ? "لغو برای توقف runهای صف/درحال اجرا و replay برای ساخت run جدید روی همان سند."
          : "Use cancel to stop queued/running runs and replay to create a new run for the same document."}
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button className="btn" type="button" onClick={() => trigger("cancel")} disabled={loading !== null}>
          {loading === "cancel" ? (
            <span className="loading-inline">
              <span className="loading-dot" />
              {labels.pending}
            </span>
          ) : (
            labels.cancel
          )}
        </button>
        <button className="btn" type="button" onClick={() => trigger("replay")} disabled={loading !== null}>
          {loading === "replay" ? (
            <span className="loading-inline">
              <span className="loading-dot" />
              {labels.pending}
            </span>
          ) : (
            labels.replay
          )}
        </button>
      </div>
      {error ? <p className="muted" style={{ color: "var(--danger)" }}>{error}</p> : null}
      {success ? <p className="muted" style={{ color: "var(--accent)" }}>{success}</p> : null}
      {response ? (
        <p className="muted" style={{ marginTop: 10 }}>
          {response.message || response.status || "OK"}{" "}
          {response.run_id ? <Link href={`/${lang}/runs/${encodeURIComponent(response.run_id)}`}>{response.run_id}</Link> : null}
        </p>
      ) : null}
    </div>
  );
}
