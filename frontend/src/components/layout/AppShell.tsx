import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { DnLogo } from "@/components/ui/DnLogo";
import { CommandPalette } from "@/components/CommandPalette";

type Role = "CREWING_OFFICER" | "CHIEF_PILOT" | "ADMIN" | "PILOT";
type NavItem = { to: string; label: string; roles?: Role[] };
type NavGroup = { label: string; items: NavItem[] };
const WRITERS: Role[] = ["CREWING_OFFICER", "CHIEF_PILOT", "ADMIN"];
const NAV_GROUPS: NavGroup[] = [
  { label: "Operations", items: [{ to: "/app", label: "Command centre" }, { to: "/app/roster", label: "Flight duty roster" }, { to: "/app/routings", label: "Flights & routings" }, { to: "/app/postings", label: "Crew postings" }, { to: "/app/irop", label: "IROP desk" }] },
  { label: "Crew readiness", items: [{ to: "/app/crew", label: "Crew directory" }, { to: "/app/training", label: "Training" }, { to: "/app/documents", label: "Documents" }, { to: "/app/currency", label: "Currency watch" }, { to: "/app/leave", label: "Leave" }, { to: "/app/swaps", label: "Duty swaps" }] },
  { label: "Safety & control", items: [{ to: "/app/fatigue", label: "Fatigue" }, { to: "/app/constraints", label: "FTL setup", roles: WRITERS }, { to: "/app/audit", label: "Audit packs" }, { to: "/app/notices", label: "Notices" }] },
  { label: "Workspace", items: [{ to: "/app/fleet", label: "Fleet" }, { to: "/app/import", label: "Import data", roles: WRITERS }, { to: "/app/settings", label: "Settings", roles: WRITERS }] },
];
function navFor(role: Role | undefined) { return NAV_GROUPS.map((group) => ({ ...group, items: group.items.filter((item) => !item.roles || (role && item.roles.includes(role))) })).filter((group) => group.items.length); }
function NavGroups({ mobile = false, onNavigate }: { mobile?: boolean; onNavigate?: () => void }) {
  const { user } = useAuth(); const groups = navFor(user?.role);
  return <nav aria-label="Main" className={cn("space-y-5", mobile && "space-y-3")}>{groups.map((group) => <section key={group.label}><p className="mb-1.5 px-3 text-[10px] font-bold uppercase tracking-[.18em] text-dn-muted">{group.label}</p><div className="space-y-0.5">{group.items.map((item) => <NavLink key={item.to} to={item.to} end={item.to === "/app"} onClick={onNavigate} className={({ isActive }) => cn("group flex items-center rounded-dn-sm px-3 py-2 text-sm transition-colors", isActive ? "bg-dn-navy text-dn-dark shadow-[inset_3px_0_0_#e7ae54]" : "text-dn-muted hover:bg-white/5 hover:text-dn-dark")}><span className="mr-2 h-1.5 w-1.5 rounded-full bg-current opacity-70" />{item.label}</NavLink>)}</div></section>)}</nav>;
}
export function AppShell() {
  const { user, logout } = useAuth(); const navigate = useNavigate(); const location = useLocation(); const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => setMenuOpen(false), [location.pathname]);
  const signOut = () => { logout(); navigate("/login"); };
  return <div className="ratiba-shell min-h-screen bg-dn-dark-deep text-dn-dark lg:grid lg:grid-cols-[17.5rem_minmax(0,1fr)]">
    <aside className="ratiba-grid hidden min-h-screen border-r border-dn-sand-deep bg-dn-dark-deep px-4 py-5 lg:flex lg:flex-col">
      <NavLink to="/app" className="mb-8 block"><DnLogo width={190} /></NavLink>
      <NavGroups />
      <div className="mt-auto border-t border-dn-sand-deep pt-4"><p className="px-3 text-xs font-medium text-dn-dark">{user?.full_name}</p><p className="px-3 pt-0.5 text-[10px] uppercase tracking-widest text-dn-muted">{user?.role?.replaceAll("_", " ")}</p><button type="button" onClick={signOut} className="mt-3 px-3 text-xs text-dn-muted underline hover:text-dn-dark">Sign out</button></div>
    </aside>
    <div className="min-w-0">
      <header className="sticky top-0 z-30 border-b border-dn-sand-deep bg-dn-dark-deep/95 backdrop-blur">
        <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-7">
          <NavLink to="/app" className="lg:hidden"><DnLogo showText={false} width={36} /></NavLink>
          <div className="hidden min-w-0 lg:block"><p className="text-[10px] font-bold uppercase tracking-[.22em] text-dn-navy-deep">East Africa · EAT (UTC+3)</p><p className="truncate text-sm text-dn-muted">Crew harmony, on time</p></div>
          <button type="button" onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))} className="hidden items-center gap-3 rounded-dn-sm border border-dn-sand-deep bg-dn-sand px-3 py-2 text-xs text-dn-muted hover:border-dn-navy hover:text-dn-dark sm:flex"><span>Search the operation</span><kbd className="rounded bg-dn-dark-deep px-1.5 py-0.5 font-mono text-[10px]">Ctrl K</kbd></button>
          <button type="button" onClick={() => setMenuOpen((open) => !open)} aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} className="rounded-dn-sm border border-dn-sand-deep p-2 text-dn-dark lg:hidden"><span className="block h-4 w-5 border-y-2 border-current before:block before:mt-[5px] before:border-t-2 before:content-['']" /></button>
        </div>
        {menuOpen && <div className="border-t border-dn-sand-deep bg-dn-dark-deep px-4 py-5 lg:hidden"><NavGroups mobile onNavigate={() => setMenuOpen(false)} /><button type="button" onClick={signOut} className="mt-4 text-xs text-dn-muted underline">Sign out</button></div>}
      </header>
      <CommandPalette />
      <main id="main-content" tabIndex={-1} className="mx-auto w-full max-w-[100rem] px-4 py-6 sm:px-7 sm:py-8"><div key={location.pathname} className="motion-fade-up"><Outlet /></div></main>
      <footer className="border-t border-dn-sand-deep px-7 py-5 text-xs text-dn-muted">Ratiba Aviation · Crew resource management · East Africa</footer>
    </div>
  </div>;
}
