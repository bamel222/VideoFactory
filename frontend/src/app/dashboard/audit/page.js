"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, SkeletonRows, useToast } from "@/components/ui";

export default function AuditPage() {
  const [logs, setLogs] = useState(null);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const { toastError } = useToast();

  const load = async () => {
    try {
      const q = filter ? `?action=${encodeURIComponent(filter)}` : "";
      setLogs(await api(`/audit${q}`));
    } catch (e) {
      toastError(e.message);
    }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader
        title="Audit Trail"
        subtitle="Logs immuables : un hash chainé est aussi écrit dans data/audit_immutable.log pour la détection de falsification."
        actions={
          <>
            <input style={{ width: 300 }} placeholder="Filtrer par action (ex: provider.update)" value={filter} onChange={(e) => setFilter(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} />
            <button className="secondary" onClick={load}>Filtrer</button>
          </>
        }
      />

      {error && <div className="error">{error}</div>}

      {!logs ? (
        <SkeletonRows rows={8} cols={8} />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>#</th><th>Date</th><th>Utilisateur</th><th>Action</th><th>Ressource</th><th>Réf</th><th>Détails</th><th>IP</th></tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td className="muted">{l.id}</td>
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
      )}
    </div>
  );
}
