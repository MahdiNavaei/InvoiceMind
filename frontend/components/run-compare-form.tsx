"use client";

import Link from "next/link";
import { useState } from "react";

import { Lang } from "@/lib/i18n";

type Props = {
  lang: Lang;
  runId: string;
};

export function RunCompareForm({ lang, runId }: Props) {
  const isFa = lang === "fa";
  const [otherRunId, setOtherRunId] = useState("");

  return (
    <section className="card">
      <h3>{isFa ? "مقایسه با اجرای دیگر" : "Compare with Another Run"}</h3>
      <div className="field">
        <label>{isFa ? "شناسه اجرای دوم" : "Other run ID"}</label>
        <input value={otherRunId} onChange={(e) => setOtherRunId(e.target.value)} />
      </div>
      <Link
        className="btn secondary"
        href={
          otherRunId
            ? `/${lang}/runs/${encodeURIComponent(runId)}/compare/${encodeURIComponent(otherRunId)}`
            : `/${lang}/runs/${encodeURIComponent(runId)}`
        }
      >
        {isFa ? "باز کردن مقایسه" : "Open Comparison"}
      </Link>
    </section>
  );
}
