import Link from "next/link";

export default function HomePage() {
  return (
    <div className="landing-shell">
      <div className="landing-glow" />
      <section className="landing-card">
        <p className="eyebrow">InvoiceMind</p>
        <h1>Operational Cockpit</h1>
        <p className="muted">
          End-to-end control for ingestion, run orchestration, quarantine operations, and governance observability.
        </p>
        <div className="landing-actions">
          <Link className="btn secondary" href="/en/dashboard">
            Enter in English
          </Link>
          <Link className="btn" href="/fa/dashboard">
            ورود به نسخه فارسی
          </Link>
        </div>
      </section>
    </div>
  );
}
