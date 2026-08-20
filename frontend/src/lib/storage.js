// Safe storage wrapper.
//
// `window.localStorage` throws a SecurityError when the app runs inside a
// sandboxed iframe without `allow-same-origin` (e.g. embedded previews), or in
// private browsing with storage blocked. We fall back to an in-memory store so
// the session still works for the lifetime of the page instead of crashing.

const memory = {};

export function getItem(key) {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(key);
  } catch (e) {
    return Object.prototype.hasOwnProperty.call(memory, key) ? memory[key] : null;
  }
}

export function setItem(key, value) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, value);
  } catch (e) {
    memory[key] = String(value);
  }
}

export function removeItem(key) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(key);
  } catch (e) {
    delete memory[key];
  }
}
