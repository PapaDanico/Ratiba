import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import { DnLogo } from "@/components/ui/DnLogo";

const NAV: Array<{ to: string; label: string; end?: boolean }> = [
  { to: "/", label: "Overview", end: true },
  { to: "/routings", label: "Routings" },
  { to: "/roster", label: "Roster" },
  { to: "/crew", label: "Crew" },
  { to: "/postings", label: "Postings" },
  { to: "/import", label: "Import" },
  { to: "/fleet", label: "Fleet" },
  { to: "/training", label: "Training" },
  { to: "/documents", label: "Documents" },
  { to: "/currency", label: "Currency" },
  { to: "/leave", label: "Leave" },
  { to: "/swaps", label: "Swaps" },
  { to: "/notices", label: "Notices" },
  { to: "/constraints", label: "FTL setup" },
  { to: "/fatigue", label: "Fatigue" },
  { to: "/irop", label: "IROP" },
  { to: "/audit", label: "Audit packs" },
  { to: "/settings", label: "Settings" },
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
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-dn-steel focus:px-3 focus:py-2 focus:text-sm focus:text-white"
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
              className="text-dn-steel hover:text-dn-dark hover:bg-dn-steel-lt/30"
              onClick={signOut}
            >
              Sign out
            </Button>
          </div>

          {/* Mobile: hamburger toggle */}
          <button
            type="button"
            className="lg:hidden inline-flex items-center justify-center h-10 w-10 rounded-md text-dn-steel hover:bg-dn-steel-lt/30"
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

        {/* Desktop navigation tabs */}
        <nav className="hidden lg:flex mx-auto max-w-7xl px-6 flex-wrap gap-x-1 border-t border-dn-steel-lt/50">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              className={({ isActive }) =>
                cn(
                  "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                  isActive
                    ? "border-dn-steel text-dn-steel"
                    : "border-transparent text-dn-muted hover:text-dn-dark hover:border-dn-steel-lt",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Mobile slide-down menu */}
        {menuOpen && (
          <nav
            className="lg:hidden bg-white border-t border-dn-steel-lt/50"
            data-testid="mobile-nav"
          >
            <div className="max-h-[70vh] overflow-y-auto py-2">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end ?? false}
                  className={({ isActive }) =>
                    cn(
                      "block px-5 py-3 text-base border-l-4 transition-colors",
                      isActive
                        ? "border-dn-steel text-dn-steel bg-dn-steel-lt/10"
                        : "border-transparent text-dn-muted hover:text-dn-dark hover:bg-dn-steel-lt/5",
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
              <div className="mt-2 border-t border-dn-steel-lt/50 px-5 py-3 flex items-center justify-between">
                {userLabel && (
                  <span className="text-xs text-dn-muted truncate pr-3">{userLabel}</span>
                )}
                <button
                  type="button"
                  onClick={signOut}
                  className="text-sm text-dn-steel hover:text-dn-dark underline shrink-0"
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
            <NavLink to="/privacy" className="hover:text-dn-steel underline">
              Privacy Policy
            </NavLink>
            <span>·</span>
            <NavLink to="/terms" className="hover:text-dn-steel underline">
              Terms of Use
            </NavLink>
          </div>
        </div>
      </footer>
    </div>
  );
}
