"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getToken, getRole, getEmail, logout } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Vue d'ensemble", perms: ["content.read"] },
  { href: "/dashboard/series", label: "Séries & Pipelines", perms: ["content.read"] },
  { href: "/dashboard/review", label: "Review & Publication", perms: ["content.read"] },
  { href: "/dashboard/providers", label: "Providers", perms: ["providers.manage", "providers.manage_noncritical"] },
  { href: "/dashboard/storage", label: "Stockage", perms: ["storage.manage"] },
  { href: "/dashboard/jobs", label: "Jobs & Checkpoints", perms: ["jobs.manage"] },
  { href: "/dashboard/monetization", label: "Monétisation", perms: ["series.manage"] },
  { href: "/dashboard/users", label: "Utilisateurs", perms: ["users.manage"] },
  { href: "/dashboard/audit", label: "Audit", perms: ["audit.read"] },
  { href: "/dashboard/settings", label: "Paramètres & Billing", perms: ["billing.manage", "content.read"] },
];

export default function DashboardLayout({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) return null;

  const role = getRole();
  const email = getEmail();

  function hasPerm(allowed) {
    return allowed.some((p) => NAV.find((n) => n.href === pathname) || true);
  }

  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="brand"><span className="dot"></span> Video Factory AI</div>
        {NAV.map((n) => {
          const show =
            role === "owner" ||
            (role === "admin" &&
              !["users.manage", "billing.manage", "publication.final"].some((p) => n.perms.includes(p))) ||
            (role === "reviewer" && ["content.read", "review.quality"].some((p) => n.perms.includes(p)));
          if (!show) return null;
          const active = pathname === n.href || (n.href !== "/dashboard" && pathname.startsWith(n.href));
          return (
            <Link key={n.href} href={n.href} className={`nav-link ${active ? "active" : ""}`}>
              {n.label}
            </Link>
          );
        })}
        <div className="spacer"></div>
        <div className="user-info">
          <div><strong>{email}</strong></div>
          <div>Rôle : {role}</div>
          <button className="small secondary mt" onClick={() => { logout(); router.replace("/"); }} style={{ marginTop: 8 }}>
            Se déconnecter
          </button>
        </div>
      </nav>
      <main className="content">{children}</main>
    </div>
  );
}
