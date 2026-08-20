"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatCard, SkeletonCards, useToast } from "@/components/ui";

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
        const [series, providers, jobs, billing, queue] = await Promise.all([
          api("/series"),
          api("/providers"),
          api("/jobs"),
          api("/settings/billing"),
          api("/review/queue"),
        ]);
        setStats({
          series: series.length,
          providers: providers.length,
          jobs: jobs.length,
          cost: billing.total_estimated_cost ?? 0,
          minutes: billing.total_minutes ?? 0,
          health: providers.filter((p) => p.healthy).length,
          ready: (queue || []).length,
        });
      } catch (err) {
        toastError(err.message);
      }
    })();
  }, [toastError]);

  return (
    <div>
      <div className="topbar">
        <div>
          <div className="kicker">Production</div>
          <h1>Vue d'ensemble</h1>
          <div className="subtitle">Supervisez votre usine vidéo — production en cours, fournisseurs et budget.</div>
        </div>
      </div>

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
          <StatCard icon={Icons.jobs} value={stats.ready ?? "—"} label="Épisodes prêts" iconBg="linear-gradient(135deg,#22c55e,#4ade80)" />
        </div>
      )}

      <div className="card">
        <h2>Commencer</h2>
        <p className="muted" style={{ fontSize: 13, marginTop: 6, maxWidth: 620 }}>
          Survolez chaque étape pour en comprendre le sens, puis lancez votre première production.
        </p>
        <ol className="muted" style={{ paddingLeft: 18, lineHeight: 2 }}>
          <li>
            <span data-tip="Une série est un ensemble d'épisodes (documentaire ou cartoon). Vous y choisissez le format de génération (Photo-Cinéma, Vidéo Clip IA, Cartoon 2D Animé) et la durée de chaque épisode.">
              Créez une série
            </span>{" "}
            dans <Link href="/dashboard/series">Séries &amp; Pipelines</Link>.
          </li>
          <li>
            <span data-tip="Un dry run est une simulation complète du pipeline sans produire de vidéo : il estime le coût, les quotas et détecte les risques (providers manquants, stockage insuffisant) avant toute dépense réelle.">
              Lancez un <strong>dry run</strong>
            </span>{" "}
            pour estimer coûts et quotas.
          </li>
          <li>
            <span data-tip="Le pipeline est la chaîne automatisée d'agents qui transforme une idée en vidéo finale : recherche, script, voix, images/vidéos, montage, SEO et licences. « Exécuter » lance cette chaîne de bout en bout.">
              Exécutez le <strong>pipeline</strong>
            </span>{" "}
            : les agents produisent recherche, script, voix, images, montage et SEO.
          </li>
          <li>
            <span data-tip="Valider est la revue qualité finale : vous contrôlez la vidéo, les shorts, le SEO et les sources avant publication. Aucun contenu ne part sans validation explicite.">
              Validez
            </span>{" "}
            dans <Link href="/dashboard/review">Review &amp; Publication</Link> puis publiez (Owner uniquement).
          </li>
        </ol>
      </div>
    </div>
  );
}
