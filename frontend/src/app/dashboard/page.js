"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader, StatCard, SkeletonCards, useToast } from "@/components/ui";

const Icons = {
  series: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="4" width="20" height="14" rx="2" />
      <path d="M9 8v6l5-3-5-3z" fill="currentColor" stroke="none" />
    </svg>
  ),
  providers: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="6" y="6" width="12" height="12" rx="2" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
    </svg>
  ),
  health: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2l2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8z" />
    </svg>
  ),
  jobs: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 6v6l4 2" />
    </svg>
  ),
  cost: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M8 8.5c0-1 1.8-1.5 4-1.5s4 .5 4 1.5-1.8 1.5-4 1.5-4 .5-4 1.5 1.8 1.5 4 1.5 4 .5 4 1.5" />
      <path d="M12 6v12" />
    </svg>
  ),
  minutes: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </svg>
  ),
};

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const { toastError } = useToast();

  useEffect(() => {
    (async () => {
      try {
        const [series, providers, jobs, billing] = await Promise.all([
          api("/series"),
          api("/providers"),
          api("/jobs"),
          api("/settings/billing"),
        ]);
        setStats({
          series: series.length,
          providers: providers.length,
          jobs: jobs.length,
          cost: billing.total_estimated_cost ?? 0,
          minutes: billing.total_minutes ?? 0,
          health: providers.filter((p) => p.healthy).length,
        });
      } catch (err) {
        toastError(err.message);
      }
    })();
  }, [toastError]);

  return (
    <div>
      <PageHeader
        title="Vue d'ensemble"
        subtitle="Pilotage de votre usine vidéo : production, fournisseurs et budget."
      />

      {!stats ? (
        <SkeletonCards count={6} />
      ) : (
        <div className="grid">
          <StatCard icon={Icons.series} value={stats.series} label="Séries & pipelines" />
          <StatCard icon={Icons.providers} value={stats.providers} label="Providers configurés" />
          <StatCard icon={Icons.health} value={stats.health} label="Providers sains" iconBg="linear-gradient(135deg,#10b981,#34d399)" />
          <StatCard icon={Icons.jobs} value={stats.jobs} label="Jobs lancés" iconBg="linear-gradient(135deg,#6366f1,#a78bfa)" />
          <StatCard icon={Icons.cost} value={`$${stats.cost ?? "—"}`} label="Coût estimé" iconBg="linear-gradient(135deg,#f59e0b,#fbbf24)" />
          <StatCard icon={Icons.minutes} value={stats.minutes ?? "—"} label="Minutes produites" iconBg="linear-gradient(135deg,#06b6d4,#22d3ee)" />
        </div>
      )}

      <div className="card">
        <h2>Commencer</h2>
        <ol className="muted" style={{ paddingLeft: 18, lineHeight: 2 }}>
          <li>
            Créez une série (documentaire ou cartoon) dans{" "}
            <Link href="/dashboard/series">Séries & Pipelines</Link> — choisissez le format (Photo-Cinéma, Vidéo Clip IA, Cartoon 2D Animé…) et la durée par épisode (24-28 min).
          </li>
          <li>
            Lancez un <strong>dry run</strong> pour estimer coûts et quotas avant toute consommation.
          </li>
          <li>
            Exécutez le <strong>pipeline</strong> : recherche, script, voix, images/vidéos, montage final, SEO et licences sont produits par les agents.
          </li>
          <li>
            Validez dans <Link href="/dashboard/review">Review & Publication</Link> puis publiez (Owner uniquement).
          </li>
        </ol>
      </div>
    </div>
  );
}
