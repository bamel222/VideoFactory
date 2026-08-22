"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, can } from "@/lib/api";
import { PageHeader, SkeletonRows, Field, Modal, useToast } from "@/components/ui";

function StatusBadge({ status }) {
  const map = {
    planned: "gray", in_progress: "blue", produced: "blue", review: "yellow",
    approved: "green", published: "green", archived: "gray",
  };
  return <span className={`badge ${map[status] || "gray"}`}>{status}</span>;
}

const MODE_OPTIONS = {
  documentary: [
    { value: "images", label: "Photo-Cinéma", title: "Images fixes animées en douceur (effet Ken Burns), narration, musique et sous-titres. Style documentaire classique et cinématographique." },
    { value: "video", label: "Vidéo Clip IA", title: "Montage de clips vidéo issus de banques d'images (Pexels/Pixabay) avec secours IA. Rendu dynamique, proche d'un reportage télévisé." },
  ],
  cartoon: [
    { value: "video", label: "Cartoon Clip IA", title: "Cartoon composé de clips vidéo animés générés par IA. Style 3D / animation fluide." },
    { value: "images", label: "Cartoon 2D Animé", title: "Images illustrées animées en 2D légère (déplacements, parallaxe, lèvres approximatives). Style dessin animé traditionnel, plus économique." },
  ],
};

const DEFAULT_MODE = { documentary: "images", cartoon: "video" };
const EMPTY_NOTIFY = { email: false, discord: false, telegram: false };
const EMPTY_FORM = { title: "", topic: "", kind: "documentary", generation_mode: "images", duration_minutes: 26, planned_episodes: 1, language: "fr", based_on_facts: false, notify: { ...EMPTY_NOTIFY } };

function NotifyCheckboxes({ value, onChange }) {
  return (
    <div className="field">
      <label>Notifier à la fin (optionnel)</label>
      <div className="row" style={{ gap: 16, marginTop: 4, flexWrap: "wrap" }}>
        <label className="row" style={{ alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={value.email} onChange={(e) => onChange({ ...value, email: e.target.checked })} />
          <span>Email</span>
        </label>
        <label className="row" style={{ alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={value.discord} onChange={(e) => onChange({ ...value, discord: e.target.checked })} />
          <span>Discord</span>
        </label>
        <label className="row" style={{ alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={value.telegram} onChange={(e) => onChange({ ...value, telegram: e.target.checked })} />
          <span>Telegram</span>
        </label>
        <small className="faint" style={{ alignSelf: "center" }}>
          Aucun choix ne bloque la génération.
        </small>
      </div>
    </div>
  );
}

export default function SeriesPage() {
  const [series, setSeries] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [launch, setLaunch] = useState(null); // { id, notify } when the run modal is open
  const { toast, toastError } = useToast();

  const load = async () => {
    try {
      setSeries(await api("/series"));
    } catch (e) {
      toastError(e.message);
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
      setForm(EMPTY_FORM);
      toast("Série créée");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function action(id, type) {
    setError("");
    setBusy(`${type}-${id}`);
    try {
      if (type === "dryrun") {
        const r = await api(`/series/${id}/dry-run`, { method: "POST" });
        toast(`Dry run : ${r.report.tasks} tâches, coût estimé $${r.report.budget.estimated_cost} — ${r.report.ready_to_launch ? "prêt à lancer" : "risques détectés"}`);
      }
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  function openLaunch(s) {
    setLaunch({ id: s.id, notify: { email: s.notify_email, discord: s.notify_discord, telegram: s.notify_telegram } });
  }

  async function confirmLaunch() {
    const { id, notify } = launch;
    setError("");
    setBusy(`run-${id}`);
    try {
      const r = await api(`/series/${id}/run`, {
        method: "POST",
        body: JSON.stringify({ series_id: id, dry_run: false, notify }),
      });
      toast(`Pipeline : ${r.done_tasks}/${r.total_tasks} tâches, statut ${r.status}`);
      setLaunch(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  const selectedModeTitle = (s) => MODE_OPTIONS[s.kind]?.find((o) => o.value === s.generation_mode)?.title;

  return (
    <div>
      <PageHeader title="Séries & Pipelines" subtitle="Créez une série documentaire ou cartoon, choisissez son format de génération puis lancez le pipeline." />

      {error && <div className="error">{error}</div>}

      <div className="card mb">
        <h2>Nouvelle série</h2>
        <form onSubmit={create}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 170px 200px 130px 110px auto", alignItems: "end" }}>
            <Field label="Titre">
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </Field>
            <Field label="Type">
              <select value={form.kind} onChange={(e) => onKindChange(e.target.value)}>
                <option value="documentary">Documentaire</option>
                <option value="cartoon">Cartoon</option>
              </select>
            </Field>
            <Field label="Format de génération">
              <select
                value={form.generation_mode}
                onChange={(e) => setForm({ ...form, generation_mode: e.target.value })}
                title={selectedModeTitle(form)}
              >
                {MODE_OPTIONS[form.kind].map((o) => (
                  <option key={o.value} value={o.value} title={o.title}>{o.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Durée / ép (min)">
              <input type="number" min="24" max="28" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} />
            </Field>
            <Field label="Épisodes">
              <input type="number" min="1" max="10" value={form.planned_episodes} onChange={(e) => setForm({ ...form, planned_episodes: Number(e.target.value) })} />
            </Field>
          </div>
          <div className="grid" style={{ gridTemplateColumns: "1fr 220px 180px", alignItems: "start" }}>
            <Field label="Sujet (facultatif, max 3000 caractères)" hint="Décrivez l'idée globale de la série — laissez vide pour un sujet générique">
              <textarea rows="4" maxLength="3000" value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} placeholder="Ex : une série documentaire grand public sur l'histoire des océans, du rôle des courants à la biodiversité des abysses..." />
            </Field>
            <Field label="Langue">
              <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {["fr", "en", "es", "de", "it", "pt"].map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </Field>
            {form.kind === "cartoon" && (
              <div className="field">
                <label>Fact-checking</label>
                <label className="row" style={{ alignItems: "center", gap: 8, marginTop: 4 }}>
                  <input type="checkbox" checked={form.based_on_facts} onChange={(e) => setForm({ ...form, based_on_facts: e.target.checked })} />
                  <span title="Cochez si le cartoon s'appuie sur des événements réels : la vérification des faits sera incluse dans le pipeline. Pour une fiction, laissez décoché.">
                    Basé sur des faits réels
                  </span>
                </label>
              </div>
            )}
          </div>
          <NotifyCheckboxes value={form.notify} onChange={(n) => setForm({ ...form, notify: n })} />
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}>
            <button type="submit">Créer</button>
          </div>
        </form>
      </div>

      {!series ? (
        <SkeletonRows rows={5} cols={10} />
      ) : (
        <div className="table-wrap">
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
                  <td className="muted">{s.id}</td>
                  <td><Link href={`/dashboard/series/${s.id}`}>{s.title}</Link></td>
                  <td><span className="badge gray">{s.kind}</span></td>
                  <td title={selectedModeTitle(s)}>{MODE_OPTIONS[s.kind]?.find((o) => o.value === s.generation_mode)?.label || s.generation_mode}</td>
                  <td>{s.duration_minutes || 26} min</td>
                  <td><StatusBadge status={s.status} /></td>
                  <td>{s.planned_episodes}</td>
                  <td>{s.business_score}</td>
                  <td>${s.production_cost}</td>
                  <td>
                    <div className="row">
                      <button className="small secondary" disabled={busy === `dryrun-${s.id}`} onClick={() => action(s.id, "dryrun")}>
                        {busy === `dryrun-${s.id}` ? "..." : "Dry run"}
                      </button>
                      {can("pipeline.run") && (
                        <button className="small" disabled={busy === `run-${s.id}`} onClick={() => openLaunch(s)}>
                          {busy === `run-${s.id}` ? "..." : "Lancer"}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {launch && (
        <Modal title="Lancer la génération" onClose={() => setLaunch(null)}>
          <p className="muted" style={{ fontSize: 13 }}>
            Choisissez comment être notifié à la fin de la génération. Vous recevrez une notification par épisode, puis un récapitulatif de la série.
          </p>
          <NotifyCheckboxes value={launch.notify} onChange={(n) => setLaunch({ ...launch, notify: n })} />
          <div className="row" style={{ justifyContent: "flex-end", gap: 10, marginTop: 18 }}>
            <button className="secondary" onClick={() => setLaunch(null)}>Annuler</button>
            <button disabled={busy === `run-${launch.id}`} onClick={confirmLaunch}>
              {busy === `run-${launch.id}` ? "Lancement..." : "Lancer le pipeline"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
