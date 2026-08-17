"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

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
        setError(err.message);
      }
    })();
  }, []);

  return (
    <div>
      <h1>{"Vue d'ensemble"}</h1>
      {error && <div className="error">{error}</div>}
      <div className="grid">
        <div className="stat"><div className="value">{stats?.series ?? "—"}</div><div className="label">Séries</div></div>
        <div className="stat"><div className="value">{stats?.providers ?? "—"}</div><div className="label">Providers</div></div>
        <div className="stat"><div className="value">{stats?.health ?? "—"}</div><div className="label">Providers sains</div></div>
        <div className="stat"><div className="value">{stats?.jobs ?? "—"}</div><div className="label">Jobs</div></div>
        <div className="stat"><div className="value">${stats?.cost ?? "—"}</div><div className="label">Coût estimé</div></div>
        <div className="stat"><div className="value">{stats?.minutes ?? "—"}</div><div className="label">Minutes produites</div></div>
      </div>
      <div className="card">
        <h2>Commencer</h2>
        <ol className="muted">
          <li>Créez une série (documentaire ou cartoon) dans <Link href="/dashboard/series">Séries & Pipelines</Link>.</li>
          <li>Lancez un <strong>dry run</strong> pour estimer coûts et quotas avant toute consommation.</li>
          <li>Exécutez le <strong>pipeline</strong> : les agents génèrent recherche, script, voix, images/vidéos, montage, SEO, licences.</li>
          <li>Validez dans <Link href="/dashboard/review">Review & Publication</Link> puis publiez (Owner uniquement).</li>
        </ol>
      </div>
    </div>
  );
}
