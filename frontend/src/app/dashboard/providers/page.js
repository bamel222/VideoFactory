"use client";

import { useEffect, useState } from "react";
import { api, can } from "@/lib/api";
import { PageHeader, SkeletonRows, Field, useToast } from "@/components/ui";

const ROLES = ["research", "script", "transcription", "translation", "tts", "voice", "music", "image", "video", "assembly", "seo", "qa", "licensing", "caption"];

const EMPTY_FORM = { name: "", role: "tts", endpoint: "mock://tts", api_key: "", quota_total: 100000, priority: 100, cost_per_unit: 0, quality_estimate: 50, status: "active" };

export default function ProvidersPage() {
  const [providers, setProviders] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const { toast, toastError } = useToast();

  const load = async () => {
    try {
      setProviders(await api("/providers"));
    } catch (e) {
      toastError(e.message);
    }
  };
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/providers", { method: "POST", body: JSON.stringify(form) });
      setForm({ ...form, name: "", api_key: "" });
      toast("Provider créé");
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
    setError("");
    try {
      const r = await api(`/providers/${p.id}/healthcheck`, { method: "POST" });
      toast(`Healthcheck ${p.name} : ${r.healthy ? "OK" : "KO"}`);
      await load();
    } catch (err) { setError(err.message); }
  }

  async function testKey(p) {
    setError("");
    try {
      const r = await api(`/providers/${p.id}/test-key`, { method: "POST" });
      toast(`Test clé ${p.name} : ${r.ok ? "acceptée" : "rejetée"}`);
    } catch (err) { setError(err.message); }
  }

  async function del(p) {
    if (!confirm(`Supprimer le provider "${p.name}" ? (action Owner)`)) return;
    setError("");
    try {
      await api(`/providers/${p.id}`, { method: "DELETE" });
      toast("Provider supprimé");
      await load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <PageHeader title="Provider Registry" subtitle="Fournisseurs d'IA (recherche, voix, images, vidéo, traduction…) avec quotas, coûts et healthchecks." />

      {error && <div className="error">{error}</div>}

      <div className="card mb">
        <h2>Nouveau provider</h2>
        <form onSubmit={create}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 150px 200px 160px 110px 100px 110px 90px auto", alignItems: "end" }}>
            <Field label="Nom"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field>
            <Field label="Rôle">
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </Field>
            <Field label="Endpoint"><input value={form.endpoint} onChange={(e) => setForm({ ...form, endpoint: e.target.value })} /></Field>
            <Field label="API key"><input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} /></Field>
            <Field label="Quota"><input type="number" value={form.quota_total} onChange={(e) => setForm({ ...form, quota_total: Number(e.target.value) })} /></Field>
            <Field label="Priorité"><input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} /></Field>
            <Field label="Coût/unité"><input type="number" step="0.001" value={form.cost_per_unit} onChange={(e) => setForm({ ...form, cost_per_unit: Number(e.target.value) })} /></Field>
            <Field label="Qualité"><input type="number" min="0" max="100" value={form.quality_estimate} onChange={(e) => setForm({ ...form, quality_estimate: Number(e.target.value) })} /></Field>
            <button type="submit">Créer</button>
          </div>
        </form>
      </div>

      {!providers ? (
        <SkeletonRows rows={8} cols={11} />
      ) : (
        <div className="table-wrap">
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
      )}
    </div>
  );
}
