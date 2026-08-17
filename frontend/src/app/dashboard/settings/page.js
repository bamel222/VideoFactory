"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [billing, setBilling] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try { setBilling(await api("/settings/billing")); } catch (e) { setError(e.message); }
    })();
  }, []);

  return (
    <div>
      <h1>Paramètres & Billing</h1>
      {error && <div className="error">{error}</div>}
      {billing ? (
        <div className="grid">
          <div className="stat"><div className="value">{billing.plan}</div><div className="label">Plan</div></div>
          <div className="stat"><div className="value">{billing.series_forecasted}</div><div className="label">Séries forecastées</div></div>
          <div className="stat"><div className="value">${billing.total_estimated_cost}</div><div className="label">Coût total estimé ({billing.currency})</div></div>
          <div className="stat"><div className="value">{billing.total_minutes}</div><div className="label">Minutes produites</div></div>
        </div>
      ) : (
        <div className="muted">Chargement du billing (Owner uniquement)…</div>
      )}
    </div>
  );
}
