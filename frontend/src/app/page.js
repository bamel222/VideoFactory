"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setSession, getToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("owner@vf.ai");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (typeof window !== "undefined" && getToken()) {
    router.replace("/dashboard");
  }

  async function login(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Erreur de connexion");
      setSession(data.access_token, data.role, data.email);
      router.replace("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="card login-card">
        <div className="brand"><span className="dot"></span> Video Factory AI</div>
        <h1>Connexion</h1>
        <p className="muted">Comptes de démo : owner@vf.ai / admin@vf.ai / reviewer@vf.ai — mot de passe : password123</p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={login}>
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </div>
          <div className="field">
            <label>Mot de passe</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </div>
          <button type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
