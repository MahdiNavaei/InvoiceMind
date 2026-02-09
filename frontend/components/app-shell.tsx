import Link from "next/link";
import { ReactNode } from "react";

import { Lang, getDict } from "@/lib/i18n";
import { NavLink } from "@/components/nav-link";

type Props = {
  lang: Lang;
  children: ReactNode;
};

export function AppShell({ lang, children }: Props) {
  const d = getDict(lang);
  const isFa = lang === "fa";
  return (
    <div className="app-shell" dir={isFa ? "rtl" : "ltr"}>
      <aside className="app-sidebar">
        <div className="brand-block">
          <p className="eyebrow">{isFa ? "پلتفرم تحلیل فاکتور" : "Invoice Intelligence Platform"}</p>
          <div className="brand">{d.appName}</div>
          <p className="brand-note">
            {isFa
              ? "مرکز عملیات دوزبانه برای پردازش، بازبینی، قرنطینه و حاکمیت"
              : "Bilingual operations cockpit for processing, quarantine, review, and governance"}
          </p>
        </div>

        <nav className="nav-cluster">
          <NavLink
            href={`/${lang}/dashboard`}
            label={d.dashboard}
            subtitle={isFa ? "شاخص‌ها و فعالیت لحظه‌ای" : "Live metrics and activity"}
          />
          <NavLink
            href={`/${lang}/upload`}
            label={d.upload}
            subtitle={isFa ? "بارگذاری سند و ایجاد اجرا" : "Upload document and create run"}
          />
          <NavLink
            href={`/${lang}/runs`}
            label={d.runs}
            subtitle={isFa ? "مانیتورینگ و کنترل اجراها" : "Run monitoring and control"}
          />
          <NavLink
            href={`/${lang}/quarantine`}
            label={d.quarantine}
            subtitle={isFa ? "اقلام قرنطینه و بازپردازش" : "Quarantine items and reprocess"}
          />
          <NavLink
            href={`/${lang}/governance`}
            label={d.governance}
            subtitle={isFa ? "Audit trail، ریسک تغییر و ظرفیت" : "Audit trail, change risk, and capacity"}
          />
          <NavLink
            href={`/${lang}/settings`}
            label={d.settings}
            subtitle={isFa ? "ترجیحات رابط و نسخه‌ها" : "Interface preferences and versions"}
          />
        </nav>

        <div className="sidebar-footer">
          <p className="eyebrow">{isFa ? "زبان رابط" : "Interface Language"}</p>
          <div className="language-switch">
            <Link href="/en/dashboard" className={lang === "en" ? "lang-chip active" : "lang-chip"}>
              English
            </Link>
            <Link href="/fa/dashboard" className={lang === "fa" ? "lang-chip active" : "lang-chip"}>
              فارسی
            </Link>
          </div>
        </div>
      </aside>

      <section className="app-frame">
        <header className="topbar">
          <div>
            <p className="eyebrow">{isFa ? "مرکز فرمان" : "Command Center"}</p>
            <h2 className="topbar-title">
              {isFa ? "کنترل کامل جریان اسناد InvoiceMind" : "Full control over InvoiceMind document flow"}
            </h2>
          </div>
          <div className="topbar-actions">
            <Link href={`/${lang}/upload`} className="btn secondary">
              {isFa ? "بارگذاری جدید" : "New Upload"}
            </Link>
            <Link href={`/${lang}/governance`} className="btn ghost">
              {isFa ? "نمای حاکمیت" : "Governance View"}
            </Link>
          </div>
        </header>
        <main className="page-body">{children}</main>
      </section>
    </div>
  );
}
