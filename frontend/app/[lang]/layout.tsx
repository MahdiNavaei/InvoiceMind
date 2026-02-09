import { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { Lang } from "@/lib/i18n";

export default async function LangLayout({
  children,
  params
}: {
  children: ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const safeLang: Lang = lang === "fa" ? "fa" : "en";
  return <AppShell lang={safeLang}>{children}</AppShell>;
}
