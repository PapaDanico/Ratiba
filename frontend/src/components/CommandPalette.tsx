import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";

/**
 * Ctrl/⌘-K command palette: jump to any page or crew member from anywhere in
 * the app. Deliberately quiet — one input, one list, no tabs or footers.
 * Pages are filtered by role (same policy as the nav); crew are fetched once
 * per open session and matched on name / employee number.
 */

type Role = "CREWING_OFFICER" | "CHIEF_PILOT" | "ADMIN" | "PILOT";
type PageEntry = { label: string; to: string; group: string; keywords?: string; roles?: Role[] };
type CrewLite = { id: string; employee_no: string; first_name: string; last_name: string };
type Item = { id: string; label: string; detail: string; to: string };

const WRITERS: Role[] = ["CREWING_OFFICER", "CHIEF_PILOT", "ADMIN"];

const PAGES: PageEntry[] = [
  { label: "Dashboard", to: "/app", group: "Overview" },
  {
    label: "Routings",
    to: "/app/routings",
    group: "Operations",
    keywords: "flights sectors schedule",
  },
  { label: "Roster", to: "/app/roster", group: "Operations", keywords: "duties publish generate" },
  { label: "Postings", to: "/app/postings", group: "Operations", keywords: "acmi lease rotation" },
  {
    label: "IROP",
    to: "/app/irop",
    group: "Operations",
    keywords: "disruption recovery alternatives",
  },
  { label: "Crew", to: "/app/crew", group: "Crew", keywords: "pilots roster pdf pairing" },
  { label: "Training", to: "/app/training", group: "Crew", keywords: "type ratings recurrency" },
  { label: "Documents", to: "/app/documents", group: "Crew", keywords: "licence medical passport" },
  { label: "Currency", to: "/app/currency", group: "Crew", keywords: "opc lpc expiry" },
  { label: "Leave", to: "/app/leave", group: "Crew", keywords: "annual sick approve" },
  { label: "Swaps", to: "/app/swaps", group: "Crew", keywords: "duty swap requests" },
  { label: "Fleet", to: "/app/fleet", group: "Fleet & data", keywords: "aircraft registration" },
  {
    label: "Import",
    to: "/app/import",
    group: "Fleet & data",
    keywords: "csv onboarding",
    roles: WRITERS,
  },
  {
    label: "FTL setup",
    to: "/app/constraints",
    group: "Compliance",
    keywords: "limits variations scheme",
    roles: WRITERS,
  },
  { label: "Fatigue", to: "/app/fatigue", group: "Compliance", keywords: "reports duty hours" },
  { label: "Audit packs", to: "/app/audit", group: "Compliance", keywords: "kcaa evidence pdf" },
  { label: "Notices", to: "/app/notices", group: "System", keywords: "announcements pinned" },
  {
    label: "Settings",
    to: "/app/settings",
    group: "System",
    keywords: "operator users account",
    roles: WRITERS,
  },
];

export function CommandPalette() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [crew, setCrew] = useState<CrewLite[] | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Global shortcut. Ctrl-K on Windows/Linux, ⌘K on macOS.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Reset per open; lazily fetch crew the first time the palette opens.
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActive(0);
    inputRef.current?.focus();
    if (crew === null) {
      api<CrewLite[]>("/api/v1/crew")
        .then(setCrew)
        .catch(() => setCrew([]));
    }
  }, [open, crew]);

  const items = useMemo<Item[]>(() => {
    const q = query.trim().toLowerCase();
    const pages = PAGES.filter((p) => !p.roles || (user && p.roles.includes(user.role))).filter(
      (p) => !q || `${p.label} ${p.keywords ?? ""}`.toLowerCase().includes(q),
    );
    const pageItems = pages.map((p) => ({
      id: p.to,
      label: p.label,
      detail: p.group,
      to: p.to,
    }));
    // Crew results only once the user starts typing — an empty palette stays
    // a calm page list, not a directory dump.
    const crewItems = !q
      ? []
      : (crew ?? [])
          .filter((c) =>
            `${c.first_name} ${c.last_name} ${c.employee_no}`.toLowerCase().includes(q),
          )
          .slice(0, 6)
          .map((c) => ({
            id: c.id,
            label: `${c.first_name} ${c.last_name}`,
            detail: `Crew · ${c.employee_no}`,
            to: "/app/crew",
          }));
    return [...pageItems, ...crewItems].slice(0, 10);
  }, [query, crew, user]);

  useEffect(() => {
    if (active > items.length - 1) setActive(0);
  }, [items, active]);

  const pick = useCallback(
    (item: Item | undefined) => {
      if (!item) return;
      setOpen(false);
      navigate(item.to);
    },
    [navigate],
  );

  if (!open) return null;

  return (
    <div
      className="motion-fade-in fixed inset-0 z-50 bg-dn-dark/40 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) setOpen(false);
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="motion-scale-in mx-auto mt-[18vh] w-full max-w-lg overflow-hidden rounded-dn border border-dn-sand bg-white shadow-dn-lg"
        data-testid="command-palette"
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          else if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, items.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            pick(items[active]);
          }
        }}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Go to a page or find crew…"
          aria-label="Search pages and crew"
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-results"
          aria-activedescendant={items[active] ? `palette-item-${items[active].id}` : undefined}
          className="w-full border-b border-dn-sand px-5 py-4 text-sm outline-none placeholder:text-dn-muted"
          data-testid="palette-input"
        />
        <ul id="palette-results" role="listbox" className="max-h-80 overflow-y-auto py-1.5">
          {items.length === 0 ? (
            <li className="px-5 py-6 text-center text-sm text-dn-muted">Nothing matches.</li>
          ) : (
            items.map((item, i) => (
              <li
                key={item.id}
                id={`palette-item-${item.id}`}
                role="option"
                aria-selected={i === active}
                onMouseEnter={() => setActive(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  pick(item);
                }}
                className={cn(
                  "mx-1.5 flex cursor-pointer items-baseline justify-between gap-4 rounded-dn-sm px-3.5 py-2.5 text-sm",
                  i === active ? "bg-dn-navy-lt/50 text-dn-dark" : "text-dn-dark",
                )}
              >
                <span>{item.label}</span>
                <span className="text-xs text-dn-muted">{item.detail}</span>
              </li>
            ))
          )}
        </ul>
        <div className="flex items-center gap-3 border-t border-dn-sand px-5 py-2 text-[11px] text-dn-muted">
          <span>↑↓ navigate</span>
          <span>↵ open</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  );
}
