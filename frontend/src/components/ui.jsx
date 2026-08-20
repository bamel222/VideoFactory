"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="topbar">
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="subtitle">{subtitle}</div>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

export function StatCard({ icon, value, label, loading }) {
  return (
    <div className="stat">
      <div className="stat-icon">{icon}</div>
      <div>
        {loading ? <div className="skeleton title" style={{ width: 80 }} /> : <div className="value">{value ?? "—"}</div>}
        <div className="label">{label}</div>
      </div>
    </div>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`skeleton ${className}`} />;
}

export function SkeletonCards({ count = 4 }) {
  return (
    <div className="grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="stat">
          <Skeleton className="card" style={{ width: 42, height: 42, borderRadius: 12 }} />
          <div style={{ flex: 1 }}>
            <Skeleton className="title" />
            <div className="mt" style={{ marginTop: 6 }}>
              <Skeleton className="text" style={{ width: "70%" }} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonRows({ rows = 5, cols = 6 }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i}>
                <Skeleton className="text" style={{ width: "70%" }} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, r) => (
            <tr key={r}>
              {Array.from({ length: cols }).map((_, c) => (
                <td key={c}>
                  <Skeleton className="text" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Modal({ title, onClose, children, footer }) {
  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="row between mb">
          <h2 style={{ margin: 0 }}>{title}</h2>
          <button className="small ghost" onClick={onClose}>
            Fermer
          </button>
        </div>
        {children}
        {footer && <div className="row mt" style={{ marginTop: 18 }}>{footer}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ title, hint }) {
  return (
    <div className="card" style={{ textAlign: "center", padding: 40 }}>
      <h3 className="muted" style={{ margin: "0 0 6px" }}>{title}</h3>
      {hint && <p className="faint" style={{ margin: 0, fontSize: 13 }}>{hint}</p>}
    </div>
  );
}

export function Field({ label, hint, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {hint && <small className="faint">{hint}</small>}
    </div>
  );
}

const ToastCtx = createContext({ toast: () => {}, toastError: () => {} });

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const idRef = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  const push = useCallback(
    (type, message) => {
      const id = ++idRef.current;
      setToasts((t) => [...t, { id, type, message }]);
      window.setTimeout(() => dismiss(id), 4200);
    },
    [dismiss]
  );

  const toast = useCallback((message) => push("ok", message), [push]);
  const toastError = useCallback((message) => push("err", message), [push]);

  return (
    <ToastCtx.Provider value={{ toast, toastError }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`} onClick={() => dismiss(t.id)}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  return useContext(ToastCtx);
}
