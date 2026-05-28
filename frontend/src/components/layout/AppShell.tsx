import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

const NAV: Array<{ to: string; label: string; end?: boolean }> = [
  { to: "/", label: "Overview", end: true },
  { to: "/roster", label: "Roster" },
  { to: "/crew", label: "Crew" },
  { to: "/currency", label: "Currency" },
  { to: "/leave", label: "Leave" },
  { to: "/swaps", label: "Swaps" },
  { to: "/audit", label: "Audit packs" },
  { to: "/settings", label: "Settings" },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-dn-steel-lt">
        <div className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <span className="inline-block h-2 w-2 rounded-full bg-dn-gold" aria-hidden />
            <span className="font-display text-2xl text-dn-dark">Ratiba</span>
            <span className="ml-3 font-mono text-xs uppercase tracking-widest text-dn-steel">
              DN Consultancy
            </span>
          </div>
          <div className="flex items-center gap-3">
            {user && (
              <span className="text-sm text-dn-muted">
                {user.full_name} · {user.role.toLowerCase().replace(/_/g, " ")}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
        <nav className="mx-auto max-w-7xl px-6 flex gap-1 -mb-px">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end ?? false}
              className={({ isActive }) =>
                cn(
                  "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                  isActive
                    ? "border-dn-gold text-dn-dark"
                    : "border-transparent text-dn-muted hover:text-dn-dark hover:border-dn-steel-lt",
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1 mx-auto w-full max-w-7xl px-6 py-8">
        <Outlet />
      </main>
      <footer className="border-t border-dn-gold/30 py-4 text-center text-xs text-dn-muted">
        © DN Consultancy · KCARs 2025 Part 8 compliant
      </footer>
    </div>
  );
}
