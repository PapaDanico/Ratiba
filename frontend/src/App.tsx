import { useEffect, useState } from "react";

type Phase = {
  id: string;
  title: string;
  status: "done" | "in-progress" | "todo";
};

const PHASES: Phase[] = [
  { id: "0", title: "Project setup", status: "done" },
  { id: "1", title: "FTL engine + core data model", status: "done" },
  { id: "2", title: "Optimiser MVP", status: "in-progress" },
  { id: "3", title: "Crewing Officer dashboard", status: "todo" },
  { id: "4", title: "Telegram bot + crew web view", status: "todo" },
  { id: "5", title: "KCAA audit pack generation", status: "todo" },
  { id: "6", title: "Pilot deployment + 30-day stability", status: "todo" },
  { id: "7", title: "LLM constraint parser (post-pilot)", status: "todo" },
];

function statusChip(status: Phase["status"]) {
  if (status === "done") {
    return "bg-dn-green/10 text-dn-green border-dn-green/30";
  }
  if (status === "in-progress") {
    return "bg-dn-gold-lt text-dn-dark border-dn-gold";
  }
  return "bg-dn-fog text-dn-muted border-dn-muted/30";
}

export function App() {
  const [health, setHealth] = useState<"unknown" | "ok" | "fail">("unknown");

  useEffect(() => {
    fetch("/healthz")
      .then((r) => (r.ok ? setHealth("ok") : setHealth("fail")))
      .catch(() => setHealth("fail"));
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <header className="border-b border-dn-gold/50 pb-6">
        <p className="font-mono text-xs uppercase tracking-widest text-dn-steel">
          DN Consultancy · AI-anchored crew rostering
        </p>
        <h1 className="mt-2 text-5xl font-display text-dn-dark">Ratiba</h1>
        <p className="mt-2 text-dn-muted">
          Purpose-built for sub-scale East African aviation operators. KCARs 2025 Part 8 compliant.
          Phase 0 — Project Setup.
        </p>
      </header>

      <section className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-dn-steel-lt bg-white p-5 shadow-sm">
          <h2 className="text-lg font-display text-dn-dark">Backend</h2>
          <p className="mt-1 text-sm text-dn-muted">
            FastAPI · OR-Tools · Anthropic SDK · PostgreSQL · Redis
          </p>
          <p className="mt-3 text-sm">
            Health:{" "}
            <span
              className={
                "font-mono " +
                (health === "ok"
                  ? "text-dn-green"
                  : health === "fail"
                    ? "text-dn-red"
                    : "text-dn-muted")
              }
            >
              {health === "ok" ? "200 OK" : health === "fail" ? "unreachable" : "checking…"}
            </span>
          </p>
        </div>

        <div className="rounded-lg border border-dn-steel-lt bg-white p-5 shadow-sm">
          <h2 className="text-lg font-display text-dn-dark">Frontend</h2>
          <p className="mt-1 text-sm text-dn-muted">
            React 18 · TypeScript · Tailwind · shadcn/ui (Phase 3)
          </p>
          <p className="mt-3 font-mono text-xs text-dn-steel">
            Brand tokens loaded · Cormorant Garamond · DM Sans
          </p>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-2xl font-display text-dn-dark">Delivery phases</h2>
        <ul className="mt-4 space-y-2">
          {PHASES.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between rounded-md border border-dn-steel-lt bg-white px-4 py-3"
            >
              <div className="flex items-center gap-4">
                <span className="font-mono text-sm text-dn-steel">Phase {p.id}</span>
                <span className="text-dn-dark">{p.title}</span>
              </div>
              <span
                className={
                  "rounded-full border px-3 py-0.5 text-xs font-medium " + statusChip(p.status)
                }
              >
                {p.status}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <footer className="mt-12 border-t border-dn-gold/50 pt-4 text-xs text-dn-muted">
        © DN Consultancy · Proprietary · Working name <em>Ratiba</em> (subject to confirmation)
      </footer>
    </main>
  );
}
