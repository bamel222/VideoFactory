"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getToken, getRole, getEmail, getInitial, logout, api } from "@/lib/api";
import { Modal, ToastProvider, useToast, Field } from "@/components/ui";

const ICONS = {
  dashboard: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="9" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  ),
  series: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="4" width="20" height="14" rx="2" />
      <path d="M9 8v6l5-3-5-3z" fill="currentColor" stroke="none" />
    </svg>
  ),
  review: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 12l2 2 4-4" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  ),
  providers: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="6" y="6" width="12" height="12" rx="2" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
    </svg>
  ),
  storage: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5" />
      <path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3" />
    </svg>
  ),
  jobs: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8z" />
    </svg>
  ),
  monetization: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 8.5c0-1 1.8-1.5 4-1.5s4 .5 4 1.5-1.8 1.5-4 1.5-4 .5-4 1.5 1.8 1.5 4 1.5 4 .5 4 1.5" />
      <path d="M12 6v12" />
    </svg>
  ),
  users: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 20c0-3.5 2.9-6 6.5-6s6.5 2.5 6.5 6" />
      <path d="M16 5.5a3.5 3.5 0 010 6" />
      <path d="M19 14.5c2 .8 3.5 2.6 3.5 5.5" />
    </svg>
  ),
  audit: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 3l7 3v5c0 4.6-3 8.6-7 10-4-1.4-7-5.4-7-10V6l7-3z" />
      <path d="M9.5 12l2 2 3.5-4" />
    </svg>
  ),
  settings: (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M19 12a7 7 0 00-.15-1.4l2-1.5-2-3.4-2.3 1a7 7 0 00-2.4-1.4L14 3h-4l-.15 2.3a7 7 0 00-2.4 1.4l-2.3-1-2 3.4 2 1.5A7 7 0 005 12c0 .48.05.94.15 1.4l-2 1.5 2 3.4 2.3-1a7 7 0 002.4 1.4L10 21h4l.15-2.3a7 7 0 002.4-1.4l2.3 1 2-3.4-2-1.5c.1-.46.15-.92.15-1.4z" />
    </svg>
  ),
};

const NAV = [
  { href: "/dashboard", label: "Vue d'ensemble", icon: ICONS.dashboard, perms: ["content.read"] },
  { href: "/dashboard/series", label: "Séries & Pipelines", icon: ICONS.series, perms: ["content.read"] },
  { href: "/dashboard/review", label: "Review & Publication", icon: ICONS.review, perms: ["content.read"] },
  { href: "/dashboard/providers", label: "Providers", icon: ICONS.providers, perms: ["providers.manage", "providers.manage_noncritical"] },
  { href: "/dashboard/storage", label: "Stockage", icon: ICONS.storage, perms: ["storage.manage"] },
  { href: "/dashboard/jobs", label: "Jobs & Checkpoints", icon: ICONS.jobs, perms: ["jobs.manage"] },
  { href: "/dashboard/monetization", label: "Monétisation", icon: ICONS.monetization, perms: ["series.manage"] },
  { href: "/dashboard/users", label: "Utilisateurs", icon: ICONS.users, perms: ["users.manage"] },
  { href: "/dashboard/audit", label: "Audit", icon: ICONS.audit, perms: ["audit.read"] },
  { href: "/dashboard/settings", label: "Paramètres & Billing", icon: ICONS.settings, perms: ["billing.manage", "content.read"] },
];

function ChangePasswordModal({ onClose }) {
  const { toast, toastError } = useToast();
  const [form, setForm] = useState({ old_password: "", new_password: "", confirm: "" });
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    if (form.new_password !== form.confirm) {
      toastError("Les deux mots de passe ne correspondent pas");
      setBusy(false);
      return;
    }
    try {
      await api("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ old_password: form.old_password, new_password: form.new_password }),
      });
      window.localStorage.removeItem("vf_pw_expired");
      toast("Mot de passe mis à jour");
      onClose();
    } catch (err) {
      toastError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Changer le mot de passe" onClose={onClose}>
      <form onSubmit={submit}>
        <Field label="Mot de passe actuel">
          <input type="password" required value={form.old_password} onChange={(e) => setForm({ ...form, old_password: e.target.value })} autoComplete="current-password" />
        </Field>
        <Field label="Nouveau mot de passe" hint="12 caractères minimum, majuscule, minuscule et chiffre requis">
          <input type="password" required minLength={12} value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} autoComplete="new-password" />
        </Field>
        <Field label="Confirmer le nouveau mot de passe">
          <input type="password" required value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} autoComplete="new-password" />
        </Field>
        <button type="submit" disabled={busy}>
          {busy ? "Enregistrement..." : "Mettre à jour"}
        </button>
      </form>
    </Modal>
  );
}

function Shell({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [pwModal, setPwModal] = useState(false);
  const { toastError } = useToast();

  useEffect(() => {
    if (!getToken()) {
      router.replace("/");
      return;
    }
    setReady(true);
  }, [router]);

  useEffect(() => {
    const flag = window.localStorage.getItem("vf_pw_expired");
    if (flag === "1" && getToken()) setPwModal(true);
  }, []);

  if (!ready) return null;

  const role = getRole();
  const email = getEmail();
  const initial = getInitial();

  function handleLogout() {
    logout();
    router.replace("/");
  }

  async function handleChangePassword() {
    try {
      setPwModal(true);
    } catch (err) {
      toastError(err.message);
    }
  }

  const isReviewer = role === "reviewer";
  const isAdmin = role === "admin";

  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="brand">
          <div className="brand-logo">VF</div>
          <span className="brand-text">Video Factory AI</span>
        </div>
        <div className="nav-section-label">Espace de travail</div>
        {NAV.map((n) => {
          const ownerOnly = ["users.manage", "billing.manage"].some((p) => n.perms.includes(p));
          const show =
            role === "owner" ||
            (isAdmin && !ownerOnly && !n.perms.includes("providers.manage")) ||
            (isReviewer && ["content.read", "review.quality"].some((p) => n.perms.includes(p)));
          if (!show) return null;
          const active = pathname === n.href || (n.href !== "/dashboard" && pathname.startsWith(n.href));
          return (
            <Link key={n.href} href={n.href} className={`nav-link ${active ? "active" : ""}`}>
              {n.icon}
              <span>{n.label}</span>
            </Link>
          );
        })}
        <div className="spacer"></div>
        <div className="user-card">
          <div className="user-row">
            <div className="user-avatar">{initial}</div>
            <div className="user-meta">
              <div className="name">{email}</div>
              <div className="role">Rôle : {role}</div>
            </div>
          </div>
          <div className="row mt" style={{ marginTop: 12 }}>
            <button className="small secondary" onClick={handleChangePassword} style={{ flex: 1 }}>
              Mot de passe
            </button>
            <button className="small ghost" onClick={handleLogout}>
              Déconnexion
            </button>
          </div>
        </div>
      </nav>
      <main className="content">{children}</main>
      {pwModal && <ChangePasswordModal onClose={() => setPwModal(false)} />}
    </div>
  );
}

export default function DashboardLayout({ children }) {
  return (
    <ToastProvider>
      <Shell>{children}</Shell>
    </ToastProvider>
  );
}
