"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Props = {
  href: string;
  label: string;
  subtitle: string;
};

export function NavLink({ href, label, subtitle }: Props) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link href={href} className={`nav-link ${active ? "active" : ""}`}>
      <span className="nav-link-label">{label}</span>
      <span className="nav-link-subtitle">{subtitle}</span>
    </Link>
  );
}
