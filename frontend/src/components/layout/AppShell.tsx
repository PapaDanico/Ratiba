import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { DnLogo } from "@/components/ui/DnLogo";

type NavItem = { to: string; label: string; end?: boolean };
type NavGroup = { label: string; items: NavItem[] };

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
      { to: "/app/import", label: "Import" },
    ],
  },
  {
    label: "Compliance",
    items: [
      { to: "/app/constraints", label: "FTL setup" },
      { to: "/app/fatigue", label: "Fatigue" },
      { to: "/app/audit", label: "Audit packs" },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/app/notices", label: "Notices" },
      { to: "/app/settings", label: "Settings" },
    ],
  },
];

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

        {/* Desktop navigation tabs, grouped with dividers between sections */}
        <nav
          aria-label="Main"
          className="hidden lg:flex mx-auto max-w-7xl px-6 flex-wrap items-center gap-x-1 border-t border-dn-steel-lt/50"
        >
          {NAV_GROUPS.map((group, gi) => (
            <div key={group.label} className="flex items-center">
              {gi > 0 && <span className="mx-1.5 h-5 w-px bg-dn-steel-lt/60" aria-hidden />}
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end ?? false}
                  className={({ isActive }) =>
                    cn(
                      "px-3 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                      isActive
                        ? "border-dn-steel text-dn-steel-deep"
                        : "border-transparent text-dn-muted hover:text-dn-dark hover:border-dn-steel-lt",
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* Mobile slide-down menu, grouped into labelled sections */}
        {menuOpen && (
          <nav
            aria-label="Main"
            className="lg:hidden bg-white border-t border-dn-steel-lt/50"
            data-testid="mobile-nav"
          >
            <div className="max-h-[70vh] overflow-y-auto py-2">
              {NAV_GROUPS.map((group) => (
                <div key={group.label} className="py-1">
                  <p className="px-5 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-dn-muted">
                    {group.label}
                  </p>
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
              ))}
              <div className="mt-2 border-t border-dn-steel-lt/50 px-5 py-3 flex items-center justify-between">
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
            </div>
          </nav>
        )}
      </header>

      {/* ── Main content ── */}
      <main
        id="main-content"
        tabIndex={-1}
        className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-6 sm:py-8"
      >
        <Outlet />
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
