"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, StatCard, SkeletonCards, Field, useToast } from "@/components/ui";

const PlanIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8z" />
  </svg>
);
const SeriesIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="2" y="4" width="20" height="14" rx="2" />
    <path d="M9 8v6l5-3-5-3z" fill="currentColor" stroke="none" />
  </svg>
);
const CostIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="9" />
    <path d="M8 8.5c0-1 1.8-1.5 4-1.5s4 .5 4 1.5-1.8 1.5-4 1.5-4 .5-4 1.5 1.8 1.5 4 1.5 4 .5 4 1.5" />
    <path d="M12 6v12" />
  </svg>
);
const MinutesIcon = (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3.5 2" />
  </svg>
);

export default function SettingsPage() {
  const [billing, setBilling] = useState(null);
  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({ discord_webhook_url: "", telegram_bot_token: "", telegram_chat_id: "" });
  const [saving, setSaving] = useState(false);
  const { toast, toastError } = useToast();

  useEffect(() => {
    (async () => {
      try {
        setBilling(await api("/settings/billing"));
        setProfile(await api("/notifications/profile"));
      } catch (e) {
        toastError(e.message);
      }
    })();
  }, [toastError]);

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    try {
      setProfile(await api("/notifications/profile", { method: "PUT", body: JSON.stringify(form) }));
      toast("Notifications mises à jour");
    } catch (err) {
      toastError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageHeader title="Paramètres & Billing" subtitle="Plan, coûts et volume de production (Owner uniquement)." />

      {!billing ? (
        <SkeletonCards count={4} />
      ) : (
        <div className="grid">
          <StatCard icon={PlanIcon} value={billing.plan} label="Plan" iconBg="linear-gradient(135deg,#6366f1,#22d3ee)" />
          <StatCard icon={SeriesIcon} value={billing.series_forecasted} label="Séries forecastées" iconBg="linear-gradient(135deg,#6366f1,#a78bfa)" />
          <StatCard icon={CostIcon} value={`$${billing.total_estimated_cost}`} label={`Coût total estimé (${billing.currency})`} iconBg="linear-gradient(135deg,#f59e0b,#fbbf24)" />
          <StatCard icon={MinutesIcon} value={billing.total_minutes} label="Minutes produites" iconBg="linear-gradient(135deg,#06b6d4,#22d3ee)" />
        </div>
      )}

      <div className="card mt" style={{ marginTop: 20 }}>
        <h2>Notifications (Discord & Telegram)</h2>
        <p className="muted" style={{ fontSize: 13 }}>
          Renseignez une fois vos canaux ; vous les activerez/désactiverez au moment de lancer une génération.
          Les identifiants sont chiffrés et jamais ré-affichés.
        </p>
        {profile && (
          <div className="row" style={{ gap: 10, marginBottom: 12 }}>
            <span className={`badge ${profile.discord_configured ? "green" : "gray"}`}>
              Discord {profile.discord_configured ? "configuré" : "non configuré"}
            </span>
            <span className={`badge ${profile.telegram_configured ? "green" : "gray"}`}>
              Telegram {profile.telegram_configured ? "configuré" : "non configuré"}
            </span>
          </div>
        )}
        <form onSubmit={save}>
          <div className="grid" style={{ gridTemplateColumns: "1fr", gap: 12 }}>
            <Field label="Webhook Discord" hint="URL du webhook de votre canal Discord (Paramètres du canal → Intégrations → Webhooks)">
              <input value={form.discord_webhook_url} onChange={(e) => setForm({ ...form, discord_webhook_url: e.target.value })} placeholder="https://discord.com/api/webhooks/..." />
            </Field>
            <Field label="Bot token Telegram" hint="Créé via @BotFather sur Telegram">
              <input value={form.telegram_bot_token} onChange={(e) => setForm({ ...form, telegram_bot_token: e.target.value })} placeholder="123456:ABC-DEF..." />
            </Field>
            <Field label="Chat ID Telegram" hint="Votre identifiant de conversation (ex. @MonBot → /getid)">
              <input value={form.telegram_chat_id} onChange={(e) => setForm({ ...form, telegram_chat_id: e.target.value })} placeholder="123456789" />
            </Field>
          </div>
          <button type="submit" disabled={saving} style={{ marginTop: 12 }}>
            {saving ? "Enregistrement..." : "Enregistrer les notifications"}
          </button>
        </form>
      </div>
    </div>
  );
}
