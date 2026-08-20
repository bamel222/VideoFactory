"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { setSession, getToken } from "@/lib/api";
import { getItem, removeItem } from "@/lib/storage";
import { Field } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("owner@vf.ai");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getToken()) {
      router.replace("/dashboard");
    }
  }, [router]);

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
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Erreur de connexion");
      }
      setSession(data.access_token, data.role, data.email);
      if (data.password_expired) {
        setItem("vf_pw_expired", "1");
      } else {
        removeItem("vf_pw_expired");
      }
      router.replace("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-glow"></div>
      <div className="card login-card">
        <div className="brand mb">
          <div className="brand-logo">VF</div>
          <span>Video Factory AI</span>
        </div>
        <h1 style={{ fontSize: 20 }}>Connexion</h1>
        <p className="muted" style={{ fontSize: 13 }}>
          Usine vidéo multi-agents — documentaires multilingues et cartoons enfants.
        </p>
        {error && <div className="error">{error}</div>}
        <form onSubmit={login}>
          <Field label="Email">
            <input value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </Field>
          <Field label="Mot de passe">
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
          </Field>
          <button type="submit" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>
        <div className="mt faint" style={{ fontSize: 12, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
          Comptes de démo : owner@vf.ai / admin@vf.ai / reviewer@vf.ai — mot de passe : password123
        </div>
      </div>
    </div>
  );
}
