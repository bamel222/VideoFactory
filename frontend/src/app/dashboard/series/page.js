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

const MODE_OPTIONS = {
  documentary: [
    { value: "images", label: "Photo-Cinéma (images fixes)", title: "Images fixes animées en douceur (effet Ken Burns), accompagnées de la narration, de la musique et des sous-titres. Style documentaire classique et cinématographique." },
    { value: "video", label: "Vidéo Clip IA (clips vidéo)", title: "Montage composé de clips vidéo issus de banques d'images (Pexels/Pixabay) avec secours IA. Rendu dynamique, proche d'un reportage télévisé." },
  ],
  cartoon: [
    { value: "video", label: "Cartoon Clip IA (clips animés)", title: "Cartoon composé de clips vidéo animés générés par IA. Style 3D / animation fluide." },
    { value: "images", label: "Cartoon 2D Animé (images + animation)", title: "Images illustrées animées en 2D légère (déplacements, parallaxe des décors, lèvres approximativement synchronisées). Style dessin animé traditionnel, plus économique que les clips vidéo." },
  ],
};

const DEFAULT_MODE = { documentary: "images", cartoon: "video" };

export default function SeriesPage() {
  const [series, setSeries] = useState([]);
  const [form, setForm] = useState({ title: "", topic: "", kind: "documentary", generation_mode: "images", duration_minutes: 26, planned_episodes: 1, language: "fr", based_on_facts: false });
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

  function onKindChange(kind) {
    setForm({ ...form, kind, generation_mode: DEFAULT_MODE[kind], based_on_facts: false });
  }

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/series", { method: "POST", body: JSON.stringify(form) });
      setForm({ title: "", topic: "", kind: "documentary", generation_mode: "images", duration_minutes: 26, planned_episodes: 1, language: "fr", based_on_facts: false });
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
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 170px 150px 110px auto", alignItems: "end" }}>
            <div className="field">
              <label>Titre</label>
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </div>
            <div className="field">
              <label>Type</label>
              <select value={form.kind} onChange={(e) => onKindChange(e.target.value)}>
                <option value="documentary">Documentaire</option>
                <option value="cartoon">Cartoon</option>
              </select>
            </div>
            <div className="field">
              <label title="Choisissez le format de génération — passez la souris sur une option pour plus de détails">
                Format de génération
              </label>
              <select
                value={form.generation_mode}
                onChange={(e) => setForm({ ...form, generation_mode: e.target.value })}
                title={MODE_OPTIONS[form.kind].find((o) => o.value === form.generation_mode)?.title}
              >
                {MODE_OPTIONS[form.kind].map((o) => (
                  <option key={o.value} value={o.value} title={o.title}>{o.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label title="Durée cible d'un épisode, en minutes">Durée / ép (min)</label>
              <input type="number" min="24" max="28" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} />
            </div>
            <div className="field">
              <label>Épisodes</label>
              <input type="number" min="1" max="10" value={form.planned_episodes} onChange={(e) => setForm({ ...form, planned_episodes: Number(e.target.value) })} />
            </div>
            <button type="submit">Créer</button>
          </div>
          <div className="grid" style={{ gridTemplateColumns: "1fr 220px 150px", alignItems: "end" }}>
            <div className="field">
              <label>{"Sujet (max 3000 caractères) — décrivez l'idée globale de la série"}</label>
              <textarea rows="4" maxLength="3000" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} required placeholder="Ex : une série documentaire grand public sur l'histoire des océans, du rôle des courants à la biodiversité des abysses..." />
            </div>
            <div className="field">
              <label>Langue</label>
              <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {["fr", "en", "es", "de", "it", "pt"].map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            {form.kind === "cartoon" && (
              <div className="field">
                <label>Fact-checking</label>
                <label className="row" style={{ alignItems: "center", gap: 8 }}>
                  <input type="checkbox" checked={form.based_on_facts} onChange={(e) => setForm({ ...form, based_on_facts: e.target.checked })} />
                  <span title="Cochez si le cartoon s'appuie sur des événements réels : la vérification des faits sera alors incluse dans le pipeline. Pour une fiction, laissez décoché.">
                    Basé sur des faits réels
                  </span>
                </label>
              </div>
            )}
          </div>
        </form>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>#</th><th>Titre</th><th>Type</th><th>Format</th><th>Durée/ép</th><th>Statut</th><th>Épisodes</th>
            <th>Score business</th><th>Coût</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {series.map((s) => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td><Link href={`/dashboard/series/${s.id}`}>{s.title}</Link></td>
              <td>{s.kind}</td>
              <td>{MODE_OPTIONS[s.kind]?.find((o) => o.value === s.generation_mode)?.label || s.generation_mode}</td>
              <td>{s.duration_minutes || 26} min</td>
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
