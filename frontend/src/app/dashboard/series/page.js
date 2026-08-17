"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, can } from "@/lib/api";

function StatusBadge({ status }) {
  const map = {
    planned: "gray", in_progress: "blue", produced: "blue", review: "yellow",
    approved: "green", published: "green", archived: "gray",
  };
  return <span className={`badge ${map[status] || "gray"}`}>{status}</span>;
}

export default function SeriesPage() {
  const [series, setSeries] = useState([]);
  const [form, setForm] = useState({ title: "", topic: "", kind: "documentary", planned_episodes: 1, language: "fr" });
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");

  const load = async () => {
    try {
      setSeries(await api("/series"));
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/series", { method: "POST", body: JSON.stringify(form) });
      setForm({ title: "", topic: "", kind: "documentary", planned_episodes: 1, language: "fr" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function action(id, type) {
    setError("");
    setMsg("");
    setBusy(`${type}-${id}`);
    try {
      if (type === "dryrun") {
        const r = await api(`/series/${id}/dry-run`, { method: "POST" });
        setMsg(`Dry run: ${r.report.ready_to_launch ? "prêt à lancer" : "attention, risques détectés"} — ${r.report.tasks} tâches, coût estimé $${r.report.budget.estimated_cost}`);
      } else {
        const r = await api(`/series/${id}/run`, { method: "POST", body: JSON.stringify({ series_id: id, dry_run: false }) });
        setMsg(`Pipeline terminé: ${r.done_tasks}/${r.total_tasks} tâches, statut ${r.status}`);
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div>
      <h1>Séries & Pipelines</h1>
      {error && <div className="error">{error}</div>}
      {msg && <div className="success">{msg}</div>}

      <div className="card mb">
        <h2>Nouvelle série</h2>
        <form onSubmit={create}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 140px 140px 120px auto", alignItems: "end" }}>
            <div className="field">
              <label>Titre</label>
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </div>
            <div className="field">
              <label>Type</label>
              <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                <option value="documentary">Documentaire</option>
                <option value="cartoon">Cartoon</option>
              </select>
            </div>
            <div className="field">
              <label>Épisodes</label>
              <input type="number" min="1" max="10" value={form.planned_episodes} onChange={(e) => setForm({ ...form, planned_episodes: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>Langue</label>
              <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {["fr", "en", "es", "de", "it", "pt"].map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <button type="submit">Créer</button>
          </div>
          <div className="field">
            <label>{"Sujet (max 3000 caractères) — décrivez l'idée globale de la série"}</label>
            <textarea rows="4" maxLength="3000" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} required placeholder="Ex : une série documentaire grand public sur l'histoire des océans, du rôle des courants à la biodiversité des abysses..." />
          </div>
        </form>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>#</th><th>Titre</th><th>Type</th><th>Statut</th><th>Épisodes</th>
            <th>Score business</th><th>Coût</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {series.map((s) => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td><Link href={`/dashboard/series/${s.id}`}>{s.title}</Link></td>
              <td>{s.kind}</td>
              <td><StatusBadge status={s.status} /></td>
              <td>{s.planned_episodes}</td>
              <td>{s.business_score}</td>
              <td>${s.production_cost}</td>
              <td>
                <div className="row">
                  <button className="small secondary" disabled={busy === `dryrun-${s.id}`} onClick={() => action(s.id, "dryrun")}>Dry run</button>
                  {can("pipeline.run") && (
                    <button className="small" disabled={busy === `run-${s.id}`} onClick={() => action(s.id, "run")}>Lancer</button>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
