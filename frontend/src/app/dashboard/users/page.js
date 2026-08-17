"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ email: "", name: "", password: "", role: "reviewer" });
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    try { setUsers(await api("/users")); } catch (e) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setError(""); setMsg("");
    try {
      await api("/users", { method: "POST", body: JSON.stringify(form) });
      setForm({ email: "", name: "", password: "", role: "reviewer" });
      await load();
    } catch (err) { setError(err.message); }
  }

  async function update(u, patch) {
    setError("");
    if (u.role !== "owner" && !confirm("Confirmer la modification du rôle / statut ?")) return;
    try {
      await api(`/users/${u.id}`, { method: "PATCH", body: JSON.stringify(patch) });
      await load();
    } catch (err) { setError(err.message); }
  }

  async function remove(u) {
    if (!confirm(`Désactiver ${u.email} ? (action Owner, irréversible via l'UI)`)) return;
    setError("");
    try {
      await api(`/users/${u.id}`, { method: "DELETE" });
      await load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <h1>Utilisateurs & Rôles</h1>
      {error && <div className="error">{error}</div>}
      {msg && <div className="success">{msg}</div>}

      <div className="card mb">
        <h2>Nouvel utilisateur</h2>
        <form onSubmit={create}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 150px auto", alignItems: "end" }}>
            <div className="field"><label>Email</label><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></div>
            <div className="field"><label>Nom</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></div>
            <div className="field"><label>Mot de passe</label><input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></div>
            <div className="field"><label>Rôle</label>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="owner">Owner</option><option value="admin">Admin</option><option value="reviewer">Reviewer</option>
              </select>
            </div>
            <button type="submit">Créer</button>
          </div>
        </form>
      </div>

      <table className="table">
        <thead>
          <tr><th>Email</th><th>Nom</th><th>Rôle</th><th>Actif</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.email}</td>
              <td>{u.name}</td>
              <td><span className={`badge ${u.role === "owner" ? "red" : u.role === "admin" ? "blue" : "gray"}`}>{u.role}</span></td>
              <td><span className={`badge ${u.active ? "green" : "red"}`}>{u.active ? "actif" : "désactivé"}</span></td>
              <td>
                <div className="row">
                  <button className="small secondary" onClick={() => update(u, { active: !u.active })}>{u.active ? "Désactiver" : "Activer"}</button>
                  {u.role !== "owner" && (
                    <button className="small secondary" onClick={() => update(u, { role: u.role === "reviewer" ? "admin" : "reviewer" })}>
                      Promouvoir/Dégrader
                    </button>
                  )}
                  <button className="small danger" onClick={() => remove(u)}>Suppr.</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
