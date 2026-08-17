"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function JobsPage() {
  const [runs, setRuns] = useState([]);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");

  const load = async () => {
    try { setRuns(await api("/jobs")); } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function open(runId) {
    setError("");
    try { setDetail(await api(`/jobs/runs/${runId}`)); } catch (e) { setError(e.message); }
  }

  return (
    <div>
      <h1>Jobs & Checkpoints</h1>
      {error && <div className="error">{error}</div>}

      <table className="table mb">
        <thead>
          <tr>
            <th>#</th><th>Série</th><th>Type</th><th>Statut</th><th>Dry run</th>
            <th>Tâches</th><th>Faites</th><th>Coût</th><th>Erreur</th><th></th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{r.series_id}</td>
              <td>{r.kind}</td>
              <td>
                <span className={`badge ${r.status === "done" ? "green" : r.status === "failed" ? "red" : "blue"}`}>{r.status}</span>
              </td>
              <td>{r.dry_run ? "oui" : "non"}</td>
              <td>{r.total_tasks}</td>
              <td>{r.done_tasks}</td>
              <td>${r.total_cost}</td>
              <td className="muted">{r.error || "—"}</td>
              <td><button className="small secondary" onClick={() => open(r.id)}>Détail</button></td>
            </tr>
          ))}
        </tbody>
      </table>

      {detail && (
        <div className="card">
          <div className="row mb">
            <h2 style={{ margin: 0 }}>Run #{detail.id} — {detail.status}</h2>
            <button className="small secondary" onClick={() => setDetail(null)}>Fermer</button>
          </div>
          <table className="table">
            <thead>
              <tr><th>Seq</th><th>Type</th><th>Queue</th><th>Statut</th><th>Épisode</th><th>Coût</th><th>Checkpoint</th><th>Erreur</th></tr>
            </thead>
            <tbody>
              {detail.tasks.map((t) => (
                <tr key={t.id}>
                  <td>{t.sequence}</td>
                  <td><span className="badge blue">{t.task_type}</span></td>
                  <td>{t.queue}</td>
                  <td>
                    <span className={`badge ${t.status === "succeeded" ? "green" : t.status === "failed" ? "red" : t.status === "running" ? "blue" : "gray"}`}>{t.status}</span>
                  </td>
                  <td>{t.episode_id ?? "—"}</td>
                  <td>${t.cost}</td>
                  <td>{t.checkpoint_id ?? "—"}</td>
                  <td className="muted">{t.error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
