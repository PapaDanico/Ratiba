import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles/index.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error("#root not found");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Register the PWA service worker in production builds only (keeps dev
// hot-reload free of SW caching). Failures are non-fatal.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
