const BASE = "/api/v1";

export function getToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("vf_token");
}

export function setSession(token, role, email) {
  window.localStorage.setItem("vf_token", token);
  window.localStorage.setItem("vf_role", role || "");
  window.localStorage.setItem("vf_email", email || "");
}

export function getRole() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("vf_role");
}

export function getEmail() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem("vf_email") || "";
}

export function logout() {
  window.localStorage.removeItem("vf_token");
  window.localStorage.removeItem("vf_role");
  window.localStorage.removeItem("vf_email");
}

export function can(permission) {
  const role = getRole();
  const matrix = {
    owner: [
      "billing.manage", "secrets.manage", "providers.delete", "users.manage",
      "publication.final", "roles.manage", "providers.manage", "storage.manage",
      "jobs.manage", "review.operational", "seo.manage", "audit.read",
      "series.manage", "pipeline.run",
    ],
    admin: [
      "providers.manage_noncritical", "storage.manage", "jobs.manage",
      "review.operational", "seo.manage", "series.manage", "pipeline.run", "audit.read",
    ],
    reviewer: ["review.quality", "review.read", "content.read"],
  };
  return (matrix[role] || []).includes(permission);
}

export async function api(path, opts = {}) {
  const token = getToken();
  const headers = { ...(opts.headers || {}) };
  if (opts.body && !(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (res.status === 401) {
    logout();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/dashboard")) {
      window.location.href = "/";
    }
    throw new Error("Non authentifié");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Erreur ${res.status}`);
  }
  return data;
}
