"use client";

import { useEffect, useState } from "react";
import { api, can } from "@/lib/api";

function StatusBadge({ s }) {
  const map = { review: "yellow", approved: "green", published: "green", produced: "blue", planned: "gray" };
  return <span className={`badge ${map[s] || "gray"}`}>{s}</span>;
}

export default function ReviewPage() {
  const [queue, setQueue] = useState([]);
  const [selected, setSelected] = useState(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    try { setQueue(await api("/review/queue")); } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function open(episodeId) {
    setError(""); setMsg("");
    try { setSelected(await api(`/review/episodes/${episodeId}`)); } catch (e) { setError(e.message); }
  }

  async function decide(status) {
    setError("");
    try {
      await api(`/review/episodes/${selected.episode.id}/decide`, {
        method: "POST",
        body: JSON.stringify({ status, comment }),
      });
      setMsg(status === "approved" ? "Épisode approuvé" : "Révision demandée");
      setComment("");
      await open(selected.episode.id);
      await load();
    } catch (e) { setError(e.message); }
  }

  async function publish() {
    setError("");
    try {
      const r = await api(`/publishing/episodes/${selected.episode.id}`, { method: "POST" });
      setMsg(`Publié (${r.licences_checked} licences vérifiées)`);
      await open(selected.episode.id);
      await load();
    } catch (e) { setError(e.message); }
  }

  return (
    <div>
      <h1>Review & Publication</h1>
      {error && <div className="error">{error}</div>}
      {msg && <div className="success">{msg}</div>}

      <table className="table mb">
        <thead>
          <tr><th>Épisode</th><th>Série</th><th>Statut</th><th>Final</th><th></th></tr>
        </thead>
        <tbody>
          {queue.map((e) => (
            <tr key={e.episode_id}>
              <td>#{e.episode_id} — {e.title}</td>
              <td>{e.series_id}</td>
              <td><StatusBadge s={e.status} /></td>
              <td>{e.is_final ? "oui" : "non"}</td>
              <td><button className="small secondary" onClick={() => open(e.episode_id)}>Ouvrir</button></td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && (
        <div className="card">
          <div className="row mb">
            <h2 style={{ margin: 0 }}>Épisode #{selected.episode.id} — {selected.episode.title}</h2>
            <StatusBadge s={selected.episode.status} />
            <button className="small secondary" onClick={() => setSelected(null)}>Fermer</button>
          </div>

          <div className="grid">
            <div>
              <h3>Narration</h3>
              <p>{selected.episode.narration || "—"}</p>
            </div>
            <div>
              <h3>Script</h3>
              <pre className="json">{selected.episode.script || "—"}</pre>
            </div>
          </div>

          {selected.seo.length > 0 && (
            <div className="mb">
              <h3>SEO</h3>
              {selected.seo.map((s, i) => (
                <div key={i} className="mb">
                  <strong>{s.language}:</strong> {s.title}
                  <pre className="json">{JSON.stringify({ description: s.description, tags: s.tags, hashtags: s.hashtags, chapters: s.chapters }, null, 2)}</pre>
                </div>
              ))}
            </div>
          )}

          {selected.shorts.length > 0 && (
            <div className="mb">
              <h3>Shorts par plateforme</h3>
              <table className="table">
                <tbody>
                  {selected.shorts.map((s, i) => (
                    <tr key={i}><td>{s.platform}</td><td>{s.captions}</td><td>{s.cta}</td><td>{s.asset_path || "—"}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="field">
            <label>Commentaire de validation</label>
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Commentaire pour l'équipe…" />
          </div>
          <div className="row">
            {can("review.operational") && (
              <>
                <button className="ok" onClick={() => decide("approved")}>Approuver</button>
                <button className="warn" onClick={() => decide("revision")}>Demander une révision</button>
              </>
            )}
            {can("publication.final") && selected.episode.status === "approved" && (
              <button onClick={publish}>Publier (Owner)</button>
            )}
          </div>

          {selected.history.length > 0 && (
            <div className="mt">
              <h3>Historique de validation</h3>
              <table className="table">
                <thead><tr><th>Version</th><th>Statut</th><th>Commentaire</th><th>Utilisateur</th><th>Date</th></tr></thead>
                <tbody>
                  {selected.history.map((h, i) => (
                    <tr key={i}>
                      <td>{h.version}</td>
                      <td><span className={`badge ${h.status === "approved" ? "green" : "yellow"}`}>{h.status}</span></td>
                      <td>{h.comment || "—"}</td>
                      <td>{h.user_id}</td>
                      <td className="muted">{new Date(h.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
