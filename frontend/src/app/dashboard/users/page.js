"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, SkeletonRows, Field, useToast } from "@/components/ui";

export default function UsersPage() {
  const [users, setUsers] = useState(null);
  const [form, setForm] = useState({ email: "", name: "", password: "", role: "reviewer" });
  const [error, setError] = useState("");
  const { toast, toastError } = useToast();

  const load = async () => {
    try {
      setUsers(await api("/users"));
    } catch (e) {
      toastError(e.message);
    }
  };
  useEffect(() => { load(); }, []);

  async function create(e) {
    e.preventDefault();
    setError("");
    try {
      await api("/users", { method: "POST", body: JSON.stringify(form) });
      setForm({ email: "", name: "", password: "", role: "reviewer" });
      toast("Utilisateur créé");
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
      toast("Utilisateur désactivé");
      await load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <PageHeader title="Utilisateurs & Rôles" subtitle="Gérez les comptes (Owner, Admin, Reviewer) et leurs accès." />

      {error && <div className="error">{error}</div>}

      <div className="card mb">
        <h2>Nouvel utilisateur</h2>
        <form onSubmit={create}>
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 150px auto", alignItems: "end" }}>
            <Field label="Email"><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required /></Field>
            <Field label="Nom"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></Field>
            <Field label="Mot de passe" hint="12+ caractères, majuscule, minuscule, chiffre"><input type="password" minLength={12} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required /></Field>
            <Field label="Rôle">
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="owner">Owner</option><option value="admin">Admin</option><option value="reviewer">Reviewer</option>
              </select>
            </Field>
            <button type="submit">Créer</button>
          </div>
        </form>
      </div>

      {!users ? (
        <SkeletonRows rows={5} cols={5} />
      ) : (
        <div className="table-wrap">
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
      )}
    </div>
  );
}
