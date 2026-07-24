import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { DnLogo } from "@/components/ui/DnLogo";
import { CommandPalette } from "@/components/CommandPalette";

type Role = "CREWING_OFFICER" | "CHIEF_PILOT" | "ADMIN" | "PILOT";
type NavItem = { to: string; label: string; end?: boolean; roles?: Role[] };
type NavGroup = { label: string; items: NavItem[] };

const WRITERS: Role[] = ["CREWING_OFFICER", "CHIEF_PILOT", "ADMIN"];

// Grouped so the main menu scans as sections rather than a flat 18-item list
// — especially important in the mobile/PWA drawer, the primary way crew
// actually use this app day to day.
const NAV_GROUPS: NavGroup[] = [
  { label: "Overview", items: [{ to: "/app", label: "Dashboard", end: true }] },
  {
    label: "Operations",
    items: [
      { to: "/app/routings", label: "Routings" },
      { to: "/app/roster", label: "Roster" },
      { to: "/app/postings", label: "Postings" },
      { to: "/app/irop", label: "IROP" },
    ],
  },
  {
    label: "Crew",
    items: [
      { to: "/app/crew", label: "Crew" },
      { to: "/app/training", label: "Training" },
      { to: "/app/documents", label: "Documents" },
      { to: "/app/currency", label: "Currency" },
      { to: "/app/leave", label: "Leave" },
      { to: "/app/swaps", label: "Swaps" },
    ],
  },
  {
    label: "Fleet & data",
    items: [
      { to: "/app/fleet", label: "Fleet" },
      { to: "/app/import", label: "Import", roles: WRITERS },
    ],
  },
  {
    label: "Compliance",
    items: [
      { to: "/app/constraints", label: "FTL setup", roles: WRITERS },
      { to: "/app/fatigue", label: "Fatigue" },
      { to: "/app/audit", label: "Audit packs" },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/app/notices", label: "Notices" },
      { to: "/app/settings", label: "Settings", roles: WRITERS },
    ],
  },
];

/** Nav filtered to what this role can actually use: read-only PILOT accounts
 * lose the configuration/import surfaces (the API rejects their writes anyway). */
function navGroupsFor(role: Role | undefined): NavGroup[] {
  return NAV_GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((i) => !i.roles || (role && i.roles.includes(role))),
  })).filter((g) => g.items.length > 0);
}

function isItemActive(item: NavItem, pathname: string): boolean {
  return item.end ? pathname === item.to : pathname.startsWith(item.to);
}

function chevron(open: boolean) {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      aria-hidden
      className={cn("transition-transform", open && "rotate-180")}
    >
      <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** One entry in the desktop nav row: a group of 2+ pages collapses into a
 * single button that opens a small dropdown, so the whole menu reads as one
 * calm row instead of 18 links wrapped across two. Closes on outside click,
 * Escape, or picking an item. */
function NavGroupMenu({ group }: { group: NavGroup }) {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const active = group.items.some((i) => isItemActive(i, location.pathname));

  useEffect(() => {
    if (!open) return;
    function onPointer(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        data-testid={`nav-group-${group.label}`}
        className={cn(
          "flex items-center gap-1 px-3 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
          active
            ? "border-dn-steel text-dn-steel-deep"
            : "border-transparent text-dn-muted hover:text-dn-dark hover:border-dn-steel-lt",
        )}
      >
        {group.label}
        {chevron(open)}
      </button>
      {open && (
        <div
          role="menu"
          className="motion-scale-in absolute left-0 top-full z-40 mt-1 min-w-[11rem] rounded-dn-sm border border-dn-sand bg-white py-1.5 shadow-dn-lg"
        >
          {group.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              role="menuitem"
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                cn(
                  "block px-4 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-dn-steel-lt/40 font-medium text-dn-steel-deep"
                    : "text-dn-dark hover:bg-dn-fog",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

/** Mobile drawer as an accordion: only the section containing the current
 * page starts expanded, so opening the menu doesn't dump all 18 links down
 * the screen at once. Remounts fresh each time the drawer opens (it's only
 * in the DOM while `menuOpen`), so the lazy initial state always reflects
 * wherever the user currently is. */
function MobileNav({ groups }: { groups: NavGroup[] }) {
  const location = useLocation();
  const [expanded, setExpanded] = useState<Set<string>>(() => {
    const current = groups.find((g) => g.items.some((i) => isItemActive(i, location.pathname)));
    return new Set(current ? [current.label] : []);
  });

  function toggle(label: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  return (
    <nav
      aria-label="Main"
      className="lg:hidden bg-white border-t border-dn-steel-lt/50"
      data-testid="mobile-nav"
    >
      <div className="max-h-[70vh] overflow-y-auto py-1">
        {groups.map((group) => {
          const isOpen = expanded.has(group.label);
          const active = group.items.some((i) => isItemActive(i, location.pathname));
          return (
            <div key={group.label} className="border-b border-dn-steel-lt/30 last:border-b-0">
              <button
                type="button"
                onClick={() => toggle(group.label)}
                aria-expanded={isOpen}
                className={cn(
                  "flex w-full items-center justify-between px-5 py-3 text-sm font-semibold uppercase tracking-wide transition-colors",
                  active ? "text-dn-steel-deep" : "text-dn-muted",
                )}
                data-testid={`mobile-nav-group-${group.label}`}
              >
                {group.label}
                {chevron(isOpen)}
              </button>
              {isOpen && (
                <div className="pb-1">
                  {group.items.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end ?? false}
                      className={({ isActive }) =>
                        cn(
                          "block px-5 py-3 text-base border-l-4 transition-colors",
                          isActive
                            ? "border-dn-steel text-dn-steel-deep bg-dn-steel-lt/10"
                            : "border-transparent text-dn-muted hover:text-dn-dark hover:bg-dn-steel-lt/5",
                        )
                      }
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </nav>
  );
}

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  function signOut() {
    logout();
    navigate("/login");
  }

  const userLabel = user
    ? `${user.full_name} · ${user.role.toLowerCase().replace(/_/g, " ")}`
    : null;
  const groups = navGroupsFor(user?.role);

  return (
    <div className="min-h-screen flex flex-col bg-white">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-dn-steel-deep focus:px-3 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to content
      </a>
      {/* ── Top bar: modern header ── */}
      <header className="bg-white border-b border-dn-steel-lt sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <DnLogo showText={false} width={28} />
            <span className="text-lg font-semibold text-dn-dark">Ratiba</span>
          </div>

          {/* Desktop: identity + sign out */}
          <div className="hidden lg:flex items-center gap-4">
            <button
              type="button"
              onClick={() =>
                window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))
              }
              className="flex items-center gap-2 rounded-dn-sm border border-dn-sand px-2.5 py-1.5 text-xs text-dn-muted transition-colors hover:border-dn-steel hover:text-dn-dark"
              aria-label="Open command palette"
              data-testid="palette-hint"
            >
              Search
              <kbd className="rounded-sm bg-dn-fog px-1.5 py-0.5 font-mono text-[10px]">
                {typeof navigator !== "undefined" && /Mac/i.test(navigator.platform)
                  ? "⌘K"
                  : "Ctrl K"}
              </kbd>
            </button>
            {userLabel && <span className="text-sm text-dn-muted">{userLabel}</span>}
            <Button
              variant="ghost"
              size="sm"
              className="text-dn-steel-deep hover:text-dn-dark hover:bg-dn-steel-lt/30"
              onClick={signOut}
            >
              Sign out
            </Button>
          </div>

          {/* Mobile: hamburger toggle */}
          <button
            type="button"
            className="lg:hidden inline-flex items-center justify-center h-10 w-10 rounded-md text-dn-steel-deep hover:bg-dn-steel-lt/30"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
            data-testid="nav-toggle"
          >
            {menuOpen ? (
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden
              >
                <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
              </svg>
            ) : (
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden
              >
                <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
              </svg>
            )}
          </button>
        </div>

        {/* Desktop navigation: one calm row. A lone-item group (Dashboard)
            renders as a direct link; every other group collapses into a
            dropdown, so 18 pages read as ~6 clicks instead of two wrapped
            rows of flat text. */}
        <nav
          aria-label="Main"
          className="hidden lg:flex mx-auto max-w-7xl px-6 items-center gap-1 border-t border-dn-steel-lt/50"
        >
          {groups.map((group) =>
            group.items.length === 1 ? (
              <NavLink
                key={group.label}
                to={group.items[0]!.to}
                end={group.items[0]!.end ?? false}
                className={({ isActive }) =>
                  cn(
                    "px-3 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                    isActive
                      ? "border-dn-steel text-dn-steel-deep"
                      : "border-transparent text-dn-muted hover:text-dn-dark hover:border-dn-steel-lt",
                  )
                }
              >
                {group.items[0]!.label}
              </NavLink>
            ) : (
              <NavGroupMenu key={group.label} group={group} />
            ),
          )}
        </nav>

        {/* Mobile slide-down menu: an accordion of the same groups. */}
        {menuOpen && (
          <>
            <MobileNav groups={groups} />
            <div className="lg:hidden border-t border-dn-steel-lt/50 bg-white px-5 py-3 flex items-center justify-between">
              {userLabel && (
                <span className="text-xs text-dn-muted truncate pr-3">{userLabel}</span>
              )}
              <button
                type="button"
                onClick={signOut}
                className="text-sm text-dn-steel-deep hover:text-dn-dark underline shrink-0"
              >
                Sign out
              </button>
            </div>
          </>
        )}
      </header>

      <CommandPalette />

      {/* ── Main content ── */}
      <main
        id="main-content"
        tabIndex={-1}
        className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-6 sm:py-8"
      >
        {/* Re-keying on the path replays a gentle settle-up on every route
            change, so navigation feels continuous rather than a hard cut. */}
        <div key={location.pathname} className="motion-fade-up">
          <Outlet />
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-dn-steel-lt/50 bg-white py-6 text-center text-xs text-dn-muted">
        <div className="mx-auto max-w-7xl px-4">
          <p className="mb-3">
            DN Consultancy · Aligned with the KCAA Flight Duty Time Scheme &amp; ICAO Annex 6
          </p>
          <div className="flex justify-center gap-4">
            <NavLink to="/privacy" className="hover:text-dn-steel-deep underline">
              Privacy Policy
            </NavLink>
            <span>·</span>
            <NavLink to="/terms" className="hover:text-dn-steel-deep underline">
              Terms of Use
            </NavLink>
          </div>
        </div>
      </footer>
    </div>
  );
}
