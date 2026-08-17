"use client";

import { useEffect, useState } from "react";
import { api, can } from "@/lib/api";

const ROLES = ["research", "script", "transcription", "translation", "tts", "voice", "music", "image", "video", "assembly", "seo", "qa", "licensing", "caption"];

export default function ProvidersPage() {
  const [providers, setProviders] = useState([]);
  const [form, setForm] = useState({ name: "", role: "tts", endpoint: "mock://tts", api_key: "", quota_total: 100000, priority: 100, cost_per_unit: 0, quality_estimate: 50, status: "active" });
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    try { setProviders(await api("/providers")); } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setError(""); setMsg("");
    try {
      await api("/providers", { method: "POST", body: JSON.stringify(form) });
      setForm({ ...form, name: "", api_key: "" });
      await load();
    } catch (err) { setError(err.message); }
  }

  async function toggle(p) {
    setError("");
    try {
      await api(`/providers/${p.id}`, { method: "PATCH", body: JSON.stringify({ status: p.status === "active" ? "disabled" : "active" }) });
      await load();
    } catch (err) { setError(err.message); }
  }

  async function healthcheck(p) {
    setError(""); setMsg("");
    try {
      const r = await api(`/providers/${p.id}/healthcheck`, { method: "POST" });
      setMsg(`Healthcheck ${p.name}: ${r.healthy ? "OK" : "KO"}`);
      await load();
    } catch (err) { setError(err.message); }
  }

  async function testKey(p) {
    setError(""); setMsg("");
    try {
      const r = await api(`/providers/${p.id}/test-key`, { method: "POST" });
      setMsg(`Test clé ${p.name}: ${r.ok ? "acceptée" : "rejetée"}`);
    } catch (err) { setError(err.message); }
  }

  async function del(p) {
    if (!confirm(`Supprimer le provider "${p.name}" ? (action Owner)`)) return;
    setError("");
    try {
      await api(`/providers/${p.id}`, { method: "DELETE" });
      await load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <h1>Provider Registry</h1>
      {error && <div className="error">{error}</div>}
      {msg && <div className="success">{msg}</div>}

      <div className="card mb">
        <h2>Nouveau provider</h2>
        <form onSubmit={create}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 150px 170px 120px 100px 100px 90px 90px auto", alignItems: "end" }}>
            <div className="field"><label>Nom</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
            <div className="field"><label>Rôle</label>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="field"><label>Endpoint</label><input value={form.endpoint} onChange={(e) => setForm({ ...form, endpoint: e.target.value })} /></div>
            <div className="field"><label>API key</label><input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} /></div>
            <div className="field"><label>Quota</label><input type="number" value={form.quota_total} onChange={(e) => setForm({ ...form, quota_total: Number(e.target.value) })} /></div>
            <div className="field"><label>Priorité</label><input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} /></div>
            <div className="field"><label>Coût/unité</label><input type="number" step="0.001" value={form.cost_per_unit} onChange={(e) => setForm({ ...form, cost_per_unit: Number(e.target.value) })} /></div>
            <div className="field"><label>Qualité</label><input type="number" min="0" max="100" value={form.quality_estimate} onChange={(e) => setForm({ ...form, quality_estimate: Number(e.target.value) })} /></div>
            <button type="submit">Créer</button>
          </div>
        </form>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>Nom</th><th>Rôle</th><th>Statut</th><th>Health</th><th>Priorité</th>
            <th>Quota</th><th>Restant</th><th>Coût/unité</th><th>Qualité</th><th>Clé</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.id}>
              <td>{p.name}</td>
              <td><span className="badge blue">{p.role}</span></td>
              <td><span className={`badge ${p.status === "active" ? "green" : "red"}`}>{p.status}</span></td>
              <td><span className={`badge ${p.healthy ? "green" : "red"}`}>{p.healthy ? "ok" : "ko"}</span></td>
              <td>{p.priority}</td>
              <td>{p.quota_total}</td>
              <td>{p.quota_remaining}</td>
              <td>${p.cost_per_unit}</td>
              <td>{p.quality_estimate}/100</td>
              <td className="muted">{p.api_key_masked || "—"}</td>
              <td>
                <div className="row">
                  <button className="small secondary" onClick={() => healthcheck(p)}>Health</button>
                  <button className="small secondary" onClick={() => testKey(p)}>Test clé</button>
                  <button className={`small ${p.status === "active" ? "warn" : "ok"}`} onClick={() => toggle(p)}>{p.status === "active" ? "Désactiver" : "Activer"}</button>
                  {can("providers.delete") && <button className="small danger" onClick={() => del(p)}>Suppr.</button>}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
