export type Lang = "en" | "fa";

type Dictionary = Record<string, string>;

const en: Dictionary = {
  appName: "InvoiceMind",
  dashboard: "Dashboard",
  upload: "Upload",
  runs: "Runs",
  settings: "Settings",
  quarantine: "Quarantine",
  governance: "Governance",
  compare: "Compare",
  quickStats: "Quick Stats",
  queueDepth: "Queue Depth",
  successRate: "Success Rate",
  reviewRate: "Needs Review",
  p95: "P95 Runtime",
  uploadTitle: "Upload Document",
  uploadHint: "Send raw file bytes to /v1/documents with X-Filename header.",
  runDetail: "Run Detail",
  compareTitle: "Run Compare",
  settingsTitle: "Preferences",
  rtl: "Enable RTL",
  language: "Language",
  reviewDecision: "Review Decision",
  reasonCodes: "Reason Codes",
  audit: "Audit",
  runtimeVersions: "Runtime Versions"
};

const fa: Dictionary = {
  appName: "اینویس‌مایند",
  dashboard: "داشبورد",
  upload: "بارگذاری",
  runs: "اجراها",
  settings: "تنظیمات",
  quarantine: "قرنطینه",
  governance: "حاکمیت",
  compare: "مقایسه",
  quickStats: "آمار سریع",
  queueDepth: "عمق صف",
  successRate: "نرخ موفقیت",
  reviewRate: "نیاز به بازبینی",
  p95: "زمان P95",
  uploadTitle: "بارگذاری سند",
  uploadHint: "فایل را به صورت raw bytes به /v1/documents با هدر X-Filename ارسال کنید.",
  runDetail: "جزئیات اجرا",
  compareTitle: "مقایسه اجرا",
  settingsTitle: "ترجیحات",
  rtl: "نمایش راست‌به‌چپ",
  language: "زبان",
  reviewDecision: "تصمیم بازبینی",
  reasonCodes: "کدهای دلیل",
  audit: "ممیزی",
  runtimeVersions: "نسخه‌های اجرا"
};

export function getDict(lang: Lang): Dictionary {
  return lang === "fa" ? fa : en;
}
