"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, SkeletonRows, Field, useToast } from "@/components/ui";

const KINDS = ["local", "pcloud", "supabase", "s3", "r2", "b2", "minio", "nas"];
const EMPTY_FORM = { name: "", kind: "local", config: '{"root":"./data/storage"}', priority: 100, status: "active", region: "" };

export default function StoragePage() {
  const [backends, setBackends] = useState(null);
  const [assets, setAssets] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const { toast, toastError } = useToast();

  const load = async () => {
    try {
      const [b, a] = await Promise.all([api("/storage"), api("/storage/assets")]);
      setBackends(b);
      setAssets(a);
    } catch (e) {
      toastError(e.message);
    }
  };
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      let config = {};
      try { config = JSON.parse(form.config); } catch { setError("config JSON invalide"); return; }
      await api("/storage", { method: "POST", body: JSON.stringify({ ...form, config, quota_bytes: 0, cost_per_gb: 0, replication: "" }) });
      setForm(EMPTY_FORM);
      toast("Backend de stockage créé");
      await load();
    } catch (err) { setError(err.message); }
  }

  async function healthcheck(b) {
    setError("");
    try {
      const r = await api(`/storage/${b.id}/healthcheck`, { method: "POST" });
      toast(`Healthcheck ${b.name} : ${r.healthy ? "OK" : "KO"}`);
      await load();
    } catch (err) { setError(err.message); }
  }

  async function toggle(b) {
    setError("");
    try {
      await api(`/storage/${b.id}`, { method: "PATCH", body: JSON.stringify({ status: b.status === "active" ? "disabled" : "active" }) });
      await load();
    } catch (err) { setError(err.message); }
  }

  async function upload(files) {
    setError("");
    const file = files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await api("/storage/upload", { method: "POST", body: fd });
      toast(`Asset stocké : ${r.path}`);
      await load();
    } catch (err) { setError(err.message); }
  }

  async function download(a) {
    setError("");
    try {
      const r = await api(`/storage/assets/${a.id}/download`);
      const bytes = Uint8Array.from(atob(r.data_b64), (c) => c.charCodeAt(0));
      const blob = new Blob([bytes]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = a.path.split("/").pop();
      link.click();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <PageHeader title="Storage Registry" subtitle="Backends de stockage répliqués (local, S3, Supabase…) et assets produits." />

      {error && <div className="error">{error}</div>}

      <div className="card mb">
        <h2>Nouveau backend de stockage</h2>
        <form onSubmit={create}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 140px 1fr 100px 120px 110px auto", alignItems: "end" }}>
            <Field label="Nom"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field>
            <Field label="Type">
              <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                {KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
            </Field>
            <Field label="Config JSON"><input value={form.config} onChange={(e) => setForm({ ...form, config: e.target.value })} /></Field>
            <Field label="Priorité"><input type="number" value={form.priority} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} /></Field>
            <Field label="Région"><input value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} /></Field>
            <Field label="Statut">
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="active">active</option><option value="disabled">disabled</option>
              </select>
            </Field>
            <button type="submit">Créer</button>
          </div>
        </form>
      </div>

      {!backends ? (
        <SkeletonRows rows={4} cols={11} />
      ) : (
        <div className="table-wrap mb">
          <table className="table">
            <thead>
              <tr>
                <th>Nom</th><th>Type</th><th>Statut</th><th>Health</th><th>Priorité</th>
                <th>Quota (Mo)</th><th>Utilisé (Mo)</th><th>Coût/Go</th><th>Région</th><th>Réplication</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {backends.map((b) => (
                <tr key={b.id}>
                  <td>{b.name}</td>
                  <td><span className="badge blue">{b.kind}</span></td>
                  <td><span className={`badge ${b.status === "active" ? "green" : "red"}`}>{b.status}</span></td>
                  <td><span className={`badge ${b.healthy ? "green" : "red"}`}>{b.healthy ? "ok" : "ko"}</span></td>
                  <td>{b.priority}</td>
                  <td>{(b.quota_bytes / 1048576).toFixed(1)}</td>
                  <td>{(b.used_bytes / 1048576).toFixed(1)}</td>
                  <td>${b.cost_per_gb}</td>
                  <td>{b.region || "—"}</td>
                  <td>{b.replication || "—"}</td>
                  <td>
                    <div className="row">
                      <button className="small secondary" onClick={() => healthcheck(b)}>Health</button>
                      <button className={`small ${b.status === "active" ? "warn" : "ok"}`} onClick={() => toggle(b)}>{b.status === "active" ? "Désactiver" : "Activer"}</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card">
        <h2>{"Upload d'asset (répliqué sur les backends actifs)"}</h2>
        <input type="file" onChange={(e) => upload(e.target.files)} />
        {assets && (
          <div className="table-wrap mt">
            <table className="table">
              <thead>
                <tr><th>#</th><th>Path</th><th>Type</th><th>Taille</th><th>Checksum</th><th>Backend</th><th></th></tr>
              </thead>
              <tbody>
                {assets.map((a) => (
                  <tr key={a.id}>
                    <td className="muted">{a.id}</td>
                    <td className="muted">{a.path}</td>
                    <td>{a.kind}</td>
                    <td>{a.size} o</td>
                    <td className="muted">{a.checksum?.slice(0, 12)}…</td>
                    <td>{a.storage_id}</td>
                    <td><button className="small secondary" onClick={() => download(a)}>Télécharger</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
