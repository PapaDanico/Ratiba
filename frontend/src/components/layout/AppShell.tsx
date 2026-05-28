import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

const NAV: Array<{ to: string; label: string; end?: boolean }> = [
  { to: "/", label: "Overview", end: true },
  { to: "/routings", label: "Routings" },
  { to: "/roster", label: "Roster" },
  { to: "/crew", label: "Crew" },
  { to: "/fleet", label: "Fleet" },
  { to: "/training", label: "Training" },
  { to: "/currency", label: "Currency" },
  { to: "/leave", label: "Leave" },
  { to: "/swaps", label: "Swaps" },
  { to: "/notices", label: "Notices" },
  { to: "/constraints", label: "FTL setup" },
  { to: "/audit", label: "Audit packs" },
  { to: "/settings", label: "Settings" },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Top bar: dark volcanic header ── */}
      <header className="bg-dn-lava tribal-texture">
        <div className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <span className="font-display text-2xl text-dn-gold tracking-wide">Ratiba</span>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-sm text-dn-gold/60">
                {user.full_name} · {user.role.toLowerCase().replace(/_/g, " ")}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              className="text-dn-gold/70 hover:text-dn-gold hover:bg-white/10"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Sign out
            </Button>
          </div>
        </div>

        {/* Maasai geometric stripe separator */}
        <div className="tribal-stripe" />

        {/* Navigation tabs */}
        <nav className="mx-auto max-w-7xl px-6 flex gap-1 bg-dn-lava/80">
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
      </header>

      {/* ── Main content ── */}
      <main className="flex-1 mx-auto w-full max-w-7xl px-6 py-8">
        <Outlet />
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-dn-gold/20 py-4 text-center text-xs text-dn-muted">
        <span className="inline-flex items-center gap-2">
          <svg width="8" height="8" viewBox="0 0 8 8" fill="#C9A84C" aria-hidden>
            <polygon points="4,0 8,4 4,8 0,4" />
          </svg>
          DN Consultancy · KCARs 2025 Part 8 compliant
          <svg width="8" height="8" viewBox="0 0 8 8" fill="#C9A84C" aria-hidden>
            <polygon points="4,0 8,4 4,8 0,4" />
          </svg>
        </span>
      </footer>
    </div>
  );
}
