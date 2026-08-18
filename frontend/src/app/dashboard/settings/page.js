"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, StatCard, SkeletonCards, useToast } from "@/components/ui";

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
  const [error, setError] = useState("");
  const { toastError } = useToast();

  useEffect(() => {
    (async () => {
      try {
        setBilling(await api("/settings/billing"));
      } catch (e) {
        toastError(e.message);
      }
    })();
  }, [toastError]);

  return (
    <div>
      <PageHeader title="Paramètres & Billing" subtitle="Plan, coûts et volume de production (Owner uniquement)." />
      {error && <div className="error">{error}</div>}

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
    </div>
  );
}
