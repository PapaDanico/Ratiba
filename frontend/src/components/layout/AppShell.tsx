import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

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

  // Close the mobile menu whenever the route changes.
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
    <div className="min-h-screen flex flex-col">
      {/* ── Top bar: dark volcanic header ── */}
      <header className="bg-dn-lava tribal-texture sticky top-0 z-30">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <span className="font-display text-2xl text-dn-gold tracking-wide">Ratiba</span>

          {/* Desktop: identity + sign out */}
          <div className="hidden lg:flex items-center gap-3">
            {userLabel && <span className="text-sm text-dn-gold/60">{userLabel}</span>}
            <Button
              variant="ghost"
              size="sm"
              className="text-dn-gold/70 hover:text-dn-gold hover:bg-white/10"
              onClick={signOut}
            >
              Sign out
            </Button>
          </div>

          {/* Mobile: hamburger toggle */}
          <button
            type="button"
            className="lg:hidden inline-flex items-center justify-center h-10 w-10 rounded-md text-dn-gold hover:bg-white/10"
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

        {/* Maasai geometric stripe separator */}
        <div className="tribal-stripe" />

        {/* Desktop navigation tabs (wrap gracefully on narrower desktops) */}
        <nav className="hidden lg:flex mx-auto max-w-7xl px-6 flex-wrap gap-x-1 bg-dn-lava/80">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              className={({ isActive }) =>
                cn(
                  "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                  isActive
                    ? "border-dn-gold text-dn-gold"
                    : "border-transparent text-dn-gold/50 hover:text-dn-gold/80 hover:border-dn-gold/30",
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
            className="lg:hidden bg-dn-lava/95 border-t border-dn-gold/10"
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
                        ? "border-dn-gold text-dn-gold bg-white/5"
                        : "border-transparent text-dn-gold/70 hover:text-dn-gold hover:bg-white/5",
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
              <div className="mt-2 border-t border-dn-gold/10 px-5 py-3 flex items-center justify-between">
                {userLabel && (
                  <span className="text-xs text-dn-gold/50 truncate pr-3">{userLabel}</span>
                )}
                <button
                  type="button"
                  onClick={signOut}
                  className="text-sm text-dn-gold/80 hover:text-dn-gold underline shrink-0"
                >
                  Sign out
                </button>
              </div>
            </div>
          </nav>
        )}
      </header>

      {/* ── Main content ── */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-6 sm:py-8">
        <Outlet />
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-dn-gold/20 py-4 text-center text-xs text-dn-muted">
        <span className="inline-flex items-center gap-2">
          <svg width="8" height="8" viewBox="0 0 8 8" fill="#C9A84C" aria-hidden>
            <polygon points="4,0 8,4 4,8 0,4" />
          </svg>
          DN Consultancy · Aligned with the KCAA Flight Duty Time Scheme &amp; ICAO Annex 6
          <svg width="8" height="8" viewBox="0 0 8 8" fill="#C9A84C" aria-hidden>
            <polygon points="4,0 8,4 4,8 0,4" />
          </svg>
        </span>
        <p className="mt-1 font-display italic text-dn-muted/80">
          Shaping Africa&apos;s Future, Together.
        </p>
        <div className="mt-1">
          <NavLink to="/privacy" className="underline hover:text-dn-dark">
            Privacy Policy
          </NavLink>
          <span className="mx-2">·</span>
          <NavLink to="/terms" className="underline hover:text-dn-dark">
            Terms of Use
          </NavLink>
        </div>
      </footer>
    </div>
  );
}
