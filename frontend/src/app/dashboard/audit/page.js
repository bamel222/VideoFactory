"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const q = filter ? `?action=${encodeURIComponent(filter)}` : "";
      setLogs(await api(`/audit${q}`));
    } catch (e) { setError(e.message); }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  return (
    <div>
      <div className="row mb">
        <h1 style={{ margin: 0 }}>Audit Trail</h1>
        <input style={{ width: 260 }} placeholder="Filtrer par action (ex: provider.update)" value={filter} onChange={(e) => setFilter(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} />
        <button className="secondary" onClick={load}>Filtrer</button>
      </div>
      <p className="muted">Logs immuables : un hash chainé est aussi écrit dans <code>data/audit_immutable.log</code> pour la détection de falsification.</p>
      {error && <div className="error">{error}</div>}
      <table className="table">
        <thead>
          <tr><th>#</th><th>Date</th><th>Utilisateur</th><th>Action</th><th>Ressource</th><th>Réf</th><th>Détails</th><th>IP</th></tr>
        </thead>
        <tbody>
          {logs.map((l) => (
            <tr key={l.id}>
              <td>{l.id}</td>
              <td className="muted">{new Date(l.created_at).toLocaleString()}</td>
              <td>{l.user_id ?? "—"}</td>
              <td><span className="badge blue">{l.action}</span></td>
              <td>{l.resource}</td>
              <td>{l.resource_id ?? "—"}</td>
              <td className="muted">{l.details}</td>
              <td className="muted">{l.ip || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
