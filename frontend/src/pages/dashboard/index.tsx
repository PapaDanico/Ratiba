import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const GUIDE_COLLAPSE_KEY = "ratiba.guide.collapsed";

const GUIDE_STEPS: Array<{ title: string; tab: string; detail: string }> = [
  {
    title: "Add your aircraft & crew",
    tab: "Fleet · Crew",
    detail:
      "Register aircraft under Fleet and add pilots under Crew. (A demo workspace already comes with sample aircraft and crew, so you can skip ahead.)",
  },
  {
    title: "Qualify your crew",
    tab: "Training",
    detail:
      "Give each pilot a type rating for the aircraft they fly. The auto-roster only assigns crew who are type-rated and current, so this step is what makes scheduling work.",
  },
  {
    title: "Build the flight schedule",
    tab: "Routings",
    detail:
      "Add flights individually, or switch to Recurring to create a daily/weekly pattern across a date range in one go. Departure and arrival times are entered in UTC.",
  },
  {
    title: "Auto-generate the roster",
    tab: "Roster",
    detail:
      "Click “Auto-generate roster”. Ratiba runs the FTL-aware optimiser and shows a legal draft — assigned duties, any that couldn’t be filled, and solve time. Review it, then Publish.",
  },
  {
    title: "Share & export",
    tab: "Crew · Audit packs",
    detail:
      "From Crew, download a pilot’s monthly roster PDF or copy their calendar-feed link to subscribe in Google/Apple/Outlook. From Audit packs, generate a KCAA audit pack and export the payroll CSV.",
  },
  {
    title: "Stay ahead of expiries",
    tab: "Training · Documents",
    detail:
      "Record licences and medicals under Documents. Training → Recurrency then lists every rating, currency, and document about to lapse — colour-coded by urgency.",
  },
];

function DemoGuide() {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(GUIDE_COLLAPSE_KEY) === "1",
  );

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(GUIDE_COLLAPSE_KEY, next ? "1" : "0");
  }

  return (
    <Card className="border-dn-gold/40 bg-dn-gold/5">
      <CardBody>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-xl text-dn-dark">Getting started</h2>
            {!collapsed && (
              <p className="mt-1 text-sm text-dn-muted">
                The fastest path from an empty workspace to a published, FTL-legal roster:
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={toggle}
            className="text-xs text-dn-steel underline shrink-0"
            data-testid="toggle-guide"
          >
            {collapsed ? "Show guide" : "Hide"}
          </button>
        </div>

        {!collapsed && (
          <ol className="mt-4 space-y-3">
            {GUIDE_STEPS.map((step, i) => (
              <li key={step.title} className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-dn-gold/80 text-xs font-semibold text-dn-lava">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="text-sm">
                    <span className="font-medium text-dn-dark">{step.title}</span>{" "}
                    <span className="font-mono text-[11px] uppercase tracking-wide text-dn-steel">
                      {step.tab}
                    </span>
                  </p>
                  <p className="text-sm text-dn-muted">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardBody>
    </Card>
  );
}

type CurrencyStatus = {
  crew_id: string;
  currency_type: string;
  expires_date: string;
  days_remaining: number;
  state: "GREEN" | "AMBER" | "RED";
};

type LeaveRequest = {
  id: string;
  status: string;
};

export function DashboardPage() {
  const { user } = useAuth();
  const [pendingLeave, setPendingLeave] = useState<number>(0);
  const [currencyCounts, setCurrencyCounts] = useState({
    green: 0,
    amber: 0,
    red: 0,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [pending, currencies] = await Promise.all([
          api<LeaveRequest[]>("/api/v1/leave?status=PENDING"),
          api<CurrencyStatus[]>("/api/v1/crew/currency/dashboard"),
        ]);
        if (cancelled) return;
        setPendingLeave(pending.length);
        const counts = { green: 0, amber: 0, red: 0 };
        for (const c of currencies) {
          if (c.state === "GREEN") counts.green++;
          else if (c.state === "AMBER") counts.amber++;
          else counts.red++;
        }
        setCurrencyCounts(counts);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-dn-dark">
          Welcome back, {user?.full_name.split(" ")[0]}
        </h1>
        <p className="mt-1 text-dn-muted text-sm">
          Operations overview — KCARs 2025 Part 8 baseline.
        </p>
      </div>
      {error && (
        <Card>
          <CardBody className="text-sm text-dn-red">{error}</CardBody>
        </Card>
      )}
      <DemoGuide />
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Pending leave</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="font-display text-5xl text-dn-dark" data-testid="pending-leave-count">
              {pendingLeave}
            </div>
            <p className="mt-2 text-sm text-dn-muted">Requests awaiting your decision.</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Currency status</CardTitle>
          </CardHeader>
          <CardBody className="space-y-2">
            <div className="flex items-center justify-between">
              <Badge tone="green">Current</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.green}</span>
            </div>
            <div className="flex items-center justify-between">
              <Badge tone="amber">Expiring ≤ 30 d</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.amber}</span>
            </div>
            <div className="flex items-center justify-between">
              <Badge tone="red">Expired</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.red}</span>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>This week</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-sm text-dn-muted">
              Roster calendar lives under{" "}
              <a href="/roster" className="text-dn-steel underline">
                Roster
              </a>
              . FTL violations show inline before publication.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
