"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function MonetizationPage() {
  const [priorities, setPriorities] = useState([]);
  const [form, setForm] = useState({ topic: "", kind: "documentary", languages: "fr,en", duration_min: 2, risk: 0.1 });
  const [score, setScore] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    try { setPriorities(await api("/monetization/priorities")); } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function compute(e) {
    e.preventDefault();
    setError(""); setScore(null);
    try {
      const params = new URLSearchParams({
        topic: form.topic, kind: form.kind,
        languages: form.languages, duration_min: String(form.duration_min), risk_of_rights: String(form.risk),
      });
      setScore(await api(`/monetization/score?${params}`));
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <h1>Monétisation & Optimisation</h1>
      {error && <div className="error">{error}</div>}

      <div className="card mb">
        <h2>Scoring de sujet</h2>
        <form onSubmit={compute}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 140px 150px 120px 110px auto", alignItems: "end" }}>
            <div className="field"><label>Sujet</label><input value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} required /></div>
            <div className="field"><label>Type</label>
              <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                <option value="documentary">Documentaire</option><option value="cartoon">Cartoon</option>
              </select>
            </div>
            <div className="field"><label>Langues (csv)</label><input value={form.languages} onChange={(e) => setForm({ ...form, languages: e.target.value })} /></div>
            <div className="field"><label>Durée min</label><input type="number" step="0.5" value={form.duration_min} onChange={(e) => setForm({ ...form, duration_min: Number(e.target.value) })} /></div>
            <div className="field"><label>Risque droits (0-1)</label><input type="number" step="0.05" min="0" max="1" value={form.risk} onChange={(e) => setForm({ ...form, risk: Number(e.target.value) })} /></div>
            <button type="submit">Scorer</button>
          </div>
        </form>
        {score && (
          <div className="grid mt">
            <div className="stat">
              <div className="value">{score.score}</div>
              <div className="label">Score business</div>
            </div>
            <div className="stat">
              <div className="value">{score.recommendation}</div>
              <div className="label">Recommandation</div>
            </div>
          </div>
        )}
      </div>

      <h2 className="mb">Priorisation des séries (ratio valeur/coût)</h2>
      <table className="table">
        <thead>
          <tr><th>#</th><th>Titre</th><th>Type</th><th>Statut</th><th>Score</th><th>Coût production</th><th>Ratio</th></tr>
        </thead>
        <tbody>
          {priorities.map((p) => (
            <tr key={p.series_id}>
              <td>{p.series_id}</td>
              <td>{p.title}</td>
              <td>{p.kind}</td>
              <td>{p.status}</td>
              <td>{p.business_score}</td>
              <td>${p.production_cost}</td>
              <td><strong>{p.value_ratio}</strong></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
