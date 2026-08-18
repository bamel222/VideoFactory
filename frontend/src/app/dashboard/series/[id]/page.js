"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Skeleton, useToast } from "@/components/ui";

const MODE_LABELS = {
  documentary: { images: "Photo-Cinéma", video: "Vidéo Clip IA" },
  cartoon: { images: "Cartoon 2D Animé", video: "Cartoon Clip IA" },
};

function StatusBadge({ status }) {
  const map = {
    planned: "gray", running: "blue", done: "green", failed: "red",
    pending: "gray", queued: "blue", succeeded: "green", skipped: "gray",
    retry: "yellow", review: "yellow", approved: "green", published: "green", produced: "blue",
  };
  return <span className={`badge ${map[status] || "gray"}`}>{status}</span>;
}

export default function SeriesDetailPage() {
  const params = useParams();
  const id = params.id;
  const [series, setSeries] = useState(null);
  const [checkpoints, setCheckpoints] = useState([]);
  const [pack, setPack] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { toast, toastError } = useToast();

  const load = async () => {
    try {
      const [s, cps, p] = await Promise.all([
        api(`/series/${id}`),
        api(`/jobs/series/${id}/checkpoints`),
        api(`/series/${id}/continuity-pack`),
      ]);
      setSeries(s);
      setCheckpoints(cps);
      setPack(p);
    } catch (e) {
      toastError(e.message);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [id]);

  async function run(dry) {
    setError("");
    setBusy(true);
    try {
      const r = dry
        ? await api(`/series/${id}/dry-run`, { method: "POST" })
        : await api(`/series/${id}/run`, { method: "POST", body: JSON.stringify({ series_id: Number(id), dry_run: false }) });
      toast(dry
        ? `Dry run : ${r.report.ready_to_launch ? "prêt" : "risques"} — ${r.report.tasks} tâches, coût $${r.report.budget.estimated_cost}`
        : `Pipeline : ${r.done_tasks}/${r.total_tasks}, statut ${r.status}`);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!series) {
    return (
      <div>
        <Skeleton className="title" style={{ width: 220, marginBottom: 16 }} />
        <Skeleton className="row-lg" />
        <Skeleton className="card mt" style={{ marginTop: 16 }} />
        <Skeleton className="card mt" style={{ marginTop: 16 }} />
      </div>
    );
  }

  return (
    <div>
      <div className="topbar">
        <div>
          <div className="subtitle" style={{ marginBottom: 4 }}>
            <Link href="/dashboard/series" className="muted">Séries & Pipelines</Link>
          </div>
          <div className="row gap">
            <h1 style={{ margin: 0 }}>{series.title}</h1>
            <StatusBadge status={series.status} />
            <span className="badge blue">{series.kind}</span>
            <span className="badge gray">{MODE_LABELS[series.kind]?.[series.generation_mode] || series.generation_mode}</span>
            <span className="badge blue">{series.duration_minutes || 26} min / ép.</span>
            {series.fact_check_enabled && <span className="badge yellow">Fact-check actif</span>}
            <span className="badge gray">{series.language}</span>
          </div>
        </div>
        <div className="row">
          <button className="secondary" disabled={busy} onClick={() => run(true)}>{busy ? "..." : "Dry Run"}</button>
          <button disabled={busy} onClick={() => run(false)}>{busy ? "..." : "Lancer la production"}</button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {series.episodes.map((ep) => (
        <div className="card mb" key={ep.id}>
          <div className="row mb">
            <h2 style={{ margin: 0 }}>Épisode {ep.number} — {ep.title}</h2>
            <StatusBadge status={ep.status} />
            {ep.is_final && <span className="badge yellow">Final</span>}
          </div>
          {ep.scenes.map((sc) => (
            <div key={sc.id} className="muted" style={{ marginBottom: 6 }}>
              <strong>{sc.title}</strong> ({sc.beat}, {sc.duration_seconds}s) — {sc.segments.length} segment(s)
            </div>
          ))}
        </div>
      ))}

      {pack?.exists && (
        <div className="card mb">
          <h2>Continuity Pack — {pack.name}</h2>
          <div className="grid">
            <div>
              <h3>Personnages ({pack.characters.length})</h3>
              <pre className="json">{JSON.stringify(pack.characters, null, 2)}</pre>
            </div>
            <div>
              <h3>Voix ({pack.voices.length})</h3>
              <pre className="json">{JSON.stringify(pack.voices, null, 2)}</pre>
            </div>
            <div>
              <h3>Style & Palette</h3>
              <pre className="json">{JSON.stringify({ style: pack.style, palette: pack.palette }, null, 2)}</pre>
            </div>
            <div>
              <h3>Règles négatives ({pack.negative_rules.length})</h3>
              <pre className="json">{JSON.stringify(pack.negative_rules, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h2>Checkpoints ({checkpoints.length})</h2>
        {checkpoints.slice().reverse().slice(0, 30).map((c) => (
          <div className="checkpoint" key={c.id}>
            <strong>{c.kind}</strong> v{c.version} · <span className="badge blue">{c.provider}</span>
            <br />
            <small>{c.content_ref}</small> · coût ${c.cost} · hash {c.hash?.slice(0, 12)}
          </div>
        ))}
      </div>
    </div>
  );
}
